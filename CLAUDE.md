# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Spendly is a personal finance / expense-tracking web application built with Flask (Python backend) and plain HTML/CSS/JS (frontend). It is structured as a step-by-step learning project: the frontend and route scaffolding are largely in place, and students progressively implement the backend.

## Development Commands

```bash
# Activate the virtual environment
source venv/bin/activate

# Run the development server (port 5001, debug mode)
python app.py

# Run all tests
pytest

# Run a single test file
pytest tests/test_auth.py

# Run a single test function
pytest tests/test_auth.py::test_login_success
```

Dependencies are managed via `requirements.txt` (Flask 3.1.3, Werkzeug 3.1.6, pytest 8.3.5, pytest-flask 1.3.0). There is no build step — this is a pure Python/Jinja2 app.

## Architecture

```
app.py               Flask app and all route definitions
database/
  db.py              SQLite helpers: get_db(), init_db(), seed_db()
templates/           Jinja2 templates
  base.html          Global layout (navbar, footer, font/CSS/JS links)
  landing.html       Marketing / home page
  login.html         Login form
  register.html      Registration form
  terms.html         Terms & Conditions
  privacy.html       Privacy Policy
static/
  css/style.css      Single stylesheet with CSS custom-property design system
  js/main.js         Vanilla JS (currently minimal)
```

**Database:** SQLite, file named `expense_tracker.db` (git-ignored). All DB access goes through `database/db.py`. `get_db()` must return a connection with `row_factory = sqlite3.Row` and `PRAGMA foreign_keys = ON`. Tables to create: Users, Expenses, Categories, Budgets.

**Routing convention:** All routes live in `app.py`. Placeholder routes return plain strings with a step label (e.g., `"Logout — coming in Step 3"`); these are replaced as each feature is built.

**Templates:** Every page extends `base.html` using `{% extends "base.html" %}` and overrides `{% block content %}`. The base template wires in Google Fonts (DM Serif Display + DM Sans), `style.css`, and `main.js`.

**Styling:** `style.css` uses CSS custom properties defined on `:root` — ink/paper/accent/secondary-accent/danger colour tokens, consistent spacing and typography variables. Avoid inline styles; extend the existing variable system.

## Implementation Steps (for context)

The project is built incrementally:
- **Step 1** – Implement `database/db.py` (`get_db`, `init_db`, `seed_db`)
- **Step 2** – Register + Login (POST handlers, password hashing, sessions)
- **Step 3** – Logout (`/logout`)
- **Step 4** – Profile page (`/profile`)
- **Steps 7–9** – Expense CRUD (`/expenses/add`, `/expenses/<id>/edit`, `/expenses/<id>/delete`)
