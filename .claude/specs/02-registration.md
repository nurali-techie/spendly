# Spec: Registration

## Overview
This step makes the registration form functional. A visitor fills in their name, email, and password; the app validates the input, hashes the password, inserts a new row into `users`, starts a session, and redirects to the dashboard (or profile). This is the first point at which a real user identity is created in Spendly.

## Depends on
- Step 01 — Database Setup (`get_db()`, `init_db()`, `users` table must exist)

## Routes
- `GET /register` — already implemented, renders `register.html` — public
- `POST /register` — **new** — processes the registration form, creates user, starts session — public

## Database changes
No new tables or columns. The `users` table from Step 01 is sufficient.
A new helper function `create_user(name, email, password)` must be added to `database/db.py`.

## Templates
- **Modify:** `templates/register.html`
  - Change `action="/register"` → `action="{{ url_for('register') }}"` (fix hardcoded URL)
  - Ensure `{{ error }}` block is already present (it is — no change needed)

## Files to change
- `app.py` — add `POST` method to `/register` route; import `session` from flask; add `app.secret_key`; import `create_user` from `database.db`
- `database/db.py` — add `create_user(name, email, password)` helper
- `templates/register.html` — fix hardcoded `action` URL to use `url_for()`

## Files to create
None.

## New dependencies
No new pip packages.

## Rules for implementation
- No SQLAlchemy or ORMs — raw `sqlite3` only
- Parameterised queries only — never f-strings in SQL
- Passwords hashed with `werkzeug.security.generate_password_hash` — never store plaintext
- `app.secret_key` must be set before any `session` usage — use a hard-coded dev string for now (e.g. `"dev-secret-key"`)
- All templates extend `base.html`
- Use CSS variables — never hardcode hex values
- After successful registration, store `user_id` and `user_name` in `session` and redirect with `redirect(url_for('profile'))`
- On duplicate email (`sqlite3.IntegrityError`), re-render `register.html` with `error="An account with that email already exists."`
- On missing/short fields, re-render with a descriptive `error` message — do not `abort()`
- Password must be at least 8 characters — validate server-side before inserting
- Use `abort(405)` for any unexpected HTTP methods

## Definition of done
- [ ] `POST /register` with valid name, email, and password creates a new row in `users`
- [ ] Password is stored as a hash — never plaintext — verifiable by inspecting the DB
- [ ] Successful registration sets `session['user_id']` and `session['user_name']`
- [ ] Successful registration redirects to `/profile`
- [ ] Submitting a duplicate email re-renders the form with a visible error message
- [ ] Submitting a password shorter than 8 characters re-renders the form with an error
- [ ] Submitting with an empty name or email re-renders the form with an error
- [ ] `action` in `register.html` uses `url_for('register')`, not a hardcoded string
- [ ] App starts without errors (`python app.py`)
- [ ] All tests pass (`pytest`)
