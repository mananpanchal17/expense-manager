# Expense Manager

A complete Flask + SQLite learning project for a first-year B.Tech CSE student. It uses an application factory, SQLAlchemy models, Flask blueprints, Bootstrap 5, and Chart.js. **Start here**, then read `SCHEMA.md` and `SOURCE_CODE.md` for the full code, file by file.

## 1. Folder structure

```text
expense_manager/
├── app/
│   ├── __init__.py             # Application factory, errors, CLI commands
│   ├── extensions.py           # Shared database, login, CSRF, rate limiter
│   ├── models.py               # Six database tables
│   ├── forms.py                # Server-side form validation
│   ├── services.py             # Reusable business logic
│   ├── auth/
│   │   ├── __init__.py
│   │   └── routes.py           # Accounts, sessions, password reset, profile
│   ├── expenses/
│   │   ├── __init__.py
│   │   └── routes.py           # Transactions, categories, budgets, recurring, import
│   ├── reports/
│   │   ├── __init__.py
│   │   └── routes.py           # Dashboard, chart JSON, reports, CSV/PDF export
│   ├── templates/
│   │   ├── base.html
│   │   ├── macros.html
│   │   ├── auth/{form,profile}.html
│   │   ├── expenses/{form,index,categories,budgets,recurring,import}.html
│   │   ├── reports/{dashboard,report}.html
│   │   └── errors/error.html
│   └── static/
│       ├── css/style.css
│       ├── js/{theme,app,charts}.js
│       └── fonts/{DejaVuSans.ttf,LICENSE-DejaVu.txt}
├── tests/
│   ├── conftest.py
│   ├── test_auth.py
│   ├── test_expenses.py
│   └── test_security.py
├── .vscode/                   # One-click VS Code setup, run and test tasks
├── config.py
├── run.py
├── setup_windows.bat          # First-time Windows setup
├── run_windows.bat            # Windows launcher
├── requirements.txt
├── pytest.ini
├── .env.example
├── .gitignore
├── sample_transactions.csv
├── README.md
├── SCHEMA.md
├── VALIDATION.md
└── SOURCE_CODE.md
```

`instance/expenses.db` is created on your machine. `.env`, the database, and your virtual environment are intentionally excluded from the source package.

## 2. Run locally

Use **Python 3.12** (the version tested). Python 3.12 or later is recommended. Bootstrap and Chart.js load from jsDelivr, so the browser needs internet for those assets; transactions and server-rendered reports do not depend on Chart.js.

### Windows PowerShell

#### Easiest method in VS Code

1. Open the extracted `expense_manager` folder in VS Code. Do not open the ZIP itself or its parent folder.
2. Double-click `setup_windows.bat` in File Explorer. Wait for **Setup completed successfully**.
3. Double-click `run_windows.bat`.
4. Open `http://127.0.0.1:5000` in your browser and create an account.

You can also run everything inside VS Code: press **Ctrl+Shift+P**, choose **Tasks: Run Task**, then select **Expense Manager: First-time setup** followed by **Expense Manager: Run**. After setup, the **Run and Debug** panel also contains **Run Expense Manager**.

If a script fails, leave its window open and copy or photograph the last error lines. The scripts do not require PowerShell activation and do not change PowerShell's execution policy.

#### Manual method

Extract the ZIP, open its `expense_manager` folder in VS Code, and open a terminal:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
python -c "import secrets; print(secrets.token_hex(32))"
```

Paste the generated string after `SECRET_KEY=` in `.env`, save, then run:

```powershell
python -m flask --app run init-db
python -m flask --app run run --debug
```

Open **http://127.0.0.1:5000** and click **Create account**. Use a password of at least 10 characters. No default administrator or shared demo account is included.

If PowerShell blocks activation, no policy change is necessary. Use the virtual environment's Python directly:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m flask --app run init-db
.\.venv\Scripts\python.exe -m flask --app run run --debug
```

### macOS / Linux

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
python -c 'import secrets; print(secrets.token_hex(32))'
```

Paste the result into `.env` as `SECRET_KEY`, then:

```bash
python -m flask --app run init-db
python -m flask --app run run --debug
```

`--debug` is for your own computer only. Stop the development server with Ctrl+C. `python run.py` also runs the app, with debug disabled.

### First five minutes

1. Register and log in.
2. Add income using the Salary category, then add an expense using Food.
3. Open Budgets and set a Food limit for the same month as your expense.
4. Add another expense to reach 80% or 100%; check the warning and progress bar.
5. Try date and amount filters, edit a transaction, and export the filtered rows.
6. Import `sample_transactions.csv` if you want sample data. Its dates are October 2026, so select that period in Reports if your current month is different.

## 3. Features and behaviour

| Area | Implemented behaviour |
|---|---|
| Transactions | Add, edit, delete, view income and expenses; amount, category, date, payment method, notes |
| Categories | Add, rename and delete; each user has independent defaults and custom categories |
| Budgets | One limit per user/category/month; create or update by saving the same category/month; delete; warnings at >=80% and >=100% |
| Search | Notes and category name; date range, category, type, minimum/maximum amount |
| Sorting | Newest, oldest, highest amount, lowest amount, category A–Z; 20 records per page |
| Recurring | Weekly, monthly and yearly expense rules; edit, pause, delete; catch up overdue occurrences |
| Export | All matching rows to CSV; up to 2,000 matching rows to a paginated PDF |
| Import | UTF-8 CSV, up to 2 MB and 2,000 rows; validates all rows before writing any |
| Dashboard | Lifetime income, expenses and balance; current calendar month's spend; three Chart.js charts |
| Reports | Monthly/yearly category totals; yearly month-by-month table; CSV/PDF links for the selected period |
| Accounts | Register, login, logout, remember me, reset password, profile, delete account, latest 100 activity events |
| Appearance | Responsive Bootstrap layout, light/dark theme persisted in the browser, flash messages and error pages |

**Budget semantics:** expense totals alone count toward the limit; income does not reduce spending. Budgets are calendar-month specific and do not automatically carry forward. Warnings are shown after relevant writes and persist on the dashboard/budget page while the threshold is met; they are not email notifications. Budgets are advisory and do not prevent spending.

**Dates and totals:** recurring generation and “this month” use `APP_TIMEZONE` (default `Asia/Kolkata`). Activity timestamps are UTC. Lifetime totals include all manually entered dates, including future-dated transactions. Current-month totals include the entire calendar month.

**Currency:** this is a single-currency ledger per user, initially INR. USD, EUR and GBP are also available. Changing the display currency relabels existing values; it does **not** perform exchange-rate conversion. The amount field always supports two decimal places.

**Categories:** an in-use category cannot be deleted. Reassign/delete its transactions and remove its budgets/recurring rules first. The database makes category names unique per user, with SQLite's ASCII case-insensitive comparison.

## 4. Recurring expenses

Create a rule under **Recurring**. The first/next due date determines when the first transaction is created. Rule creation itself does not generate transactions.

- Click **Generate due expenses** to process the signed-in user's due rules.
- To automate every user's rules, run this command daily using a scheduler:

```bash
/path/to/expense_manager/.venv/bin/python -m flask --app run generate-recurring
```

Run it with the project folder as the working directory. For Linux cron, a daily example is:

```cron
0 1 * * * cd /path/to/expense_manager && /path/to/expense_manager/.venv/bin/python -m flask --app run generate-recurring
```

The scheduler's timezone controls when it starts; the app's timezone determines which dates are due. The server and scheduler must be running for unattended generation. No background scheduler starts inside Flask workers.

Generation catches up missed dates. January 31 becomes February 28/29, then March 31. A February 29 yearly rule returns to February 29 in leap years. A conditional database update claims a due occurrence, and a unique occurrence constraint provides an additional duplicate guard. Re-running the command does not duplicate entries.

Pausing retains the next date; reactivating catches up from that date unless you move it forward. Editing a rule affects future generation only. Its next due date cannot move backwards. Deleting a rule keeps generated transactions as ordinary entries. Deleting a generated transaction does not recreate it on the next normal run because the rule has already advanced.

## 5. Password reset and email

### Local development

Keep `MAIL_MODE=console`. Request a reset from **Forgot password**. The link appears in the terminal running Flask. It is never returned in the browser response. Anyone who can read those local logs can use that development link.

### SMTP delivery

Configure your email provider's SMTP details in `.env`:

```dotenv
MAIL_MODE=smtp
MAIL_SERVER=smtp.your-provider.example
MAIL_PORT=587
MAIL_USERNAME=your-smtp-user
MAIL_PASSWORD=your-smtp-password-or-app-password
MAIL_FROM=verified-sender@your-domain.example
MAIL_USE_TLS=true
APP_BASE_URL=https://your-actual-domain.example
```

This implementation supports SMTP with STARTTLS on a provider-supported port such as 587. It does not implement implicit TLS/SMTP_SSL on port 465. Use your provider's verified sender and credentials. A delivery failure is logged without exposing credentials and the browser still receives a generic response to avoid revealing whether an email has an account.

Tokens expire after 30 minutes. They contain a user ID and a signed session version, not the password. A successful reset rotates the version so the link cannot be reused and all old sessions/remember cookies stop working. Changing your email or password in Profile also revokes old sessions. Email ownership verification at registration is a future improvement; reset delivery itself does require access to the mailbox.

## 6. CSV import and export

Use exactly these six columns, in any order:

```csv
kind,amount,category,date,payment_method,notes
expense,120.50,Food,2026-10-30,UPI,Lunch
income,5000.00,Salary,2026-10-30,Bank transfer,Allowance
```

- `kind`: `income` or `expense`.
- `amount`: positive decimal, maximum `999999999.99`; do not use currency signs or thousands separators.
- `category`: an existing category belonging to the signed-in user.
- `date`: ISO `YYYY-MM-DD`, year 1900–9998.
- `payment_method`: `Cash`, `UPI`, `Debit card`, `Credit card`, `Bank transfer`, or `Other`.
- `notes`: plain text, maximum 500 characters; quote fields containing commas or line breaks using standard CSV quoting.

A validation error identifies the row. No rows are saved unless all rows validate. Importing the same file twice **creates duplicates**; deduplication is not implemented.

CSV export applies the current filters and includes all matching pages. Text starting with spreadsheet formula markers is prefixed with an apostrophe for spreadsheet safety. That prefix is not stripped on reimport; unusual category names starting with such markers may require editing the exported category cell before importing.

PDF export applies the same filters and includes totals plus each transaction. It uses a bundled DejaVu Sans font with its license. This improves common Unicode support but does not provide full Indic-script shaping or emoji coverage. Filter large exports to stay below the 2,000-row PDF limit.

## 7. Security implemented

- Werkzeug's salted password hashing; no plaintext password column.
- Flask-Login sessions; 14-day optional remember cookie; sensitive profile/delete operations require a fresh login and current password.
- Global Flask-WTF CSRF protection on state-changing requests. Search and report filter forms use GET and do not require tokens.
- Server-side form validation, bounded lengths/ranges, and normalization of emails and text. Notes remain text, and Jinja auto-escapes output.
- SQLAlchemy queries with bound parameters. Sort columns come from an explicit whitelist; no user-provided SQL is constructed.
- Record ownership checks in every private CRUD path and user-specific category choices on every form, including imports.
- Login limits: 10 POSTs/minute and 50/hour per IP; a 15-minute account lockout after five failed attempts. Registration and password reset have additional limits.
- HttpOnly and SameSite=Lax session/remember cookies. Set `COOKIE_SECURE=true` for HTTPS deployment.
- Secret key and SMTP configuration read from `.env`; `.env` is excluded from Git and the source archive.
- Security headers: CSP, frame blocking, MIME sniffing protection, same-origin referrer policy; HSTS when secure cookies are enabled.
- Sensitive pages use `Cache-Control: no-store`; reset links use the configured base URL, not the incoming Host header.
- Spreadsheet formula protection on CSV export and XML escaping in PDF output.
- Account-owned activity logs; account deletion removes owned rows through SQLAlchemy cascades.

Production startup rejects insecure cookies, console mail, a non-HTTPS base URL, and in-memory rate-limit storage. Configure a shared backend such as `rediss://...` for Redis, reachable from every worker. Behind a proxy, the current key is the address exposed to Flask; do not trust arbitrary `X-Forwarded-For` headers. If your host does not expose the real client address, configure a trusted proxy layer with the exact documented hop count before using IP limits at scale.

This project has tested security controls; it has not undergone an external penetration test. Optional TOTP two-factor authentication is **not implemented**.

## 8. File-by-file learning guide

| File | What it teaches |
|---|---|
| `run.py` | The entry point: imports the factory and exposes a WSGI `app` object. |
| `config.py` | Reads environment variables, sets database path, mail, cookie and timezone settings. |
| `app/__init__.py` | `create_app()` configures an application, attaches extensions, registers blueprints and adds CLI/error handlers. |
| `app/extensions.py` | Defines reusable extension objects before any application exists, avoiding circular imports. |
| `app/models.py` | SQLAlchemy classes describe database tables, relationships, constraints and password methods. |
| `app/forms.py` | WTForms fields and validators reject invalid data even when browser validation is bypassed. |
| `app/services.py` | Common business functions: ownership, money conversion, budget totals, recurrence, reset tokens and filtered queries. |
| `app/auth/__init__.py`, `app/expenses/__init__.py`, `app/reports/__init__.py` | Empty package markers that make these directories importable Python packages. |
| `app/auth/routes.py` | Maps account URLs to registration/login/profile/reset handlers. |
| `app/expenses/routes.py` | Handles user-owned CRUD, monthly budgets, recurring rules and atomic CSV validation. |
| `app/reports/routes.py` | Aggregates numbers, returns chart JSON, renders reports and builds downloads. |
| `templates/base.html` | Shared HTML shell, responsive navigation, theme control, flash messages and assets. |
| `templates/macros.html` | Reusable form, delete-button, summary-card and transaction-table components. |
| `templates/auth/form.html` | Shared registration, login, reset and account deletion screen. |
| `templates/auth/profile.html` | Profile editing and the activity log. |
| `templates/expenses/index.html` | Transaction filters, exports, table and pagination. |
| `templates/expenses/form.html` | Shared editor for transactions, categories and recurring rules. |
| `templates/expenses/categories.html` | Add/rename/delete category interface. |
| `templates/expenses/budgets.html` | Month selection, budget editing and accessible progress indicators. |
| `templates/expenses/recurring.html` | Rule creation/list, edit/pause/delete and generation button. |
| `templates/expenses/import.html` | CSV upload form, column examples and import behaviour. |
| `templates/reports/dashboard.html` | Summary cards, chart canvases, budget warnings and recent transactions. |
| `templates/reports/report.html` | Monthly/yearly report selectors and tables. |
| `templates/errors/error.html` | Shared friendly 400/404/413/429/500 error layout. |
| `static/css/style.css` | Colours, spacing, responsive cards, charts and light/dark styling. |
| `static/js/theme.js` | Loads the saved theme before the page paints. |
| `static/js/app.js` | Theme toggle and confirmation prompts; security still lives on the server. |
| `static/js/charts.js` | Fetches JSON and draws category pie, expense trend line and income/expense bar charts. |
| `static/fonts/DejaVuSans.ttf` | Bundled Unicode PDF font; `LICENSE-DejaVu.txt` carries its license. |
| `tests/conftest.py` | Builds a fresh temporary SQLite app and reusable test clients/data. |
| `tests/test_auth.py` | Account creation, hashing, login/logout, lockout, reset, profile and deletion tests. |
| `tests/test_expenses.py` | CRUD, isolation, filters, budgets, recurrence, imports and exports. |
| `tests/test_security.py` | CSRF, XSS escaping, headers, errors and login rate-limit checks. |
| `requirements.txt` | Exact Python package versions used for validation, including dependencies. |
| `pytest.ini` | Test discovery and import path settings. |
| `.env.example` | Safe configuration template; copy it and provide your own secret. |
| `.gitignore` | Keeps secrets, local databases, caches and virtual environments out of Git. |
| `sample_transactions.csv` | Small example import with default category names. |
| `SCHEMA.md` | All tables, important columns, relationships and data decisions. |
| `VALIDATION.md` | Test results and exactly what has or has not been verified. |
| `SOURCE_CODE.md` | The full text source collected file by file for study. |

### Follow one request

When you submit **Add transaction**:

1. The browser sends form fields and a CSRF token to `/expenses/add`.
2. Flask-Login checks your session and Flask-WTF checks the token.
3. `TransactionForm` validates the amount, date and your category choices.
4. The route converts `120.50` to integer `12050` and assigns your `user_id`.
5. SQLAlchemy inserts the transaction and activity event in a database transaction.
6. The route checks budgets, flashes feedback, and redirects to the list.
7. Jinja renders the updated page, escaping notes so they cannot run as HTML.

## 9. Run the tests

```bash
python -m pytest -q
```

Tests use temporary SQLite databases and never touch your real database. Most functional tests disable CSRF to focus on the feature; dedicated security tests turn it back on and verify both rejection and acceptance of tokens. Tests cover cross-user ID access, invalid amounts, lockout, reset expiry and reuse, recurrence boundaries, all-or-nothing CSV import, and PDF output. Exact final results and verification limits are recorded in `VALIDATION.md`.

Run a syntax check if you edit the Python code:

```bash
python -m compileall -q app config.py run.py
```

## 10. Deploy to PythonAnywhere

These steps use PythonAnywhere's existing-Flask-app workflow, verified against the official documentation. You need a hosting plan/network setup that can reach your SMTP provider and shared Redis backend; this guide does not assume those services are available on a free plan.

1. Upload and extract the project under `/home/YOUR_USERNAME/expense_manager`.
2. Create a Python 3.12 virtual environment in the PythonAnywhere Bash console and install the requirements:

```bash
cd /home/YOUR_USERNAME/expense_manager
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python -c 'import secrets; print(secrets.token_hex(32))'
```

3. Put the generated secret and your actual production values into `.env`:

```dotenv
APP_ENV=production
SECRET_KEY=YOUR_FRESH_RANDOM_SECRET
COOKIE_SECURE=true
APP_BASE_URL=https://YOUR_USERNAME.pythonanywhere.com
APP_TIMEZONE=Asia/Kolkata
DATABASE_URL=sqlite:////home/YOUR_USERNAME/expense_manager/instance/expenses.db
RATELIMIT_STORAGE_URI=rediss://YOUR_REDIS_CONNECTION_DETAILS
MAIL_MODE=smtp
MAIL_SERVER=YOUR_SMTP_HOST
MAIL_PORT=587
MAIL_USERNAME=YOUR_SMTP_USERNAME
MAIL_PASSWORD=YOUR_SMTP_PASSWORD
MAIL_FROM=YOUR_VERIFIED_SENDER
MAIL_USE_TLS=true
```

4. Ensure `instance/` exists, then initialize the tables:

```bash
mkdir -p instance
python -m flask --app run init-db
```

5. In **Web → Add a new web app**, select **Manual configuration** and the same Python version as your virtual environment. Set the virtualenv path to `/home/YOUR_USERNAME/expense_manager/.venv`.
6. Edit the site's WSGI file to import this app:

```python
import sys

project_path = '/home/YOUR_USERNAME/expense_manager'
if project_path not in sys.path:
    sys.path.insert(0, project_path)

from run import app as application
```

7. Configure `/static/` to serve `/home/YOUR_USERNAME/expense_manager/app/static/`. Enable HTTPS/force HTTPS for the site, then reload it from the Web tab. Never expose Flask's debug server in production.
8. Use your account's scheduled-task facility, if available, to run the daily recurring command from section 4 with the actual project path and virtualenv Python. Test it once from the Bash console first.
9. Check account creation, login/logout, a transaction, CSRF-enabled forms, PDF export, a real password-reset email and recurrence on the deployed site. Check the host's error logs if anything fails.

Keep `SECRET_KEY` stable across restarts; changing it invalidates sessions and reset links. Back up the SQLite database regularly while writes are paused, or use SQLite's backup API. `init-db` creates missing tables but does not migrate an existing schema. Before changing models for a deployed project, add Alembic/Flask-Migrate and a migration workflow.

SQLite suits a small learning deployment. For many simultaneous writers, plan a PostgreSQL migration, adapt SQLite-specific collation/engine settings, and add migration tests. A deployment using ephemeral storage must have a persistent disk for SQLite; this is why the included walkthrough uses PythonAnywhere's persistent project storage.

Official references:

- https://help.pythonanywhere.com/pages/Flask/
- https://help.pythonanywhere.com/pages/VirtualEnvForWebsites/
- https://flask-limiter.readthedocs.io/en/stable/configuration.html
- https://flask-wtf.readthedocs.io/en/latest/csrf/
- https://flask-login.readthedocs.io/en/0.6.3/#alternative-tokens

## 11. Troubleshooting

| Symptom | Fix |
|---|---|
| Secret key error | Copy `.env.example` to `.env`, set a newly generated key of at least 32 characters, restart Flask. |
| `no such table` | Run `python -m flask --app run init-db` in the project folder. |
| Login fails after several attempts | Wait 15 minutes or reset your password. |
| Reset email not received locally | In console mode, look at the Flask terminal; for SMTP, verify credentials, sender and host logs. |
| CSRF error | Reload the form, keep cookies enabled and submit again. |
| Cannot log in on local HTTP | Use `COOKIE_SECURE=false` locally; secure cookies require HTTPS. |
| Cannot edit profile after browser restart | Remembered sessions need a fresh login before sensitive changes. |
| Charts missing | Check CDN connectivity and the chart-data request; reports still provide numeric tables. |
| CSV rejected | Use the exact headers, existing categories, UTF-8, valid dates and positive two-decimal amounts. |
| Recurring transactions missing | Click Generate due expenses, or configure/run the daily CLI job. |

## 12. Future improvements

1. Optional TOTP 2FA with encrypted secrets and recovery codes.
2. Email ownership verification and asynchronous email delivery.
3. Alembic migrations, PostgreSQL and stronger database-level tenant constraints.
4. Import preview, duplicate detection and per-row import history.
5. Real multi-currency amounts and explicit exchange-rate conversion.
6. Receipt uploads/OCR, saving goals and budget rollover.
7. A dedicated job queue, monitoring, backups and broader browser/accessibility testing.
8. Locally hosted frontend assets, a stricter CSP and additional language/font support.
