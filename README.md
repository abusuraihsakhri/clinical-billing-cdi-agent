# Clinical Billing / CDI Rule Demonstrator

### [Open the Live Application →](https://abusuraihsakhri.github.io/clinical-billing-cdi-agent/)

A deterministic Python prototype for testing clinical-documentation workflow mechanics: rule evaluation, CSV batch processing, local audit records, an optional FastAPI interface, and a browser-based demonstration UI.

> **Scope:** This repository does **not** implement validated CMS-HCC coefficients, ICD-10 coding logic, physician-query compliance rules, reimbursement calculations, or a HIPAA de-identification system. The thresholds in the code are demonstration values and must not be used for clinical, coding, or reimbursement decisions.

## What it does

The maintained workflow evaluates four simple conditions:

- primary metric greater than 25
- secondary metric greater than 12
- an explicit priority flag
- configured status keywords such as DISCORDANT, EQUIVOCAL, or SUSPICIOUS

The result is a deterministic review status plus rule alerts. Public legacy class names are retained where practical for compatibility, but names such as HCCRiskWeightCalculatorAgent and PhysicianQuerySynthesizerAgent do not imply that those functions are implemented.

## Browser application

The site/ application provides:

- single-case analysis with a visible **Analyze case** action
- CSV upload, local batch processing, and CSV download
- light mode by default with a dark-mode toggle
- responsive desktop/mobile layout
- client-side Python through Pyodide
- a deterministic JavaScript fallback if the Pyodide runtime cannot load

The browser application does not upload case or CSV content to this repository or to an application server. Pyodide itself is loaded from the jsDelivr CDN, so opening the page requires a network request to that CDN unless the JavaScript fallback is used. Theme preference is stored in browser localStorage.

## Python usage

Python 3.10 or newer is required.

~~~bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[api,test]"
~~~

Run a single case:

~~~bash
clinical-billing-cdi-engine audit \
  --case-id CASE-001 \
  --primary 28.5 \
  --secondary 14.2 \
  --status DISCORDANT
~~~

Process a CSV file:

~~~bash
python cli.py batch -i sample.csv -o results.csv
~~~

Run the optional API:

~~~bash
clinical-billing-cdi-engine serve
~~~

The API exposes /health, /api/audit, and /api/chat. The chat route is a deterministic local response helper; it does not call an external language model.

## Audit and identifier guard

The legacy-compatible workflow includes an in-memory HMAC-SHA256 chained audit log. AUDIT_SECRET_KEY can provide a persistent configured key; otherwise a random process-local key is generated. Integrity verification recomputes record signatures and verifies chain linkage.

The identifier guard blocks a limited set of common direct-identifier patterns. It is a defensive programming aid, **not** a complete HIPAA Safe Harbor implementation and not a substitute for an institutional de-identification pipeline.

## Testing

~~~bash
python -m pytest -p no:zarr -v
python -m compileall -q agents clinical_billing_cdi_agent cdi_sentinel.py cli.py enrichment.py simulator.py
python cli.py batch -i sample.csv -o out_smoke.csv
~~~

GitHub Actions tests Python 3.10 through 3.13, compiles the Python sources, runs the test suite, exercises both CLI paths, checks the browser-compatible Python engine, and verifies the static-site files.

## Repository layout

- clinical_billing_cdi_agent/ — maintained Python package and browser-compatible engine
- agents/ — legacy-compatible rule, API, audit, telemetry, and metrics modules
- cdi_sentinel.py — compatibility facade for the earlier interface
- cli.py — legacy-compatible command-line interface
- site/ — static browser application
- tests/ — regression tests
- .github/workflows/ — CI and GitHub Pages deployment

enrichment.py retains historical public class names as compatibility threshold modules. It does not implement the advanced features suggested by those legacy names.

## Browser compatibility

The static application targets current versions of Chrome, Edge, Firefox, and Safari with WebAssembly and modern JavaScript enabled. If the external Python runtime is unavailable, core single-case and CSV workflows continue through the local JavaScript fallback.

## License

MIT. See [LICENSE](LICENSE).
