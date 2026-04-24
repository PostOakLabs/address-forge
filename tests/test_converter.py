"""
Tests for address_forge.converter — LLM-powered free-text → PostalAddress24.

All tests mock the Anthropic API client. No real API calls are made.
The anthropic SDK does not need to be installed to run these tests.

Covers:
  - UK standard address parsing (3 cases: standard, flat/apartment, postcode variants)
  - US address parsing (3 cases: standard, PO Box, ZIP+4)
  - German address parsing (2 cases)
  - French address parsing (2 cases)
  - Country code detection and model field population
  - Malformed JSON response from API → graceful error
  - Missing mandatory fields in API response → error surfaced
  - convert_to_xml returns valid XML fragment
  - convert_batch processes multiple addresses
"""

import json
import os
import sys
from types import ModuleType
from unittest.mock import MagicMock, patch

import pytest

import address_forge.converter as converter_module
from address_forge.converter import (
    convert,
    convert_batch,
    convert_to_xml,
    ConversionResult,
)
from address_forge.models import PostalAddress24

# ---------------------------------------------------------------------------
# Build a fake anthropic module so patch targets always exist
# ---------------------------------------------------------------------------


def _make_fake_anthropic():
    """Return a MagicMock that looks like the anthropic module with Anthropic class."""
    fake = MagicMock(spec=ModuleType)
    fake.Anthropic = MagicMock()
    return fake


# ---------------------------------------------------------------------------
# Mock helpers
# ---------------------------------------------------------------------------


def _make_mock_client(payload: dict) -> MagicMock:
    """Return a mock anthropic client whose messages.create returns payload as JSON text."""
    content_block = MagicMock()
    content_block.text = json.dumps(payload)
    message = MagicMock()
    message.content = [content_block]
    client = MagicMock()
    client.messages.create.return_value = message
    return client


def _patch_claude(payload: dict):
    """
    Patch address_forge.converter.anthropic with a fake module that returns payload.
    Usage:
        with _patch_claude(payload):
            result = convert(...)
    """
    fake_anthropic = _make_fake_anthropic()
    fake_anthropic.Anthropic.return_value = _make_mock_client(payload)
    return patch.object(converter_module, "anthropic", fake_anthropic)


# ---------------------------------------------------------------------------
# Shared payloads
# ---------------------------------------------------------------------------

UK_STANDARD_PAYLOAD = {
    "address_type": "ADDR",
    "street_name": "Baker Street",
    "building_number": "221B",
    "post_code": "NW1 6XE",
    "town_name": "London",
    "country": "GB",
    "address_lines": [],
    "confidence": {
        "street_name": 0.99,
        "building_number": 0.99,
        "post_code": 0.98,
        "town_name": 0.99,
        "country": 1.0,
    },
}

UK_FLAT_PAYLOAD = {
    "address_type": "ADDR",
    "building_number": "Flat 3B",
    "building_name": "Riverside House",
    "street_name": "Thames Embankment",
    "post_code": "SE1 7PB",
    "town_name": "London",
    "country": "GB",
    "address_lines": [],
    "confidence": {
        "street_name": 0.97,
        "building_number": 0.95,
        "post_code": 0.99,
        "town_name": 0.99,
        "country": 1.0,
    },
}

UK_POSTCODE_VARIANT_PAYLOAD = {
    "address_type": "ADDR",
    "building_number": "10",
    "street_name": "Downing Street",
    "post_code": "SW1A 2AA",
    "town_name": "London",
    "country_sub_division": "Greater London",
    "country": "GB",
    "address_lines": [],
    "confidence": {
        "street_name": 0.99,
        "building_number": 1.0,
        "post_code": 1.0,
        "town_name": 1.0,
        "country": 1.0,
    },
}

US_STANDARD_PAYLOAD = {
    "address_type": "ADDR",
    "building_number": "1600",
    "street_name": "Pennsylvania Avenue NW",
    "town_name": "Washington",
    "country_sub_division": "DC",
    "post_code": "20500",
    "country": "US",
    "address_lines": [],
    "confidence": {
        "street_name": 0.99,
        "building_number": 1.0,
        "post_code": 0.99,
        "town_name": 0.99,
        "country": 1.0,
    },
}

US_PO_BOX_PAYLOAD = {
    "address_type": "PBOX",
    "post_box": "12345",
    "town_name": "New York",
    "country_sub_division": "NY",
    "post_code": "10001",
    "country": "US",
    "address_lines": [],
    "confidence": {"post_code": 0.95, "town_name": 0.99, "country": 1.0},
}

US_ZIP4_PAYLOAD = {
    "address_type": "ADDR",
    "building_number": "350",
    "street_name": "Fifth Avenue",
    "town_name": "New York",
    "country_sub_division": "NY",
    "post_code": "10118-0110",
    "country": "US",
    "address_lines": [],
    "confidence": {
        "street_name": 0.98,
        "building_number": 0.99,
        "post_code": 0.97,
        "town_name": 0.99,
        "country": 1.0,
    },
}

DE_STANDARD_PAYLOAD = {
    "address_type": "ADDR",
    "street_name": "Unter den Linden",
    "building_number": "77",
    "post_code": "10117",
    "town_name": "Berlin",
    "country": "DE",
    "address_lines": [],
    "confidence": {
        "street_name": 0.99,
        "building_number": 0.99,
        "post_code": 0.99,
        "town_name": 0.99,
        "country": 1.0,
    },
}

DE_MUNICH_PAYLOAD = {
    "address_type": "ADDR",
    "street_name": "Marienplatz",
    "building_number": "1",
    "post_code": "80331",
    "town_name": "München",
    "country": "DE",
    "address_lines": [],
    "confidence": {
        "street_name": 0.99,
        "building_number": 0.99,
        "post_code": 0.98,
        "town_name": 0.99,
        "country": 1.0,
    },
}

FR_STANDARD_PAYLOAD = {
    "address_type": "ADDR",
    "building_number": "1",
    "street_name": "Rue de Rivoli",
    "post_code": "75001",
    "town_name": "Paris",
    "country": "FR",
    "address_lines": [],
    "confidence": {
        "street_name": 0.98,
        "building_number": 0.99,
        "post_code": 0.99,
        "town_name": 1.0,
        "country": 1.0,
    },
}

FR_LYON_PAYLOAD = {
    "address_type": "ADDR",
    "building_number": "20",
    "street_name": "Place Bellecour",
    "post_code": "69002",
    "town_name": "Lyon",
    "country": "FR",
    "address_lines": [],
    "confidence": {
        "street_name": 0.97,
        "building_number": 0.99,
        "post_code": 0.99,
        "town_name": 0.99,
        "country": 1.0,
    },
}


# ---------------------------------------------------------------------------
# UK Address Tests (3 cases)
# ---------------------------------------------------------------------------


class TestUKAddressParsing:
    def test_uk_standard_address(self):
        """221B Baker Street — the canonical test address."""
        with _patch_claude(UK_STANDARD_PAYLOAD):
            result = convert("221B Baker Street, London NW1 6XE, UK")

        assert result.success
        assert isinstance(result.address, PostalAddress24)
        assert result.address.street_name == "Baker Street"
        assert result.address.building_number == "221B"
        assert result.address.post_code == "NW1 6XE"
        assert result.address.town_name == "London"
        assert result.address.country == "GB"

    def test_uk_flat_apartment_address(self):
        """Flat/apartment number goes into building_number."""
        with _patch_claude(UK_FLAT_PAYLOAD):
            result = convert(
                "Flat 3B, Riverside House, Thames Embankment, London SE1 7PB"
            )

        assert result.success
        assert result.address.building_number == "Flat 3B"
        assert result.address.building_name == "Riverside House"
        assert result.address.street_name == "Thames Embankment"
        assert result.address.country == "GB"

    def test_uk_postcode_with_country_subdivision(self):
        """SW1A 2AA format — full postcode with country_sub_division."""
        with _patch_claude(UK_POSTCODE_VARIANT_PAYLOAD):
            result = convert("10 Downing Street, London SW1A 2AA")

        assert result.success
        assert result.address.post_code == "SW1A 2AA"
        assert result.address.country == "GB"
        assert result.address.building_number == "10"
        assert result.address.street_name == "Downing Street"


# ---------------------------------------------------------------------------
# US Address Tests (3 cases)
# ---------------------------------------------------------------------------


class TestUSAddressParsing:
    def test_us_standard_address(self):
        """Standard US address with state in country_sub_division."""
        with _patch_claude(US_STANDARD_PAYLOAD):
            result = convert("1600 Pennsylvania Avenue NW, Washington, DC 20500")

        assert result.success
        assert result.address.building_number == "1600"
        assert result.address.street_name == "Pennsylvania Avenue NW"
        assert result.address.town_name == "Washington"
        assert result.address.country_sub_division == "DC"
        assert result.address.post_code == "20500"
        assert result.address.country == "US"

    def test_us_po_box_address(self):
        """PO Box → address_type=PBOX, post_box field populated."""
        with _patch_claude(US_PO_BOX_PAYLOAD):
            result = convert("PO Box 12345, New York, NY 10001")

        assert result.success
        assert result.address.post_box == "12345"
        assert result.address.town_name == "New York"
        assert result.address.country == "US"

    def test_us_zip_plus_4(self):
        """ZIP+4 format (10118-0110) stored in post_code."""
        with _patch_claude(US_ZIP4_PAYLOAD):
            result = convert("350 Fifth Avenue, New York, NY 10118-0110")

        assert result.success
        assert result.address.post_code == "10118-0110"
        assert result.address.country == "US"
        assert result.address.country_sub_division == "NY"


# ---------------------------------------------------------------------------
# German Address Tests (2 cases)
# ---------------------------------------------------------------------------


class TestGermanAddressParsing:
    def test_de_berlin_standard(self):
        """German address: Unter den Linden 77, Berlin."""
        with _patch_claude(DE_STANDARD_PAYLOAD):
            result = convert("Unter den Linden 77, 10117 Berlin, Deutschland")

        assert result.success
        assert result.address.street_name == "Unter den Linden"
        assert result.address.building_number == "77"
        assert result.address.post_code == "10117"
        assert result.address.town_name == "Berlin"
        assert result.address.country == "DE"

    def test_de_munich_umlaut_town_name(self):
        """München with umlaut preserved in town_name."""
        with _patch_claude(DE_MUNICH_PAYLOAD):
            result = convert("Marienplatz 1, 80331 München")

        assert result.success
        assert result.address.town_name == "München"
        assert result.address.country == "DE"
        assert result.address.post_code == "80331"


# ---------------------------------------------------------------------------
# French Address Tests (2 cases)
# ---------------------------------------------------------------------------


class TestFrenchAddressParsing:
    def test_fr_paris_standard(self):
        """Standard Paris address."""
        with _patch_claude(FR_STANDARD_PAYLOAD):
            result = convert("1 Rue de Rivoli, 75001 Paris, France")

        assert result.success
        assert result.address.street_name == "Rue de Rivoli"
        assert result.address.building_number == "1"
        assert result.address.post_code == "75001"
        assert result.address.town_name == "Paris"
        assert result.address.country == "FR"

    def test_fr_lyon_address(self):
        """Lyon address — non-Paris French city."""
        with _patch_claude(FR_LYON_PAYLOAD):
            result = convert("20 Place Bellecour, 69002 Lyon")

        assert result.success
        assert result.address.town_name == "Lyon"
        assert result.address.country == "FR"
        assert result.address.post_code == "69002"


# ---------------------------------------------------------------------------
# Country code detection
# ---------------------------------------------------------------------------


class TestCountryCodeDetection:
    def test_country_code_is_iso_alpha2(self):
        """Country code on the model must always be 2 uppercase letters."""
        for payload in [
            UK_STANDARD_PAYLOAD,
            US_STANDARD_PAYLOAD,
            DE_STANDARD_PAYLOAD,
            FR_STANDARD_PAYLOAD,
        ]:
            with _patch_claude(payload):
                result = convert("any address string")
            assert result.success
            assert len(result.address.country) == 2
            assert result.address.country.isupper()

    def test_confidence_scores_attached_to_result(self):
        """Confidence dict from Claude response is available on ConversionResult."""
        with _patch_claude(UK_STANDARD_PAYLOAD):
            result = convert("221B Baker Street, London")

        assert isinstance(result.confidence, dict)
        assert "country" in result.confidence
        assert 0.0 <= result.confidence["country"] <= 1.0


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


class TestErrorHandling:
    def test_malformed_json_returns_error_result(self):
        """If Claude returns non-JSON text, convert() returns a failed ConversionResult."""
        fake_anthropic = _make_fake_anthropic()
        content_block = MagicMock()
        content_block.text = "Sorry, I cannot parse that address."
        message = MagicMock()
        message.content = [content_block]
        fake_anthropic.Anthropic.return_value.messages.create.return_value = message

        with patch.object(converter_module, "anthropic", fake_anthropic):
            result = convert("not a real address")

        assert result.success is False
        assert result.address is None
        assert result.error is not None
        assert "JSON" in result.error or "parse" in result.error.lower()

    def test_api_exception_returns_error_result(self):
        """If the Anthropic API raises, convert() returns a failed ConversionResult."""
        fake_anthropic = _make_fake_anthropic()
        fake_anthropic.Anthropic.return_value.messages.create.side_effect = Exception(
            "Connection timeout"
        )

        with patch.object(converter_module, "anthropic", fake_anthropic):
            result = convert("221B Baker Street, London")

        assert result.success is False
        assert "Claude API call failed" in result.error
        assert "Connection timeout" in result.error

    def test_missing_mandatory_fields_in_response_returns_error(self):
        """If Claude omits town_name (mandatory), the Pydantic model fails → error result."""
        bad_payload = {
            "street_name": "Baker Street",
            "building_number": "221B",
            "country": "GB",
            # town_name deliberately missing
            "address_lines": [],
            "confidence": {},
        }
        with _patch_claude(bad_payload):
            result = convert("221B Baker Street, London")

        assert result.success is False
        assert result.error is not None

    def test_no_api_key_raises_value_error(self):
        """If no API key is set, a ValueError is raised (SDK present but key missing)."""
        fake_anthropic = _make_fake_anthropic()
        saved = os.environ.pop("ANTHROPIC_API_KEY", None)
        try:
            with patch.object(converter_module, "anthropic", fake_anthropic):
                with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
                    convert("221B Baker Street, London", api_key=None)
        finally:
            if saved:
                os.environ["ANTHROPIC_API_KEY"] = saved


# ---------------------------------------------------------------------------
# convert_to_xml
# ---------------------------------------------------------------------------


class TestConvertToXml:
    def test_convert_to_xml_returns_xml_string(self):
        pytest.importorskip("lxml")
        with _patch_claude(UK_STANDARD_PAYLOAD):
            xml = convert_to_xml("221B Baker Street, London NW1 6XE, UK")

        assert isinstance(xml, str)
        assert "PstlAdr" in xml
        assert "London" in xml
        assert "GB" in xml

    def test_convert_to_xml_contains_mandatory_fields(self):
        pytest.importorskip("lxml")
        with _patch_claude(UK_STANDARD_PAYLOAD):
            xml = convert_to_xml("221B Baker Street, London NW1 6XE")

        assert "TwnNm" in xml
        assert "Ctry" in xml

    def test_convert_to_xml_raises_on_conversion_failure(self):
        pytest.importorskip("lxml")
        fake_anthropic = _make_fake_anthropic()
        content_block = MagicMock()
        content_block.text = "not json"
        message = MagicMock()
        message.content = [content_block]
        fake_anthropic.Anthropic.return_value.messages.create.return_value = message

        with patch.object(converter_module, "anthropic", fake_anthropic):
            with pytest.raises(ValueError):
                convert_to_xml("bad address")


# ---------------------------------------------------------------------------
# convert_batch
# ---------------------------------------------------------------------------


class TestConvertBatch:
    def test_convert_batch_returns_one_result_per_input(self):
        payloads = [UK_STANDARD_PAYLOAD, US_STANDARD_PAYLOAD, DE_STANDARD_PAYLOAD]
        address_strings = [
            "221B Baker Street, London NW1 6XE",
            "1600 Pennsylvania Avenue NW, Washington DC 20500",
            "Unter den Linden 77, 10117 Berlin",
        ]

        call_count = 0

        def fake_convert(address_string, **kwargs):
            nonlocal call_count
            payload = payloads[call_count]
            call_count += 1
            data = {
                k: v for k, v in payload.items() if k != "confidence" and v is not None
            }
            confidence = payload.get("confidence", {})
            addr = PostalAddress24(**data)
            return ConversionResult(
                address=addr,
                raw_input=address_string,
                raw_llm_response=json.dumps(payload),
                confidence=confidence,
            )

        with patch("address_forge.converter.convert", side_effect=fake_convert):
            results = convert_batch(address_strings)

        assert len(results) == 3

    def test_convert_batch_handles_partial_failures(self):
        """Batch continues even if one address fails."""
        good_result = ConversionResult(
            address=PostalAddress24(town_name="London", country="GB"),
            raw_input="London",
            raw_llm_response="{}",
            confidence={},
        )
        bad_result = ConversionResult(
            address=None,
            raw_input="???",
            raw_llm_response="not json",
            confidence={},
            error="Parse error",
        )

        with patch(
            "address_forge.converter.convert", side_effect=[good_result, bad_result]
        ):
            results = convert_batch(["London, UK", "???"])

        assert results[0].success is True
        assert results[1].success is False
