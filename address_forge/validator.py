"""
SR 2026 address validator — SWIFT-style error codes for PostalAddress24.

Implements SWIFT's SR 2026 structured address validation rules. The error codes
T9351–T9354 mirror FINplus network-level reject codes that will be issued from
November 2026 onward when MX messages contain non-compliant postal addresses.

References:
  - SWIFT SR 2026 Standards Release Notes
  - SWIFT MT-to-MX Address Structured Data Requirements
  - ISO 20022 PostalAddress24 field definitions
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional

from .models import PostalAddress24


class ErrorSeverity(str, Enum):
    ERROR = "ERROR"     # Message will be rejected by SWIFT from SR 2026
    WARNING = "WARNING" # Message may be rejected; remediation strongly recommended
    INFO = "INFO"       # Informational only


@dataclass
class ValidationError:
    """A single validation finding against an SR 2026 rule."""
    code: str
    severity: ErrorSeverity
    field: Optional[str]
    message: str
    remediation: str

    def __str__(self) -> str:
        field_part = f"[{self.field}] " if self.field else ""
        return f"{self.code} {self.severity.value}: {field_part}{self.message}"


@dataclass
class ValidationResult:
    """Aggregate result of validating a PostalAddress24 against SR 2026 rules."""
    errors: list[ValidationError] = field(default_factory=list)
    warnings: list[ValidationError] = field(default_factory=list)
    info: list[ValidationError] = field(default_factory=list)

    @property
    def is_valid(self) -> bool:
        """True if no ERROR-level findings (address will not be rejected by SWIFT)."""
        return len(self.errors) == 0

    @property
    def will_be_rejected(self) -> bool:
        """True if any ERROR-level finding exists that will cause SR 2026 rejection."""
        return len(self.errors) > 0

    @property
    def all_findings(self) -> list[ValidationError]:
        return self.errors + self.warnings + self.info

    def summary(self) -> str:
        lines = [
            f"Validation result: {'PASS' if self.is_valid else 'FAIL'}",
            f"  Errors   (SR 2026 reject): {len(self.errors)}",
            f"  Warnings (remediate soon): {len(self.warnings)}",
            f"  Info:                      {len(self.info)}",
        ]
        for finding in self.all_findings:
            lines.append(f"  {finding}")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# SR 2026 Error Code Definitions
# ---------------------------------------------------------------------------
# T9351: Missing mandatory TownName field
# T9352: Missing mandatory Country field
# T9353: Unstructured address only — no structured fields present
# T9354: Country code is not a valid ISO 3166-1 alpha-2 code
# T9355: Field length exceeds ISO 20022 maximum (address-forge extension)
# T9356: Address line count exceeds maximum of 7 (address-forge extension)

# Recognised ISO 3166-1 alpha-2 country codes (abbreviated for core validation)
# Full list is maintained in address_forge/countries/
_ISO_COUNTRY_CODES = {
    "AD","AE","AF","AG","AI","AL","AM","AO","AQ","AR","AS","AT","AU","AW","AX",
    "AZ","BA","BB","BD","BE","BF","BG","BH","BI","BJ","BL","BM","BN","BO","BQ",
    "BR","BS","BT","BV","BW","BY","BZ","CA","CC","CD","CF","CG","CH","CI","CK",
    "CL","CM","CN","CO","CR","CU","CV","CW","CX","CY","CZ","DE","DJ","DK","DM",
    "DO","DZ","EC","EE","EG","EH","ER","ES","ET","FI","FJ","FK","FM","FO","FR",
    "GA","GB","GD","GE","GF","GG","GH","GI","GL","GM","GN","GP","GQ","GR","GS",
    "GT","GU","GW","GY","HK","HM","HN","HR","HT","HU","ID","IE","IL","IM","IN",
    "IO","IQ","IR","IS","IT","JE","JM","JO","JP","KE","KG","KH","KI","KM","KN",
    "KP","KR","KW","KY","KZ","LA","LB","LC","LI","LK","LR","LS","LT","LU","LV",
    "LY","MA","MC","MD","ME","MF","MG","MH","MK","ML","MM","MN","MO","MP","MQ",
    "MR","MS","MT","MU","MV","MW","MX","MY","MZ","NA","NC","NE","NF","NG","NI",
    "NL","NO","NP","NR","NU","NZ","OM","PA","PE","PF","PG","PH","PK","PL","PM",
    "PN","PR","PS","PT","PW","PY","QA","RE","RO","RS","RU","RW","SA","SB","SC",
    "SD","SE","SG","SH","SI","SJ","SK","SL","SM","SN","SO","SR","SS","ST","SV",
    "SX","SY","SZ","TC","TD","TF","TG","TH","TJ","TK","TL","TM","TN","TO","TR",
    "TT","TV","TW","TZ","UA","UG","UM","US","UY","UZ","VA","VC","VE","VG","VI",
    "VN","VU","WF","WS","XK","YE","YT","ZA","ZM","ZW",
}


def validate(address: PostalAddress24) -> ValidationResult:
    """
    Validate a PostalAddress24 against SWIFT SR 2026 structured address rules.

    Returns a ValidationResult containing any ERROR, WARNING, or INFO findings.
    An ERROR means the message will be rejected by SWIFT from November 2026 onward.
    """
    result = ValidationResult()

    # T9351 — TownName mandatory
    if not address.town_name or not address.town_name.strip():
        result.errors.append(ValidationError(
            code="T9351",
            severity=ErrorSeverity.ERROR,
            field="TwnNm",
            message="TownName (TwnNm) is mandatory in PostalAddress24 from SR 2026.",
            remediation="Populate TwnNm with the town or city name.",
        ))

    # T9352 — Country mandatory
    if not address.country or not address.country.strip():
        result.errors.append(ValidationError(
            code="T9352",
            severity=ErrorSeverity.ERROR,
            field="Ctry",
            message="Country (Ctry) is mandatory in PostalAddress24 from SR 2026.",
            remediation="Populate Ctry with a valid ISO 3166-1 alpha-2 country code.",
        ))

    # T9354 — Country code format (also catches lowercase codes, which are invalid per ISO 3166-1)
    elif address.country != address.country.upper() or address.country.upper() not in _ISO_COUNTRY_CODES:
        result.errors.append(ValidationError(
            code="T9354",
            severity=ErrorSeverity.ERROR,
            field="Ctry",
            message=(
                f"Country code '{address.country}' is not a valid ISO 3166-1 alpha-2 code."
            ),
            remediation=(
                "Use a two-letter uppercase ISO 3166-1 alpha-2 country code "
                "(e.g. GB, US, DE, FR)."
            ),
        ))

    # T9353 — Unstructured address only (will be rejected when no structured fields present)
    if not address.is_structured() and address.address_lines:
        result.errors.append(ValidationError(
            code="T9353",
            severity=ErrorSeverity.ERROR,
            field="AdrLine",
            message=(
                "Address contains only unstructured free-text lines (AdrLine) with no "
                "structured fields. SWIFT will reject this from SR 2026 (November 2026)."
            ),
            remediation=(
                "Add at least one structured field: StrtNm, BldgNb, BldgNm, PstCd, "
                "or CtrySubDvsn alongside TwnNm and Ctry."
            ),
        ))
    elif not address.is_structured() and not address.address_lines:
        # Only TownName and Country — technically valid but very thin
        result.info.append(ValidationError(
            code="I0001",
            severity=ErrorSeverity.INFO,
            field=None,
            message=(
                "Address contains only TownName and Country. "
                "This is SR 2026 compliant but may be rejected by correspondent banks "
                "expecting more detail."
            ),
            remediation="Consider adding StrtNm, BldgNb, and PstCd.",
        ))

    # T9356 — Address line count
    if len(address.address_lines) > 7:
        result.errors.append(ValidationError(
            code="T9356",
            severity=ErrorSeverity.ERROR,
            field="AdrLine",
            message=(
                f"Address has {len(address.address_lines)} AdrLine entries; "
                "ISO 20022 PostalAddress24 allows a maximum of 7."
            ),
            remediation="Reduce the number of free-text address lines to 7 or fewer.",
        ))

    # W0001 — Address lines present alongside structured fields (mixed address)
    if address.is_structured() and address.address_lines:
        result.warnings.append(ValidationError(
            code="W0001",
            severity=ErrorSeverity.WARNING,
            field="AdrLine",
            message=(
                "Address mixes structured fields with free-text AdrLine entries. "
                "This is a 'hybrid' address — allowed but some institutions may reject it."
            ),
            remediation=(
                "Prefer fully structured addresses. Remove AdrLine entries if all "
                "information is captured in structured fields."
            ),
        ))

    # W0002 — Missing post code (expected for most countries)
    if not address.post_code and address.country in {
        "GB", "US", "DE", "FR", "NL", "BE", "CH", "AT", "AU", "CA", "JP", "SG"
    }:
        result.warnings.append(ValidationError(
            code="W0002",
            severity=ErrorSeverity.WARNING,
            field="PstCd",
            message=(
                f"No PostCode (PstCd) provided for country '{address.country}'. "
                "Most correspondent banks require a post code for this country."
            ),
            remediation=f"Add the postal code for the {address.country} address.",
        ))

    # W0003 — Missing street name (likely to cause downstream enrichment failures)
    if not address.street_name and not address.address_lines and not address.post_box:
        result.warnings.append(ValidationError(
            code="W0003",
            severity=ErrorSeverity.WARNING,
            field="StrtNm",
            message=(
                "No StreetName (StrtNm), AddressLine, or PostBox provided. "
                "Address may be insufficient for delivery or correspondent bank processing."
            ),
            remediation="Add StrtNm and BldgNb for the full address.",
        ))

    return result


def validate_batch(addresses: list[PostalAddress24]) -> list[ValidationResult]:
    """Validate a list of PostalAddress24 objects. Returns a result per address."""
    return [validate(addr) for addr in addresses]


def remediation_report(addresses: list[PostalAddress24]) -> str:
    """
    Generate a plain-text remediation report for a batch of addresses.
    Summarises how many will be rejected and what needs to be fixed.
    """
    results = validate_batch(addresses)
    total = len(results)
    will_reject = sum(1 for r in results if r.will_be_rejected)
    lines = [
        "=" * 60,
        "PostOakLabs address-forge — SR 2026 Remediation Report",
        "=" * 60,
        f"Total addresses analysed : {total}",
        f"Will be rejected (ERROR)  : {will_reject}",
        f"Pass                      : {total - will_reject}",
        "",
    ]
    for i, (addr, result) in enumerate(zip(addresses, results), 1):
        if result.all_findings:
            lines.append(f"Address {i}: {addr.town_name}, {addr.country}")
            for finding in result.all_findings:
                lines.append(f"  {finding}")
            lines.append("")
    return "\n".join(lines)
