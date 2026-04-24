"""
address-forge — ISO 20022 PostalAddress24 converter and SR 2026 validator.

Converts free-text postal addresses to structured ISO 20022 PostalAddress24
format using Claude API, and validates them against SWIFT SR 2026 requirements.

Quick start:
    from address_forge import convert, validate

    result = convert("221B Baker Street, London NW1 6XE, UK")
    if result.success:
        print(result.address.town_name)   # London
        print(result.address.country)     # GB

    validation = validate(result.address)
    print(validation.is_valid)            # True

GitHub: https://github.com/PostOakLabs/address-forge
"""

__version__ = "0.1.0"
__author__ = "PostOakLabs"
__license__ = "MIT"

from .converter import convert, convert_batch, convert_to_xml, ConversionResult
from .models import PostalAddress24, AddressType
from .validator import validate, validate_batch, remediation_report, ValidationResult

__all__ = [
    # Conversion
    "convert",
    "convert_batch",
    "convert_to_xml",
    "ConversionResult",
    # Validation
    "validate",
    "validate_batch",
    "remediation_report",
    "ValidationResult",
    # Models
    "PostalAddress24",
    "AddressType",
]
