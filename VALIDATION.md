# Validation report

Validated on 30 October 2026 with Python 3.12.14 and the exact package versions in `requirements.txt`.

## Automated checks

- `python -m pytest -q`: **28 passed** (final run: 9.04 seconds).
- `python -m compileall -q app config.py run.py`: passed.
- `node --check` for all three JavaScript files: passed.
- `python -m pip check`: no broken requirements.
- Local `flask --app run init-db`: succeeded.

The tests cover account registration, duplicate email handling, hashing, login, remember-me logout, lockout/expiry, time-limited and single-use reset tokens, invalidation of old sessions, generic forgot-password responses, profile password confirmation, account deletion, expense/income CRUD, exact monetary storage, invalid inputs, cross-user ownership protection, filters/sorting, category management, budgets at 80%/100%, recurring catch-up and month-end/leap-year logic, simultaneous recurring jobs, paused rules, atomic CSV imports, filtered CSV export, spreadsheet formula escaping, PDF export with long notes and multiple pages, dashboard/report rendering, chart JSON, CSRF rejection and valid-token workflows, XSS escaping, security headers, custom 404/500 errors, oversized uploads, and rate limits.

Third-party deprecation warnings remain: Flask-Login 0.6.3 uses `datetime.utcnow()` for remember-cookie expiry, and WTForms 3.3.1 warns about tuple-style select choices. The pinned versions work and all tests pass. Review their migration notes before upgrading these dependencies.

## Verification limits

- Browser visual/layout QA was attempted, but the available preview runtime could not execute Python. Responsive CSS, rendered pages and form behaviour were checked through source review and Flask's test client; visual rendering and Chart.js canvas interaction were not browser-verified.
- SMTP delivery was not exercised against a real mail provider; tests stub delivery while exercising token logic and browser flows. Configure and test your actual provider before deploying.
- No live host deployment was performed. The included PythonAnywhere instructions were checked against official documentation.
- Production Redis connectivity was not exercised. Login rate limiting was tested with an isolated in-memory backend; production startup requires a shared backend.
- Optional TOTP 2FA is not implemented.

The package includes no working credentials, default user accounts, virtual environment, or transaction database.
