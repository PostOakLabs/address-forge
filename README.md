# address-forge

**ISO 20022 structured address cleansing & validation for SWIFT SR 2026 compliance.**

A developer tool that converts free-text postal addresses into `PostalAddress24`-compliant structured format and validates them against SWIFT's November 2026 rejection rules.

**Shipped: CLI.** A REST API and web UI are designed but not built yet — see [Status](#status).

---

## Why this exists

SWIFT's SR 2026 update (effective November 2026) will **reject** any cross-border MX message that contains only an unstructured postal address. Every party and agent block must use structured or hybrid address format, with `TownName` and `Country` as mandatory fields.

Every bank, payment processor, corporate treasury, and fintech using FINplus for cross-border payments has to solve this. Mid-tier institutions have no affordable tool. The current options are manual remediation, expensive vendor projects, or one-off internal scripts.

`address-forge` is the missing open-source layer.

---

## What it does

**Parse & convert**
- Input: free-text address string, JSON object, or CSV bulk upload
- Output: valid `PostalAddress24` XML block + JSON equivalent, with per-field confidence scores

**Validate against SR 2026 rules**
- Flags addresses using only free-text lines (will be rejected post-November 2026)
- Confirms `TownName` and `Country` are present and correctly structured
- Generates SWIFT-style validation error codes mirroring FINplus error messages

**Remediation reporting**
- Bulk analysis: "47 of 1,200 addresses will be rejected — here are the corrections"
- Export corrected records to CSV or JSON

---

## Quick start

### CLI (shipped)

```bash
pip install address-forge

# Single address
address-forge convert "221B Baker Street, London, NW1 6XE, United Kingdom"

# Bulk CSV
address-forge validate --input addresses.csv --output report.json
```

## Status

| Surface | State |
|---|---|
| CLI (`address-forge convert` / `validate` / `validate-csv` / `countries`) | **Shipped.** See `address_forge/cli.py`. |
| REST API | **Not built.** `fastapi`/`uvicorn` are declared as optional dependencies in `pyproject.toml` for the planned service, but no server module exists in this repo yet. The example below is the target shape, not a working endpoint. |
| Web sandbox | **Not built.** No hosted sandbox exists at this time. |

Planned REST API shape (target, not yet implemented):

```bash
# NOT YET IMPLEMENTED
docker run -p 8080:8080 postoaklabs/address-forge

curl -X POST http://localhost:8080/v1/convert \
  -H "Content-Type: application/json" \
  -d '{"address": "221B Baker Street, London, NW1 6XE, United Kingdom"}'
```

Target response shape:

```json
{
  "PostalAddress24": {
    "StrtNm": "Baker Street",
    "BldgNb": "221B",
    "TwnNm": "London",
    "PstCd": "NW1 6XE",
    "Ctry": "GB"
  },
  "confidence": {
    "StrtNm": 0.98,
    "BldgNb": 0.99,
    "TwnNm": 0.99,
    "PstCd": 0.97,
    "Ctry": 1.0
  },
  "sr2026_compliant": true,
  "validation_errors": []
}
```

---

## PostalAddress24 field mapping

| ISO 20022 Field | Description | SR 2026 Mandatory |
|---|---|---|
| `StrtNm` | Street name | No |
| `BldgNb` | Building number | No |
| `BldgNm` | Building name | No |
| `Flr` | Floor | No |
| `PstBx` | PO Box | No |
| `PstCd` | Post code | No |
| `TwnNm` | Town name | **Yes** |
| `TwnLctnNm` | Town location name | No |
| `DstrctNm` | District name | No |
| `CtrySubDvsn` | Country subdivision | No |
| `Ctry` | Country (ISO 3166-1 alpha-2) | **Yes** |
| `AdrLine` | Unstructured line (max 2, flagged) | Deprecated |

---

## SR 2026 validation error codes

`address-forge` generates validation errors in SWIFT FINplus format so they can be surfaced directly in your existing message validation pipeline:

| Code | Meaning |
|---|---|
| `T9351` | Unstructured address only — TownName missing |
| `T9352` | Country code missing or invalid |
| `T9353` | AdrLine count exceeds SR 2026 limit |
| `T9354` | Hybrid address missing mandatory structured fields |

---

## Roadmap

- [x] Single address conversion (CLI)
- [x] SR 2026 field validation (CLI)
- [x] Bulk CSV processing (CLI)
- [x] SWIFT FINplus error code output (CLI, codes `T9351`–`T9354`)
- [ ] REST API (no server module in this repo yet — `fastapi`/`uvicorn` are declared but unused)
- [ ] Web sandbox UI
- [ ] Address deduplication & normalisation across bulk uploads
- [ ] Country-specific postal format rules (UK, US, DE, FR, JP, AU)
- [ ] Integration plugin for Finastra, Temenos, Form3

---

## Contributing

Pull requests are welcome. If you're a payment operations engineer, compliance analyst, or fintech developer working on SR 2026 remediation, your real-world address edge cases are invaluable — please open an issue.

See [CONTRIBUTING.md](CONTRIBUTING.md) for setup instructions.

---

## License

MIT License. See [LICENSE](LICENSE).

---

## About PostOakLabs

PostOakLabs builds open-source developer tooling at the intersection of ISO 20022, tokenized assets, and A2A payments. See also:

- [`iso20022-token-bridge`](https://github.com/PostOakLabs/iso20022-token-bridge) — ISO 20022 ↔ tokenized MMF middleware
- [`a2a-iso-gateway`](https://github.com/PostOakLabs/a2a-iso-gateway) — Open banking A2A → ISO 20022 translator
- [`mmf-token-sandbox`](https://github.com/PostOakLabs/mmf-token-sandbox) — Tokenized MMF developer playground
