# address-forge

**ISO 20022 structured address cleansing & validation for SWIFT SR 2026 compliance.**

A developer tool — web UI, CLI, and REST API — that converts free-text postal addresses into `PostalAddress24`-compliant structured format and validates them against SWIFT's November 2026 rejection rules.

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

### CLI

```bash
pip install address-forge

# Single address
address-forge convert "221B Baker Street, London, NW1 6XE, United Kingdom"

# Bulk CSV
address-forge validate --input addresses.csv --output report.json
```

### REST API

```bash
docker run -p 8080:8080 postoaklabs/address-forge

curl -X POST http://localhost:8080/v1/convert \
  -H "Content-Type: application/json" \
  -d '{"address": "221B Baker Street, London, NW1 6XE, United Kingdom"}'
```

**Response:**

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

### Web sandbox

A hosted sandbox is available at **[address-forge.postoaklabs.io](https://address-forge.postoaklabs.io)** *(coming soon)*

- Paste any address → see ISO 20022 XML output → edit inline
- Free tier: 100 addresses/day

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

- [x] Single address conversion (CLI + REST)
- [x] SR 2026 field validation
- [x] Bulk CSV processing
- [ ] SWIFT FINplus error code output
- [ ] Batch REST API with API key auth
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
