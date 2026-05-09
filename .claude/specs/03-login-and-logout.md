# Spec: Login and Logout

## Overview
This step makes the login form functional and implements the logout route. A registered user submits their email and password; the app looks up the account, verifies the hashed password, stores the user identity in the session, and redirects to the profile page. Logout clears the session and redirects to the landing page. Together these two routes complete the authentication lifecycle started in Step 02.

## Depends on
- Step 01 — Database Setup (`get_db()`, `users` table must exist)
- Step 02 — Registration (`create_user()`, password hashing pattern, session keys)

## Routes
- `GET /login` — already implemented, renders `login.html` — public
- `POST /login` — **new** — validates credentials, starts session, redirects to profile — public
- `GET /logout` — **implement stub** — clears session, redirects to landing — logged-in

## Database changes
No new tables or columns. The existing `users` table is sufficient.
A new helper function `get_user_by_email(email)` must be added to `database/db.py`.

## Templates
- **Modify:** `templates/login.html`
  - Ensure `<form>` uses `method="POST"` and `action="{{ url_for('login') }}"`
  - Ensure an `{{ error }}` block is present to display validation errors
  - Ensure email field value is re-populated on error via `{{ email or '' }}`

## Files to change
- `app.py` — add `POST` method to `/login` route; implement `/logout` route; import `check_password_hash` from `werkzeug.security`; import `get_user_by_email` from `database.db`
- `database/db.py` — add `get_user_by_email(email)` helper
- `templates/login.html` — ensure form posts correctly and shows errors

## Files to create
None.

## New dependencies
No new pip packages. `werkzeug.security.check_password_hash` is already available via the existing `werkzeug` install.

## Rules for implementation
- No SQLAlchemy or ORMs — raw `sqlite3` only
- Parameterised queries only — never f-strings in SQL
- Password verification with `werkzeug.security.check_password_hash` — never compare plaintext
- All templates extend `base.html`
- Use CSS variables — never hardcode hex values
- On successful login, store `session['user_id']` and `session['user_name']`, then redirect with `redirect(url_for('profile'))`
- On wrong email or wrong password, re-render `login.html` with `error="Invalid email or password."` — do not reveal which field is wrong (prevents user enumeration)
- On missing email or password fields, re-render `login.html` with a descriptive `error` message
- `GET /logout` must call `session.clear()` then redirect to `url_for('landing')`
- Do not protect the logout route with a login check — a logged-out user hitting `/logout` should just redirect cleanly

## Definition of done
- [ ] `POST /login` with valid credentials sets `session['user_id']` and `session['user_name']`
- [ ] Successful login redirects to `/profile`
- [ ] Submitting a non-existent email re-renders the form with `"Invalid email or password."` error
- [ ] Submitting a correct email but wrong password re-renders the form with `"Invalid email or password."` error
- [ ] Submitting with a blank email or blank password re-renders the form with an error
- [ ] Email field is re-populated after a failed login attempt
- [ ] `GET /logout` clears the session and redirects to `/`
- [ ] After logout, session no longer contains `user_id`
- [ ] `login.html` form uses `url_for('login')` — no hardcoded URLs
- [ ] App starts without errors (`python app.py`)
- [ ] All tests pass (`pytest`)
