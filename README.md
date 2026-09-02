# Data-Mapping-ROPA

A database-backed Record of Processing Activities (ROPA) tool, built as
Project 2 of a portfolio for a transition into Data Governance & Privacy
Analyst work.

## Why this project exists

Most companies maintain their ROPA — the document that maps what personal
data they process, why, on what legal basis, who they share it with, and
how long they keep it — as a static Word document or spreadsheet that
someone updates by hand, if it gets updated at all. That approach doesn't
scale, is hard to search or filter, and produces a document that's already
stale by the time an auditor or regulator asks to see it.

This project is the tool a privacy analyst would actually want instead:
processing activities are entered once as structured, related database
records, and the ROPA — plus its filtered views and PDF/CSV exports — is
generated automatically from that data every time it's needed.

It's the operational counterpart to a separate legal-comparison project in
this portfolio (LGPD/GDPR/CCPA side-by-side): that one shows the legal
research skill, this one shows the "build the tool the team runs on" skill.

## What it does

- **Structured data model**: processing activities are linked to reusable
  data categories, a legal basis, one or more recipients (internal teams or
  third parties, flagged for international transfers), and a retention
  period — instead of free-text fields repeated everywhere.
- **Django admin as the data-entry tool**: a privacy team maintains records
  the same way over time, without needing a custom UI just to add a row.
- **Dashboard**: every processing activity at a glance, in one filterable,
  searchable table — the "auto-generated ROPA" that replaces the manual
  spreadsheet.
- **Filters**: by data category, legal basis, or whether an activity
  involves an international/cross-border data transfer (relevant under
  both GDPR and LGPD).
- **One-click export**: the current (filtered or full) view exports to a
  ready-to-hand-over PDF or CSV, simulating handing a document to an
  auditor or regulator on demand.
- **Automated risk flag**: any activity that combines a sensitive data
  category with an undefined legal basis and/or retention period is
  visually flagged — surfacing exactly the kind of documentation gap a
  real risk assessment needs to catch, not just listing data.

## Tech stack

- **Backend**: Django 5/6, SQLite (development database)
- **Frontend**: Django templates, plain CSS, a few lines of vanilla JS
  (no frontend framework — kept intentionally simple)
- **PDF export**: [ReportLab](https://www.reportlab.com/) (pure Python,
  no native/GTK dependencies — chosen over WeasyPrint specifically for
  smooth setup on Windows)
- **CSV export**: Python's built-in `csv` module

## A note on legal content

All company, department, and vendor names in the seed data are fictional
(a made-up e-commerce company, "NimbusCart"). Legal basis labels are
generic categories (Consent, Contract Necessity, Legitimate Interest,
Legal Obligation), not legal advice for any real situation. Retention
periods are illustrative placeholders — they are **not** asserted as
legally required durations. Anywhere a real retention period or legal
threshold would normally need to come from a specific statute, the code
carries a `# TODO: VERIFY legal retention standard against official
source` comment instead of a stated-as-fact number (see
`ropa/models.py` and `ropa/management/commands/seed_ropa.py`).

## Running it locally

```bash
# 1. Clone/enter the project directory, then create a virtual environment
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux

# 2. Install dependencies
pip install -r requirements.txt

# 3. Set up the database
python manage.py migrate

# 4. Load the sample ROPA data (10 fictional processing activities)
python manage.py seed_ropa

# 5. Create an admin login (choose your own username/password here —
#    there is no preset admin account in this repo)
python manage.py createsuperuser

# 6. Run the server
python manage.py runserver
```

By default the app runs with a development-only fallback secret key and
`DEBUG=True`, so the steps above work with zero configuration. To
override them (required before any real deployment — see **Security
notes** below), copy `.env.example` to `.env` and fill in real values,
or set `DJANGO_SECRET_KEY` / `DJANGO_DEBUG` / `DJANGO_ALLOWED_HOSTS` as
environment variables directly.

Then visit:

- **Dashboard**: <http://127.0.0.1:8000/>
- **Admin (data entry)**: <http://127.0.0.1:8000/admin/>
- **About**: <http://127.0.0.1:8000/about/>

Re-running `python manage.py seed_ropa` clears and reloads the sample
data (pass `--keep` to add to existing records instead).

## Project structure

```
config/                        Django project settings & root URLs
ropa/                           The ROPA app
  models.py                     DataCategory, LegalBasis, DataRecipient,
                                 RetentionPeriod, ProcessingActivity
  admin.py                      Django admin configuration
  views.py                      Dashboard, filters, about, export views
  exports.py                    CSV and PDF export logic
  management/commands/
    seed_ropa.py                 Fictional sample data for NimbusCart
  templates/ropa/                Dashboard, about, and base templates
static/                          CSS and JS
.env.example                     Environment variables this app reads (copy to .env)
```

## Security notes

- `SECRET_KEY`, `DEBUG`, and `ALLOWED_HOSTS` are read from environment
  variables (`DJANGO_SECRET_KEY`, `DJANGO_DEBUG`, `DJANGO_ALLOWED_HOSTS`)
  with dev-only fallbacks — see `config/settings.py` and `.env.example`.
  Never commit a real `.env` file (it's already git-ignored).
- There is no admin account bundled with this repo or its seed data —
  `createsuperuser` (step 5 above) is interactive and always asks you to
  set your own username/password.
- `db.sqlite3` is git-ignored. Sample/seed data lives in
  `ropa/management/commands/seed_ropa.py`, not in the database file, so
  nothing sensitive is at risk of being committed.

## Deployment (not yet set up)

For a live demo link on a resume, this app is a good fit for a free-tier
Django host such as **Render** or **PythonAnywhere** (swap SQLite for
Render's free Postgres if using Render). Deployment is intentionally not
configured yet, pending a content review of the seed data and About
page — see the `# TODO` markers in `ropa/templates/ropa/about.html`.

## Author

Built by Gustavo Valença, a Brazilian-trained lawyer with legal team
leadership experience transitioning into Data Governance & Privacy
Analyst work in the US, as part of a 4-project portfolio.

<!-- TODO: add real LinkedIn/GitHub profile links here before publishing. -->
LinkedIn · GitHub
