"""
Tests for address_forge.validator — SR 2026 rule checks and SWIFT error codes.

Covers:
  - Valid address passes with no errors
  - T9351: missing TownName
  - T9352: missing Country
  - T9353: unstructured-only address (AdrLine with no structured fields)
  - T9354: invalid ISO 3166-1 alpha-2 country code
  - Multiple simultaneous errors
  - W0001: hybrid address warning
  - W0002: missing postcode warning for known countries
  - batch validation
  - remediation_report output
"""

import pytest

from address_forge.models import PostalAddress24
from address_forge.validator import (
    ErrorSeverity,
    ValidationError,
    validate,
    validate_batch,
    remediation_report,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_address(**kwargs) -> PostalAddress24:
    """Build a minimal valid PostalAddress24, overriding with kwargs."""
    defaults = dict(
        town_name="London",
        country="GB",
        street_name="Baker Street",
        building_number="221B",
        post_code="NW1 6XE",
    )
    defaults.update(kwargs)
    return PostalAddress24(**defaults)


def _error_codes(result) -> list[str]:
    return [e.code for e in result.errors]


def _warning_codes(result) -> list[str]:
    return [w.code for w in result.warnings]


# ---------------------------------------------------------------------------
# 1. Valid address — clean pass
# ---------------------------------------------------------------------------

class TestValidAddress:
    def test_fully_structured_uk_address_passes(self):
        address = _make_address()
        result = validate(address)
        assert result.is_valid
        assert result.will_be_rejected is False
        assert result.errors == []

    def test_minimal_valid_address_town_and_country_only(self):
        """TownName + Country alone is technically SR 2026 compliant."""
        address = PostalAddress24(town_name="Berlin", country="DE")
        result = validate(address)
        assert result.is_valid
        # Should get an INFO about thin address, not an ERROR
        info_codes = [i.code for i in result.info]
        assert "I0001" in info_codes

    def test_is_valid_property(self):
        address = _make_address()
        result = validate(address)
        assert result.is_valid is True


# ---------------------------------------------------------------------------
# 2. T9351 — missing TownName
# ---------------------------------------------------------------------------

class TestT9351MissingTownName:
    def test_missing_town_name_triggers_t9351(self):
        # Pydantic requires town_name, so we bypass via model_construct
        address = PostalAddress24.model_construct(
            town_name="",
            country="GB",
            street_name="Baker Street",
            building_number="221B",
            post_code="NW1 6XE",
            address_lines=[],
        )
        result = validate(address)
        assert "T9351" in _error_codes(result)
        assert result.will_be_rejected is True

    def test_whitespace_town_name_triggers_t9351(self):
        address = PostalAddress24.model_construct(
            town_name="   ",
            country="GB",
            street_name="High Street",
            building_number="1",
            address_lines=[],
        )
        result = validate(address)
        assert "T9351" in _error_codes(result)

    def test_t9351_error_has_correct_severity(self):
        address = PostalAddress24.model_construct(
            town_name="",
            country="FR",
            address_lines=[],
        )
        result = validate(address)
        t9351 = next(e for e in result.errors if e.code == "T9351")
        assert t9351.severity == ErrorSeverity.ERROR
        assert t9351.field == "TwnNm"


# ---------------------------------------------------------------------------
# 3. T9352 — missing Country
# ---------------------------------------------------------------------------

class TestT9352MissingCountry:
    def test_missing_country_triggers_t9352(self):
        address = PostalAddress24.model_construct(
            town_name="Paris",
            country="",
            street_name="Rue de Rivoli",
            building_number="1",
            address_lines=[],
        )
        result = validate(address)
        assert "T9352" in _error_codes(result)
        assert result.will_be_rejected is True

    def test_t9352_error_field_is_ctry(self):
        address = PostalAddress24.model_construct(
            town_name="Munich",
            country="",
            address_lines=[],
        )
        result = validate(address)
        t9352 = next(e for e in result.errors if e.code == "T9352")
        assert t9352.field == "Ctry"
        assert t9352.severity == ErrorSeverity.ERROR


# ---------------------------------------------------------------------------
# 4. T9353 — unstructured address only
# ---------------------------------------------------------------------------

class TestT9353UnstructuredOnly:
    def test_address_lines_only_triggers_t9353(self):
        """An address with only free-text lines and no structured fields → T9353."""
        address = PostalAddress24.model_construct(
            town_name="London",
            country="GB",
            address_lines=["221B Baker Street", "Marylebone"],
            street_name=None,
            building_number=None,
            building_name=None,
            post_code=None,
            country_sub_division=None,
        )
        result = validate(address)
        assert "T9353" in _error_codes(result)
        assert result.will_be_rejected is True

    def test_structured_fields_present_no_t9353(self):
        """If any structured field is present, T9353 must NOT fire."""
        address = _make_address(address_lines=["c/o John Smith"])
        result = validate(address)
        assert "T9353" not in _error_codes(result)

    def test_t9353_remediation_text_mentions_structured_fields(self):
        address = PostalAddress24.model_construct(
            town_name="Manchester",
            country="GB",
            address_lines=["1 Piccadilly Gardens"],
            street_name=None,
            building_number=None,
            building_name=None,
            post_code=None,
            country_sub_division=None,
        )
        result = validate(address)
        t9353 = next(e for e in result.errors if e.code == "T9353")
        assert "StrtNm" in t9353.remediation or "structured" in t9353.remediation.lower()


# ---------------------------------------------------------------------------
# 5. T9354 — invalid country code
# ---------------------------------------------------------------------------

class TestT9354InvalidCountryCode:
    def test_invalid_country_code_triggers_t9354(self):
        address = PostalAddress24.model_construct(
            town_name="London",
            country="XX",
            street_name="Baker Street",
            building_number="221B",
            address_lines=[],
        )
        result = validate(address)
        assert "T9354" in _error_codes(result)

    def test_lowercase_country_code_triggers_t9354(self):
        """Validator expects uppercase; lowercase is invalid per ISO 3166-1."""
        address = PostalAddress24.model_construct(
            town_name="Berlin",
            country="de",
            street_name="Unter den Linden",
            building_number="1",
            address_lines=[],
        )
        result = validate(address)
        assert "T9354" in _error_codes(result)

    def test_valid_country_codes_do_not_trigger_t9354(self):
        for code in ["GB", "US", "DE", "FR", "SG", "JP", "AU"]:
            address = _make_address(country=code)
            result = validate(address)
            assert "T9354" not in _error_codes(result), f"T9354 incorrectly fired for {code}"


# ---------------------------------------------------------------------------
# 6. Multiple simultaneous errors
# ---------------------------------------------------------------------------

class TestMultipleSimultaneousErrors:
    def test_missing_town_and_country_returns_two_errors(self):
        address = PostalAddress24.model_construct(
            town_name="",
            country="",
            street_name="Baker Street",
            address_lines=[],
        )
        result = validate(address)
        codes = _error_codes(result)
        assert "T9351" in codes
        assert "T9352" in codes
        assert len(result.errors) >= 2

    def test_unstructured_and_invalid_country_returns_multiple_errors(self):
        address = PostalAddress24.model_construct(
            town_name="London",
            country="ZZ",
            address_lines=["Some free text line"],
            street_name=None,
            building_number=None,
            building_name=None,
            post_code=None,
            country_sub_division=None,
        )
        result = validate(address)
        codes = _error_codes(result)
        assert "T9354" in codes
        assert "T9353" in codes
        assert result.will_be_rejected is True


# ---------------------------------------------------------------------------
# 7. Warnings
# ---------------------------------------------------------------------------

class TestWarnings:
    def test_w0001_hybrid_address_warning(self):
        """Structured fields + address_lines → W0001 warning."""
        address = _make_address(address_lines=["Floor 12"])
        result = validate(address)
        assert "W0001" in _warning_codes(result)

    def test_w0002_missing_postcode_for_gb(self):
        address = PostalAddress24.model_construct(
            town_name="London",
            country="GB",
            street_name="Baker Street",
            building_number="221B",
            post_code=None,
            address_lines=[],
        )
        result = validate(address)
        assert "W0002" in _warning_codes(result)

    def test_w0002_not_fired_for_country_without_postcode_expectation(self):
        """W0002 should not fire for a country not in the known-postcode-required set."""
        address = PostalAddress24.model_construct(
            town_name="Nairobi",
            country="KE",
            street_name="Kenyatta Avenue",
            building_number="1",
            post_code=None,
            address_lines=[],
        )
        result = validate(address)
        assert "W0002" not in _warning_codes(result)


# ---------------------------------------------------------------------------
# 8. Batch validation
# ---------------------------------------------------------------------------

class TestBatchValidation:
    def test_validate_batch_returns_one_result_per_address(self):
        addresses = [
            _make_address(),
            _make_address(town_name="Paris", country="FR"),
            _make_address(town_name="Berlin", country="DE"),
        ]
        results = validate_batch(addresses)
        assert len(results) == 3

    def test_validate_batch_mixed_valid_invalid(self):
        valid = _make_address()
        invalid = PostalAddress24.model_construct(
            town_name="",
            country="GB",
            address_lines=[],
        )
        results = validate_batch([valid, invalid])
        assert results[0].is_valid is True
        assert results[1].is_valid is False


# ---------------------------------------------------------------------------
# 9. Remediation report
# ---------------------------------------------------------------------------

class TestRemediationReport:
    def test_remediation_report_contains_totals(self):
        addresses = [
            _make_address(),
            PostalAddress24.model_construct(
                town_name="",
                country="XX",
                address_lines=["Some text"],
                street_name=None,
                building_number=None,
                building_name=None,
                post_code=None,
                country_sub_division=None,
            ),
        ]
        report = remediation_report(addresses)
        assert "Total addresses analysed" in report
        assert "Will be rejected" in report

    def test_remediation_report_string_output(self):
        addresses = [_make_address()]
        report = remediation_report(addresses)
        assert isinstance(report, str)
        assert len(report) > 0


# ---------------------------------------------------------------------------
# 10. ValidationResult helpers
# ---------------------------------------------------------------------------

class TestValidationResultHelpers:
    def test_all_findings_combines_errors_warnings_info(self):
        address = PostalAddress24(town_name="London", country="GB")
        result = validate(address)
        assert len(result.all_findings) == len(result.errors) + len(result.warnings) + len(result.info)

    def test_summary_returns_string(self):
        address = _make_address()
        result = validate(address)
        summary = result.summary()
        assert isinstance(summary, str)
        assert "PASS" in summary or "FAIL" in summary
