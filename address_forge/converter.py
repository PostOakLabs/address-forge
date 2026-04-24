"""
address-forge converter — LLM-powered free-text address → PostalAddress24.

Uses the Claude API to parse unstructured address strings into structured
ISO 20022 PostalAddress24 components, then returns a validated Pydantic model.

The converter is intentionally thin: it handles prompt construction, API calls,
JSON parsing, and model hydration. Domain validation lives in validator.py.
"""

from __future__ import annotations

import json
import os

try:
    import anthropic
except ImportError:  # allow import of module without SDK installed (tests mock it)
    anthropic = None  # type: ignore[assignment]

from .countries import get_country_rules
from .models import PostalAddress24

# ---------------------------------------------------------------------------
# Prompt template
# ---------------------------------------------------------------------------

_SYSTEM_PROMPT = """You are an expert in postal address parsing and the ISO 20022 PostalAddress24 schema.

Your task: parse a free-text postal address into structured ISO 20022 PostalAddress24 fields.

Return ONLY a valid JSON object with the following keys (omit keys where the value is unknown or absent):
{
  "address_type": "ADDR" | "PBOX" | "HOME" | "BIZZ" | "MLTO" | "DLVY" | null,
  "department": string (max 70 chars) | null,
  "sub_department": string (max 70 chars) | null,
  "street_name": string (max 70 chars) | null,
  "building_number": string (max 16 chars) | null,
  "building_name": string (max 35 chars) | null,
  "floor": string (max 70 chars) | null,
  "post_box": string (max 16 chars) | null,
  "room": string (max 70 chars) | null,
  "post_code": string (max 16 chars) | null,
  "town_name": string (max 35 chars, MANDATORY),
  "town_location_name": string (max 35 chars) | null,
  "district_name": string (max 35 chars) | null,
  "country_sub_division": string (max 35 chars) | null,
  "country": string (exactly 2 uppercase letters, ISO 3166-1 alpha-2, MANDATORY),
  "address_lines": array of strings (max 7 items, use ONLY if structured fields are insufficient),
  "confidence": {
    "street_name": 0.0–1.0,
    "building_number": 0.0–1.0,
    "post_code": 0.0–1.0,
    "town_name": 0.0–1.0,
    "country": 0.0–1.0
  }
}

Rules:
1. Prefer structured fields over address_lines.
2. town_name and country are MANDATORY — always populate them.
3. country must be an ISO 3166-1 alpha-2 code (e.g. GB, US, DE, FR, SG).
4. Separate building number from street name (e.g. "221B Baker Street" → building_number="221B", street_name="Baker Street").
5. Never invent data — if a field is genuinely absent, omit it or set null.
6. Confidence scores reflect your certainty about each field value.
7. Return ONLY the JSON object — no explanation, no markdown fences.
"""


# ---------------------------------------------------------------------------
# Converter
# ---------------------------------------------------------------------------


class ConversionResult:
    """Result of a single address conversion."""

    def __init__(
        self,
        address: PostalAddress24 | None,
        raw_input: str,
        raw_llm_response: str,
        confidence: dict[str, float],
        error: str | None = None,
    ):
        self.address = address
        self.raw_input = raw_input
        self.raw_llm_response = raw_llm_response
        self.confidence = confidence
        self.error = error
        self.success = address is not None and error is None

    def __repr__(self) -> str:
        if self.success:
            return f"<ConversionResult OK: {self.address.town_name}, {self.address.country}>"
        return f"<ConversionResult ERROR: {self.error}>"


def convert(
    address_string: str,
    api_key: str | None = None,
    model: str = "claude-sonnet-4-20250514",
    max_tokens: int = 1024,
    country_hint: str | None = None,
) -> ConversionResult:
    """
    Convert a free-text address string to a PostalAddress24 object.

    Args:
        address_string: Raw address text (e.g. "221B Baker Street, London, NW1 6XE, UK")
        api_key: Anthropic API key. Defaults to ANTHROPIC_API_KEY env var.
        model: Claude model to use. Defaults to claude-sonnet-4-20250514.
        max_tokens: Maximum tokens in the LLM response.
        country_hint: ISO 3166-1 alpha-2 country code hint (e.g. "GB") to improve accuracy.

    Returns:
        ConversionResult with a populated PostalAddress24 or an error message.
    """
    resolved_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
    if not resolved_key:
        raise ValueError(
            "No Anthropic API key provided. Set ANTHROPIC_API_KEY environment variable "
            "or pass api_key= to convert()."
        )

    if anthropic is None:
        raise ImportError(
            "anthropic SDK is not installed. Install it with: pip install anthropic"
        )

    client = anthropic.Anthropic(api_key=resolved_key)

    # Build the user prompt
    user_prompt = f"Parse this postal address:\n\n{address_string.strip()}"
    if country_hint:
        rules = get_country_rules(country_hint)
        if rules:
            user_prompt += (
                f"\n\nCountry hint: {country_hint}. Country-specific rules:\n{rules}"
            )
        else:
            user_prompt += f"\n\nCountry hint: {country_hint}"

    # Call Claude
    raw_response = ""
    try:
        message = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )
        raw_response = message.content[0].text.strip()
    except Exception as exc:
        return ConversionResult(
            address=None,
            raw_input=address_string,
            raw_llm_response="",
            confidence={},
            error=f"Claude API call failed: {exc}",
        )

    # Parse JSON
    try:
        # Strip markdown fences if the model adds them despite instructions
        cleaned = raw_response
        if cleaned.startswith("```"):
            cleaned = "\n".join(cleaned.split("\n")[1:])
        if cleaned.endswith("```"):
            cleaned = "\n".join(cleaned.split("\n")[:-1])
        data = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        return ConversionResult(
            address=None,
            raw_input=address_string,
            raw_llm_response=raw_response,
            confidence={},
            error=f"Failed to parse Claude response as JSON: {exc}\nResponse: {raw_response[:300]}",
        )

    # Extract confidence scores before building model
    confidence = data.pop("confidence", {})

    # Remove null values so Pydantic uses defaults
    data = {k: v for k, v in data.items() if v is not None}

    # Handle empty address_lines
    if "address_lines" not in data:
        data["address_lines"] = []

    # Hydrate Pydantic model
    try:
        address = PostalAddress24(**data)
    except Exception as exc:
        return ConversionResult(
            address=None,
            raw_input=address_string,
            raw_llm_response=raw_response,
            confidence=confidence,
            error=f"PostalAddress24 validation failed: {exc}",
        )

    result = ConversionResult(
        address=address,
        raw_input=address_string,
        raw_llm_response=raw_response,
        confidence=confidence,
    )
    return result


def convert_to_xml(
    address_string: str,
    element_name: str = "PstlAdr",
    **kwargs,
) -> str:
    """
    Convert a free-text address string directly to an ISO 20022 XML block.

    Returns an XML string fragment suitable for embedding in an MX message,
    or raises ValueError if conversion fails.
    """
    try:
        from lxml import etree
    except ImportError:
        raise ImportError(
            "lxml is required for XML output. Install it with: pip install lxml"
        )

    result = convert(address_string, **kwargs)
    if not result.success:
        raise ValueError(f"Address conversion failed: {result.error}")

    xml_dict = result.address.to_xml_dict()
    root = etree.Element(element_name)
    for tag, value in xml_dict.items():
        child = etree.SubElement(root, tag)
        child.text = str(value)

    return etree.tostring(root, pretty_print=True, encoding="unicode")


def convert_batch(
    address_strings: list[str],
    **kwargs,
) -> list[ConversionResult]:
    """
    Convert a list of free-text address strings to PostalAddress24 objects.
    Calls are made sequentially (no concurrency by default).
    """
    return [convert(addr, **kwargs) for addr in address_strings]
