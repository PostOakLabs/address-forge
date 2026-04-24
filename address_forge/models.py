"""
PostalAddress24 Pydantic model — ISO 20022 structured address schema.

Defined in the ISO 20022 data dictionary as PostalAddress24, this structure
is mandatory for all cross-border MX messages from SWIFT SR 2026 onward.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field, model_validator


class AddressType(str, Enum):
    """ISO 20022 AddressType2Code values."""

    ADDR = "ADDR"  # Postal address
    PBOX = "PBOX"  # PO Box
    HOME = "HOME"  # Residential address
    BIZZ = "BIZZ"  # Business address
    MLTO = "MLTO"  # Mail-to address
    DLVY = "DLVY"  # Delivery-to address


class PostalAddress24(BaseModel):
    """
    ISO 20022 PostalAddress24 structured address model.

    SR 2026 mandatory fields: TownName (town_name) and Country (country).
    All other fields are optional but increasingly expected by correspondent banks.

    Reference: ISO 20022 Data Dictionary — PostalAddress24
    SWIFT SR 2026 validation: T9351–T9354 error codes
    """

    # Address type (optional)
    address_type: AddressType | None = Field(
        default=None,
        description="ISO 20022 AddressType2Code. Typically ADDR for postal.",
    )

    # Department / sub-department (optional)
    department: str | None = Field(
        default=None,
        max_length=70,
        description="Name of a division in an organisation.",
    )
    sub_department: str | None = Field(
        default=None,
        max_length=70,
        description="Identification of a sub-division in an organisation.",
    )

    # Street-level fields (SR 2026: at least one structured field or TwnNm+Ctry)
    street_name: str | None = Field(
        default=None,
        max_length=70,
        description="Name of a street or thoroughfare.",
    )
    building_number: str | None = Field(
        default=None,
        max_length=16,
        description="Number that identifies the position of a building on a street.",
    )
    building_name: str | None = Field(
        default=None,
        max_length=35,
        description="Name of the building or house.",
    )
    floor: str | None = Field(
        default=None,
        max_length=70,
        description="Floor or storey within a building.",
    )
    post_box: str | None = Field(
        default=None,
        max_length=16,
        description="Numbered box in a post office.",
    )
    room: str | None = Field(
        default=None,
        max_length=70,
        description="Building room number.",
    )

    # Postal code
    post_code: str | None = Field(
        default=None,
        max_length=16,
        description="Identifier for the posting district or zone.",
    )

    # Town / city (MANDATORY from SR 2026)
    town_name: str = Field(
        ...,
        max_length=35,
        description="Name of a built-up area, with defined boundaries. MANDATORY SR 2026.",
    )

    # Town location (optional district/suburb)
    town_location_name: str | None = Field(
        default=None,
        max_length=35,
        description="Specific location name within a town.",
    )

    # District (optional)
    district_name: str | None = Field(
        default=None,
        max_length=35,
        description="Identifies a subdivision within a country sub-division.",
    )

    # Country sub-division (state/province)
    country_sub_division: str | None = Field(
        default=None,
        max_length=35,
        description="Identifies a subdivision of a country (e.g. state, region, county).",
    )

    # Country (MANDATORY from SR 2026) — ISO 3166-1 alpha-2
    country: str = Field(
        ...,
        min_length=2,
        max_length=2,
        pattern=r"^[A-Z]{2}$",
        description="Two-character ISO 3166-1 alpha-2 country code. MANDATORY SR 2026.",
    )

    # Unstructured free-text lines (max 7, will trigger SR 2026 warnings if used alone)
    address_lines: list[str] = Field(
        default_factory=list,
        max_length=7,
        description=(
            "Free-format address lines. Max 7. "
            "Using only address_lines without structured fields will be REJECTED "
            "by SWIFT from SR 2026 (November 2026) onward."
        ),
    )

    # Confidence scores (added by address-forge, not part of ISO 20022 schema)
    _confidence: dict[str, float] | None = None

    @model_validator(mode="after")
    def validate_sr2026_compliance(self) -> "PostalAddress24":
        """Warn if the address relies solely on free-text lines (SR 2026 reject risk)."""
        has_structured = any(
            [
                self.street_name,
                self.building_number,
                self.building_name,
                self.post_code,
                self.town_location_name,
                self.district_name,
                self.country_sub_division,
            ]
        )
        if not has_structured and self.address_lines:
            # This is valid today but will be rejected by SWIFT from Nov 2026
            # Validation errors are surfaced by validator.py, not raised here
            pass
        return self

    def is_structured(self) -> bool:
        """Return True if address has at least one structured field beyond TownName/Country."""
        return any(
            [
                self.street_name,
                self.building_number,
                self.building_name,
                self.post_code,
                self.country_sub_division,
            ]
        )

    def to_xml_dict(self) -> dict:
        """Return a dict of ISO 20022 XML element names → values (non-None only)."""
        mapping = {
            "AdrTp": (
                (
                    self.address_type.value
                    if hasattr(self.address_type, "value")
                    else self.address_type
                )
                if self.address_type
                else None
            ),
            "Dept": self.department,
            "SubDept": self.sub_department,
            "StrtNm": self.street_name,
            "BldgNb": self.building_number,
            "BldgNm": self.building_name,
            "Flr": self.floor,
            "PstBx": self.post_box,
            "Room": self.room,
            "PstCd": self.post_code,
            "TwnNm": self.town_name,
            "TwnLctnNm": self.town_location_name,
            "DstrctNm": self.district_name,
            "CtrySubDvsn": self.country_sub_division,
            "Ctry": self.country,
        }
        result = {k: v for k, v in mapping.items() if v is not None}
        for i, line in enumerate(self.address_lines, 1):
            result[f"AdrLine{i}"] = line
        return result

    model_config = {"use_enum_values": True}
