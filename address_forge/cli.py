"""
address-forge CLI — convert and validate postal addresses against ISO 20022 SR 2026.

Usage:
    address-forge convert "221B Baker Street, London NW1 6XE, UK"
    address-forge convert "221B Baker Street, London NW1 6XE, UK" --format xml
    address-forge validate '{"town_name": "London", "country": "GB", ...}'
    address-forge validate-csv addresses.csv
    address-forge countries
"""

from __future__ import annotations

import json
import sys

import click

from .converter import convert, convert_batch, convert_to_xml
from .countries import list_supported_countries
from .models import PostalAddress24
from .validator import validate, remediation_report


@click.group()
@click.version_option(package_name="address-forge")
def cli():
    """address-forge — ISO 20022 PostalAddress24 converter and SR 2026 validator."""
    pass


# ---------------------------------------------------------------------------
# convert command
# ---------------------------------------------------------------------------

@cli.command()
@click.argument("address_string")
@click.option(
    "--format",
    "output_format",
    type=click.Choice(["json", "xml", "summary"], case_sensitive=False),
    default="json",
    show_default=True,
    help="Output format.",
)
@click.option(
    "--country-hint",
    default=None,
    metavar="CC",
    help="ISO 3166-1 alpha-2 country code hint to improve parsing (e.g. GB, US, DE).",
)
@click.option(
    "--api-key",
    default=None,
    envvar="ANTHROPIC_API_KEY",
    help="Anthropic API key. Falls back to ANTHROPIC_API_KEY env var.",
)
@click.option(
    "--model",
    default="claude-sonnet-4-20250514",
    show_default=True,
    help="Claude model to use for address parsing.",
)
@click.option(
    "--validate/--no-validate",
    "run_validation",
    default=True,
    show_default=True,
    help="Run SR 2026 validation after conversion and include results in output.",
)
def convert_cmd(address_string, output_format, country_hint, api_key, model, run_validation):
    """
    Convert a free-text ADDRESS_STRING to ISO 20022 PostalAddress24.

    Example:

        address-forge convert "221B Baker Street, London NW1 6XE, UK"
    """
    try:
        if output_format == "xml":
            xml = convert_to_xml(
                address_string,
                country_hint=country_hint,
                api_key=api_key,
                model=model,
            )
            click.echo(xml)
            return

        result = convert(
            address_string,
            country_hint=country_hint,
            api_key=api_key,
            model=model,
        )

        if not result.success:
            click.echo(click.style(f"ERROR: {result.error}", fg="red"), err=True)
            sys.exit(1)

        if output_format == "summary":
            click.echo(click.style("✓ Conversion successful", fg="green"))
            click.echo(f"  Town:    {result.address.town_name}")
            click.echo(f"  Country: {result.address.country}")
            if result.address.street_name:
                bldg = result.address.building_number or ""
                click.echo(f"  Street:  {bldg} {result.address.street_name}".strip())
            if result.address.post_code:
                click.echo(f"  Postcode: {result.address.post_code}")
            if result.confidence:
                click.echo("\n  Confidence scores:")
                for field, score in result.confidence.items():
                    bar = "█" * int(score * 10) + "░" * (10 - int(score * 10))
                    click.echo(f"    {field:20s} {bar} {score:.0%}")

            if run_validation:
                val = validate(result.address)
                click.echo()
                if val.is_valid:
                    click.echo(click.style("✓ SR 2026 validation: PASS", fg="green"))
                else:
                    click.echo(click.style("✗ SR 2026 validation: FAIL", fg="red"))
                for finding in val.all_findings:
                    colour = "red" if finding.severity.value == "ERROR" else (
                        "yellow" if finding.severity.value == "WARNING" else "blue"
                    )
                    click.echo(click.style(f"  {finding}", fg=colour))
        else:
            # JSON output
            output = result.address.model_dump(exclude_none=True)
            if result.confidence:
                output["_confidence"] = result.confidence
            if run_validation:
                val = validate(result.address)
                output["_validation"] = {
                    "is_valid": val.is_valid,
                    "errors": [str(e) for e in val.errors],
                    "warnings": [str(w) for w in val.warnings],
                }
            click.echo(json.dumps(output, indent=2))

    except Exception as exc:
        click.echo(click.style(f"ERROR: {exc}", fg="red"), err=True)
        sys.exit(1)


# ---------------------------------------------------------------------------
# validate command
# ---------------------------------------------------------------------------

@cli.command()
@click.argument("address_json")
def validate_cmd(address_json):
    """
    Validate a PostalAddress24 JSON string against SR 2026 rules.

    Pass a JSON object as ADDRESS_JSON.

    Example:

        address-forge validate '{"town_name": "London", "country": "GB", "street_name": "Baker Street", "building_number": "221B", "post_code": "NW1 6XE"}'
    """
    try:
        data = json.loads(address_json)
        address = PostalAddress24(**data)
    except json.JSONDecodeError as exc:
        click.echo(click.style(f"Invalid JSON: {exc}", fg="red"), err=True)
        sys.exit(1)
    except Exception as exc:
        click.echo(click.style(f"Invalid address data: {exc}", fg="red"), err=True)
        sys.exit(1)

    result = validate(address)
    if result.is_valid:
        click.echo(click.style("✓ SR 2026 validation: PASS", fg="green"))
    else:
        click.echo(click.style("✗ SR 2026 validation: FAIL", fg="red"))

    for finding in result.all_findings:
        colour = "red" if finding.severity.value == "ERROR" else (
            "yellow" if finding.severity.value == "WARNING" else "blue"
        )
        click.echo(click.style(f"  {finding}", fg=colour))

    sys.exit(0 if result.is_valid else 1)


# ---------------------------------------------------------------------------
# validate-csv command
# ---------------------------------------------------------------------------

@cli.command("validate-csv")
@click.argument("csv_path", type=click.Path(exists=True))
@click.option(
    "--address-col",
    default="address",
    show_default=True,
    help="Name of the column containing free-text addresses.",
)
@click.option(
    "--output",
    "-o",
    default=None,
    help="Path to write remediation report. Defaults to stdout.",
)
@click.option(
    "--api-key",
    default=None,
    envvar="ANTHROPIC_API_KEY",
)
def validate_csv_cmd(csv_path, address_col, output, api_key):
    """
    Convert and validate all addresses in a CSV file against SR 2026.

    Reads CSV_PATH, converts each address, validates, and produces a
    remediation report.
    """
    import csv

    with open(csv_path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    if address_col not in (rows[0].keys() if rows else []):
        click.echo(
            click.style(
                f"Column '{address_col}' not found. Available columns: "
                f"{', '.join(rows[0].keys() if rows else [])}",
                fg="red",
            ),
            err=True,
        )
        sys.exit(1)

    address_strings = [row[address_col] for row in rows]
    click.echo(f"Converting {len(address_strings)} addresses…")

    results = convert_batch(address_strings, api_key=api_key)
    failed = [r for r in results if not r.success]
    converted = [r.address for r in results if r.success]

    click.echo(f"Converted: {len(converted)} / {len(address_strings)}")
    if failed:
        click.echo(click.style(f"Failed to convert: {len(failed)}", fg="yellow"))

    report = remediation_report(converted)

    if output:
        with open(output, "w", encoding="utf-8") as f:
            f.write(report)
        click.echo(f"Report written to {output}")
    else:
        click.echo(report)


# ---------------------------------------------------------------------------
# countries command
# ---------------------------------------------------------------------------

@cli.command()
def countries():
    """List countries with defined address parsing rules."""
    codes = list_supported_countries()
    click.echo("Countries with address parsing rules:")
    for code in codes:
        click.echo(f"  {code}")
    click.echo(f"\nTotal: {len(codes)} (contribute more at github.com/PostOakLabs/address-forge)")


def main():
    cli()


if __name__ == "__main__":
    main()
