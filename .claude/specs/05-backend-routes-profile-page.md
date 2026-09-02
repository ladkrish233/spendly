# Spec: Backend Routes for Profile Page

## Overview
Spendly currently renders `login.html`, `register.html`, and a stub `/profile`
route, but none of the backend logic exists yet: `/login` and `/register` are
GET-only stubs with no form handling, `/logout` returns a placeholder string,
and `/profile` returns `"Profile page — coming in Step 4"`. This feature
implements the backend routes needed to take a visitor from registration
through to viewing their account details: session-based authentication
(register, login, logout) and a session-gated profile page that reads the
logged-in user's details from the database. This is Step 4 of the Spendly
roadmap (with its Step 3 session/auth prerequisite folded in, since profile
cannot be session-gated without it).

## Depends on
- Step 3 — Login/Logout & Session Handling (not yet implemented on `master`:
  `/login` and `/register` have no POST handlers, no `secret_key` or session
  usage is configured, and `/logout` is a plain stub). This spec implements
  Step 3 as a prerequisite alongside Step 4, since the profile route cannot
  be session-gated otherwise.

## Routes
- `GET /register` — render registration form — public
- `POST /register` — validate name/email/password, reject duplicate emails,
  hash password, create user, start session, redirect to `/profile` — public
- `GET /login` — render login form — public
- `POST /login` — verify email/password against stored hash, start session
  on success, show inline error on failure, redirect to `/profile` on
  success — public
- `GET /logout` — clear the session, redirect to `/` — logged-in
- `GET /profile` — show the logged-in user's name, email, and member-since
  date; redirect anonymous visitors (and visitors whose session user no
  longer exists in the database) to `/login` — logged-in

## Database changes
No schema changes needed — `users` table (id, name, email, password_hash,
created_at) already exists in `database/db.py`. Add these query functions to
`database/db.py`:
- `get_user_by_id(user_id)` — parameterized SELECT, used by `/profile`
- `get_user_by_email(email)` — parameterized SELECT, used by `/login` and
  duplicate-email checks in `/register`
- `create_user(name, email, password_hash)` — parameterized INSERT, used by
  `/register`

## Templates
- **Create:** `templates/profile.html` (extends `base.html`) — shows name,
  email, and formatted member-since date
- **Modify:**
  - `templates/base.html` — nav conditionally shows Profile/Sign out when
    `session.get("user_id")` is set, Sign in/Get started otherwise
  - `templates/login.html` — replace hardcoded `action="/login"` with
    `action="{{ url_for('login') }}"`; render `{{ error }}` if passed
  - `templates/register.html` — replace hardcoded form action with
    `url_for('register')`; render field errors if passed

## Files to change
- `app.py` — add `secret_key` config, POST handlers for `/register` and
  `/login`, implement `/logout` and `/profile`
- `database/db.py` — add `get_user_by_id`, `get_user_by_email`, `create_user`
- `templates/base.html` — conditional nav
- `templates/login.html` — form action + error rendering
- `templates/register.html` — form action + error rendering

## Files to create
- `templates/profile.html`
- `static/css/profile.css`

## New dependencies
No new dependencies — `werkzeug.security` (already imported in
`database/db.py`) provides `generate_password_hash` / `check_password_hash`.

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterized queries only (`?` placeholders) — never f-strings in SQL
- Passwords hashed with `werkzeug.security.generate_password_hash`, verified
  with `check_password_hash` — never store or compare plaintext
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- Every internal link uses `url_for()` — never hardcode URLs, including in
  existing `login.html` / `register.html` form `action` attributes
- Route functions do one thing: fetch data, render template, done — no DB
  logic inline in `app.py`
- Do not touch `/expenses/*` stub routes — out of scope for this step

## Definition of done
- [ ] Visiting `/register`, submitting valid name/email/password creates a
      user, logs them in, and redirects to `/profile`
- [ ] Submitting `/register` with an already-used email shows an error and
      does not create a duplicate user
- [ ] Visiting `/login` and submitting the demo user's credentials
      (`demo@spendly.com` / `demo123`) logs in and redirects to `/profile`
- [ ] Submitting `/login` with a wrong password shows an inline error and
      does not start a session
- [ ] Visiting `/profile` while logged out redirects to `/login`
- [ ] Visiting `/profile` while logged in shows the correct name, email, and
      member-since date for that user
- [ ] Visiting `/logout` clears the session and redirects to `/`; a
      subsequent visit to `/profile` redirects to `/login`
- [ ] Nav bar in `base.html` shows Sign in/Get started when logged out, and
      Profile/Sign out when logged in
- [ ] `pytest` passes with no regressions to existing landing/terms/privacy
      route behavior
