# Spec: Expenses — Add

## Overview
`GET /expenses/add` is currently a stub in `app.py` that returns the plain
string `"Add expense — coming in Step 7"`. This feature replaces it with a
real, session-gated form for logging a new expense: `GET /expenses/add`
renders the form, and `POST /expenses/add` validates the input and inserts a
row into the existing `expenses` table for the logged-in user.

Spendly has no expense-listing page yet (that's a later step), so there is
nowhere natural to land the user after a successful save except the page
that already shows account-level information: `/profile`. This spec
redirects a successful `POST /expenses/add` back to `/profile`. When a future
step adds an expenses list/dashboard route, the redirect target should move
there instead — this is called out explicitly so it isn't forgotten.

This is Step 7 of the Spendly roadmap.

## Depends on
- Step 4 — Backend Routes for Profile Page (`.claude/specs/05-backend-routes-profile-page.md`),
  already implemented on this branch: session handling (`session["user_id"]`,
  `app.secret_key`), the `/login` redirect pattern used by `/profile`, and
  `get_user_by_id`. `/expenses/add` reuses this exact session-gating pattern.
- Step 1 — Database Setup (`.claude/specs/01-database-setup.md`): the
  `expenses` table (id, user_id, amount, category, date, description,
  created_at) already exists in `database/db.py`'s `init_db()` — verified by
  reading the file directly. No schema changes are needed for this step.

## Routes
- `GET /expenses/add` — logged-in only; redirect anonymous visitors to
  `/login` (same pattern as `/profile`); render the add-expense form,
  pre-selecting no category and no date
- `POST /expenses/add` — logged-in only; same redirect-to-`/login` guard as
  the GET handler; validate form input:
  - `amount` — required, must parse as a number, must be strictly greater
    than 0
  - `category` — required, non-empty after `.strip()`; must be one of the
    fixed categories already used by `seed_db()`: Food, Transport, Bills,
    Health, Entertainment, Shopping, Other
  - `date` — required, non-empty (format `YYYY-MM-DD`, consistent with the
    rest of the schema)
  - `description` — optional, may be blank
  - On validation failure: re-render `templates/expenses_add.html` with an
    `error` message and the previously-entered values so the user doesn't
    have to retype the form
  - On success: insert the expense via a new `add_expense()` helper in
    `database/db.py`, tied to `session["user_id"]`, then redirect to
    `/profile`

## Database changes
No schema changes — the `expenses` table (id, user_id, amount, category,
date, description, created_at) already exists in `database/db.py`'s
`init_db()`. Add one new query function to `database/db.py`:
- `add_expense(user_id, amount, category, date, description)` — parameterized
  `INSERT INTO expenses (user_id, amount, category, date, description) VALUES (?, ?, ?, ?, ?)`,
  matching the exact column set and order already used in `seed_db()`;
  commits and returns `cursor.lastrowid`

## Templates
- **Create:** `templates/expenses_add.html` (extends `base.html`) — a form
  page following the same structure as `login.html`/`register.html`:
  - `{% block title %}Add expense — Spendly{% endblock %}`
  - `{% block head %}` links a new `static/css/expenses.css`
  - Displays `{{ error }}` in an `.auth-error`-style banner when present
  (reuse the existing `.auth-error` class from `style.css` rather than
  inventing a new one)
  - Form fields: `amount` (`type="number"`, `step="0.01"`, `min="0.01"`),
    `category` (`<select>` populated with the fixed category list — pass the
    list from the route, don't hardcode it twice), `date` (`type="date"`),
    `description` (`<textarea>`, optional)
  - Form posts with `method="POST" action="{{ url_for('add_expense') }}"`
  - Re-populate each field's value from the previously-submitted form data
    on a validation error (e.g. `value="{{ form.amount if form else '' }}"`)
- **Modify:** `templates/base.html` — nav's logged-in branch (`{% if
  session.get('user_id') %}`) gets an added link to `/expenses/add` (e.g.
  "Add expense") alongside the existing Profile/Sign out links

## Files to change
- `app.py` — implement `GET`/`POST` for `/expenses/add`, replacing the
  current stub; import `add_expense` from `database.db`
- `database/db.py` — add `add_expense(user_id, amount, category, date, description)`
- `templates/base.html` — add "Add expense" nav link for logged-in users

## Files to create
- `templates/expenses_add.html`
- `static/css/expenses.css`

## New dependencies
None — validation uses only the standard library (e.g. `float()` in a
`try`/`except` for the amount check). No new pip packages.

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterized queries only (`?` placeholders) — never f-strings in SQL
- All DB access goes through `database/db.py` — no inline SQL in `app.py`
- `/expenses/add` (both GET and POST) must redirect anonymous visitors to
  `/login`, exactly like the existing `/profile` route
- Use CSS variables already defined in `static/css/style.css` (`--ink`,
  `--paper`, `--accent`, `--border`, `--radius-*`, etc.) — never hardcode new
  hex values in `expenses.css`
- `templates/expenses_add.html` must extend `base.html`
- Every internal link/form action uses `url_for()` — never hardcode URLs
- Category values must match the fixed list already established in
  `database/db.py`'s `seed_db()`: Food, Transport, Bills, Health,
  Entertainment, Shopping, Other — no free-text category input
- Store `amount` as a float (`REAL` column) — never insert it as a string
- Dates stored as `YYYY-MM-DD` text, consistent with the existing schema
- Do not touch `/expenses/<id>/edit` or `/expenses/<id>/delete` — out of
  scope for this step
- Do not add an expenses-listing page in this step — out of scope; the
  redirect target is `/profile` for now, called out above as a TODO for a
  future step

## Definition of done
- [ ] Visiting `/expenses/add` while logged out redirects to `/login`
- [ ] Visiting `/expenses/add` while logged in renders the add-expense form
- [ ] Submitting the form with a valid amount, category, and date creates a
      new row in `expenses` linked to the logged-in user's `id`, and
      redirects to `/profile`
- [ ] Submitting with a non-numeric or zero/negative amount re-renders the
      form with an inline error and does not insert a row
- [ ] Submitting with an empty category or a category outside the fixed
      list re-renders the form with an inline error and does not insert a
      row
- [ ] Submitting with an empty date re-renders the form with an inline error
      and does not insert a row
- [ ] Submitting with a blank description succeeds (description is optional)
- [ ] Posting to `/expenses/add` while logged out redirects to `/login`
      without inserting a row
- [ ] Nav bar shows an "Add expense" link when logged in
- [ ] `pytest` passes with no regressions to existing landing/auth/profile
      route behavior
