# Spec: Login and Logout

## Overview
This step wires up real session-based authentication for Spendly. `GET /login` and `GET /register` already render their forms and both forms already `POST` to `/login` and `/register`, but neither endpoint has a handler yet — so this step implements both POST handlers together, plus the `GET /logout` stub, as called out in CLAUDE.md's Step 3/4 territory note. After this step, a visitor can register, get signed in automatically, log in with existing credentials, and log out, with the navbar reflecting whether a session is active.

## Depends on
- Step 1 — Database setup (`database/db.py` — `users` table, `get_db()`, hashed passwords) must be complete.

## Routes
- `POST /register` — create a user, hash the password, start a session, redirect to `/` — public
- `POST /login` — verify credentials, start a session, redirect to `/` — public
- `GET /logout` — clear the session, redirect to `/login` — logged-in

`GET /login` and `GET /register` already exist and are unchanged except that a logged-in user hitting either should be redirected to `/` instead of seeing the form again.

## Database changes
No database changes. The `users` table (id, name, email, password_hash, created_at) already covers everything this step needs. `database/db.py` gains two new functions (logic only, no schema change):
- `get_user_by_email(email)` — returns a single user row or `None`
- `create_user(name, email, password_hash)` — inserts a user, returns the new user id; lets the `UNIQUE` constraint on `email` surface as `sqlite3.IntegrityError` for the route to catch

## Templates
- **Create:** none
- **Modify:**
  - `templates/login.html` — no structural change; `error` var already supported, just needs real errors passed in (e.g. "Invalid email or password")
  - `templates/register.html` — no structural change; `error` var already supported, just needs real errors passed in (e.g. "Email already registered")
  - `templates/base.html` — nav currently always shows "Sign in" / "Get started". Make it session-aware: logged-in users see a "Log out" link (`url_for('logout')`) instead; logged-out users see the current "Sign in" / "Get started" links. Do **not** add a link to `/profile` — that route is still a stub (Step 4).

## Files to change
- `app.py` — add `secret_key` config, implement `POST /register`, `POST /login`, `GET /logout`; guard `GET /login` and `GET /register` to redirect logged-in users to `/`
- `database/db.py` — add `get_user_by_email()` and `create_user()`
- `templates/base.html` — session-aware nav links

## Files to create
None.

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterised queries only
- Passwords hashed with werkzeug (`generate_password_hash` on register, `check_password_hash` on login)
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- Session only stores the user id (e.g. `session["user_id"]`) — never store the password hash in the session
- `app.secret_key` must come from `os environ.get("SECRET_KEY", ...)` with a dev-only fallback, not a bare hardcoded string used unconditionally
- Auth-related DB logic (lookups, inserts) lives in `database/db.py`, never inline in `app.py` routes
- On duplicate email during registration, catch `sqlite3.IntegrityError` and re-render `register.html` with an `error` message — don't let it 500

## Definition of done
- [ ] Registering with a new name/email/password creates a user row with a hashed password (not plaintext) and logs the user in immediately (redirected to `/`)
- [ ] Registering with an email that already exists re-renders `register.html` with an error and does not create a duplicate row
- [ ] Logging in with the seeded demo user (`demo@spendly.com` / `demo123`) succeeds and redirects to `/`
- [ ] Logging in with a wrong password or unknown email re-renders `login.html` with an error, no session is created
- [ ] Visiting `/login` or `/register` while already logged in redirects to `/` instead of showing the form
- [ ] Visiting `/logout` while logged in clears the session and redirects to `/login`
- [ ] Navbar shows "Sign in" / "Get started" when logged out, and a "Log out" link when logged in
- [ ] App starts without errors on port 5001 and all existing routes still work
