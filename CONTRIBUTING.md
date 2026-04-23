# Contributing to address-forge

Thanks for taking the time to contribute. This project is early-stage and every issue report, edge case, and pull request matters significantly.

---

## Ways to contribute

You don't need to write code to contribute meaningfully:

- **Submit a failing address** — if you paste an address into the tool and the output is wrong or incomplete, open an issue with the input and what you expected. Real-world address edge cases are the most valuable thing you can give this project right now.
- **Report an SR 2026 rule we're missing** — if you work in payments compliance and know of a SWIFT validation rule that isn't covered, open an issue describing it.
- **Improve documentation** — if something in the README or field mapping table is unclear or incorrect, a PR fixing it is just as welcome as a code change.
- **Write code** — see the roadmap in the README for prioritized work items.

---

## Opening an issue

Before opening an issue, search existing issues to see if it's already been reported.

When reporting a **bad conversion**, please include:
- The raw input address string
- The output you received
- The output you expected
- The country the address is from

When reporting a **validation error**, please include:
- The ISO 20022 message snippet (redact any real counterparty data)
- The error code produced
- Why you believe it's incorrect

---

## Setting up locally

### Requirements

- Python 3.11 or higher
- `pip`
- Docker (optional, for running the REST API locally)

### Steps

```bash
# 1. Fork the repo on GitHub, then clone your fork
git clone https://github.com/YOUR_USERNAME/address-forge.git
cd address-forge

# 2. Create a virtual environment
python -m venv .venv
source .venv/bin/activate        # Mac/Linux
.venv\Scripts\activate           # Windows

# 3. Install dependencies including dev tools
pip install -e ".[dev]"

# 4. Run the test suite to confirm everything works
pytest
```

If all tests pass, you're ready to make changes.

---

## Making a change

```bash
# Create a branch named for what you're fixing or adding
git checkout -b fix/uk-postcode-parsing

# Make your changes, then run tests
pytest

# Commit with a short, descriptive message
git commit -m "fix: handle UK postcodes with space omitted"

# Push to your fork
git push origin fix/uk-postcode-parsing
```

Then open a Pull Request from your fork to the `main` branch of this repo.

---

## Pull request guidelines

- **One change per PR.** A PR that fixes a UK postcode bug and also refactors the validator is harder to review and slower to merge.
- **Include a test.** If you're fixing a conversion bug, add the failing address as a test case so it can't regress.
- **Update the docs if needed.** If your change affects the field mapping table, error codes, or CLI behavior, update the README or relevant doc file in the same PR.
- **Don't open a PR for work in progress.** Use a draft PR if you want early feedback on an approach before it's ready to merge.

---

## Commit message format

Use the conventional commits style — it keeps the history readable:

| Prefix | Use for |
|---|---|
| `fix:` | Bug fix |
| `feat:` | New feature or capability |
| `docs:` | Documentation only |
| `test:` | Adding or correcting tests |
| `refactor:` | Code change with no behavior change |
| `chore:` | Dependency updates, CI config, tooling |

Examples:
```
fix: correctly extract building number for French addresses
feat: add T9354 hybrid address validation error code
docs: clarify PostalAddress24 AdrLine deprecation note
```

---

## Code style

- Python: formatted with `black`, linted with `ruff`. Both run automatically if you install the dev dependencies.
- Run `black . && ruff check .` before committing — CI will fail if either reports errors.
- Type hints are required for all public functions.

---

## Adding a new country's address rules

Country-specific postal format support is a priority roadmap item. If you want to add support for a new country:

1. Add a file at `address_forge/countries/{iso2_country_code}.py`
2. Implement the `parse(raw: str) -> PostalAddress24` function
3. Add at least 10 test cases covering common formats for that country, including edge cases (PO boxes, rural addresses, addresses missing postcodes)
4. Document any country-specific SR 2026 quirks in `docs/country-notes/{iso2_country_code}.md`

---

## Questions

Open a GitHub Discussion if you're unsure about an approach before building it. Issues are for bugs and concrete feature requests; Discussions are for everything else.
