"""
Country-specific address rules for address-forge.

Each country module defines validation hints and formatting notes
that are injected into the LLM prompt to improve parsing accuracy.
"""

from __future__ import annotations

from importlib import import_module


def get_country_rules(country_code: str) -> str | None:
    """
    Return country-specific address parsing rules for the given ISO 3166-1 alpha-2 code.
    Returns None if no rules are defined for the country.
    """
    code = country_code.upper()
    try:
        module = import_module(f".{code.lower()}", package=__name__)
        return getattr(module, "RULES", None)
    except ModuleNotFoundError:
        return None


def list_supported_countries() -> list[str]:
    """Return ISO 3166-1 alpha-2 codes for countries with defined rules."""
    # Enumerate known modules — extend as more countries are added
    return ["GB"]
