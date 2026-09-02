# Spec: Edit Expense

## Overview
`GET /expenses/<id>/edit` is currently a stub in `app.py` that returns the
plain string `"Edit expense — coming in Step 8"`. This feature replaces it
with a real, session-gated form for editing an existing expense: `GET
/expenses/<id>/edit` renders the form pre-filled with the expense's current
values, and `POST /expenses/<id>/edit` validates the input and updates the
matching row in the `expenses` table. This reuses the add-expense form
layout and validation rules, giving users a way to correct mistakes in
previously logged expenses rather than only being able to add new ones.

## Depends on
- Step 9 — Add Expense (`.claude/specs/09-add-expense.md`): the
  `expenses_add.html` form structure, `expenses.css` styling, and the
  amount/category/date validation rules this feature reuses for editing.
- Step 5 — Backend Routes for Profile Page
  (`.claude/specs/05-backend-routes-profile-page.md`): session handling
  (`session["user_id"]`), the `/login` redirect pattern, and
  `get_user_by_id`. `/expenses/<id>/edit` reuses this exact session-gating
  pattern.
- Step 1 — Database Setup (`.claude/specs/01-database-setup.md`): the
  `expenses` table (id, user_id, amount, category, date, description,
  created_at) already exists in `database/db.py`'s `init_db()` — verified by
  reading the file directly. No schema changes are needed for this step.

## Routes
- `GET /expenses/<int:id>/edit` — logged-in only; redirect anonymous
  visitors to `/login` (same pattern as `/profile`); look up the expense by
  `id` via a new `get_expense_by_id()` helper — if it doesn't exist or
  doesn't belong to `session["user_id"]`, `abort(404)`; render the edit form
  pre-filled with the expense's current `amount`, `category`, `date`, and
  `description`
- `POST /expenses/<int:id>/edit` — logged-in only; same redirect-to-`/login`
  guard and same ownership check (`abort(404)` if the expense doesn't exist
  or belongs to another user) as the GET handler; validate form input using
  the same rules as `/expenses/add`:
  - `amount` — required, must parse as a number, must be strictly greater
    than 0
  - `category` — required, non-empty after `.strip()`; must be one of the
    fixed categories already used by `seed_db()`: Food, Transport, Bills,
    Health, Entertainment, Shopping, Other
  - `date` — required, non-empty, format `YYYY-MM-DD`
  - `description` — optional, may be blank
  - On validation failure: re-render `templates/expenses_edit.html` with an
    `error` message and the previously-entered values (not the stale DB
    values) so the user doesn't lose their edits
  - On success: update the row via a new `update_expense()` helper in
    `database/db.py`, scoped to both `id` and `user_id`, then redirect to
    `/profile`

## Database changes
No schema changes — the `expenses` table already exists in
`database/db.py`'s `init_db()`. Add two new query functions to
`database/db.py`:
- `get_expense_by_id(expense_id, user_id)` — parameterized
  `SELECT * FROM expenses WHERE id = ? AND user_id = ?`; returns `None` if
  no match (used for the ownership check in both the GET and POST handlers)
- `update_expense(expense_id, user_id, amount, category, date, description)`
  — parameterized
  `UPDATE expenses SET amount = ?, category = ?, date = ?, description = ? WHERE id = ? AND user_id = ?`;
  commits; the `user_id` clause is a defense-in-depth guard alongside the
  route-level ownership check

## Templates
- **Create:** `templates/expenses_edit.html` (extends `base.html`) — same
  structure as `expenses_add.html`:
  - `{% block title %}Edit expense — Spendly{% endblock %}`
  - `{% block head %}` links the existing `static/css/expenses.css` (no new
    stylesheet needed)
  - Displays `{{ error }}` in an `.auth-error` banner when present
  - Same fields as `expenses_add.html`: `amount`, `category` (`<select>`
    populated from the passed-in category list), `date`, `description`
  - Form posts with `method="POST" action="{{ url_for('edit_expense', id=expense['id']) }}"`
  - Field values default to `form.<field> if form else expense['<field>']`
    so a validation error re-shows the user's last input, and a fresh GET
    shows the expense's current stored values
  - Submit button reads "Save changes" (distinct from add-expense's "Add
    expense")
- **Modify:** `templates/profile.html` — the Recent Transactions table gets
  an added "Actions" column (`<th>Actions</th>` / a trailing `<td>`) with an
  edit link per row: `<a href="{{ url_for('edit_expense', id=expense['id']) }}">Edit</a>`

## Files to change
- `app.py` — implement `GET`/`POST` for `/expenses/<int:id>/edit`,
  replacing the current stub; import `get_expense_by_id` and
  `update_expense` from `database.db`; import `abort` from `flask`
- `database/db.py` — add `get_expense_by_id(expense_id, user_id)` and
  `update_expense(expense_id, user_id, amount, category, date, description)`
- `templates/profile.html` — add an Actions column with an Edit link to the
  Recent Transactions table

## Files to create
- `templates/expenses_edit.html`

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterized queries only (`?` placeholders) — never f-strings in SQL
- All DB access goes through `database/db.py` — no inline SQL in `app.py`
- Passwords hashed with werkzeug (unaffected by this feature — no password
  handling here, but the codebase-wide rule still applies)
- `/expenses/<id>/edit` (both GET and POST) must redirect anonymous
  visitors to `/login`, exactly like `/profile` and `/expenses/add`
- An expense that doesn't exist, or belongs to a different user, must
  `abort(404)` — never leak or allow editing another user's data
- Use CSS variables already defined in `static/css/style.css` — never
  hardcode new hex values; reuse `static/css/expenses.css` as-is
- `templates/expenses_edit.html` must extend `base.html`
- Every internal link/form action uses `url_for()` — never hardcode URLs
- Category values must match the fixed list already established in
  `database/db.py`'s `seed_db()` — no free-text category input
- Store `amount` as a float (`REAL` column) — never insert it as a string
- Dates stored as `YYYY-MM-DD` text, consistent with the existing schema
- Do not touch `/expenses/<id>/delete` — out of scope for this step
- Do not add bulk-edit or an expenses-listing page in this step — out of
  scope

## Definition of done
- [ ] Visiting `/expenses/<id>/edit` while logged out redirects to `/login`
- [ ] Visiting `/expenses/<id>/edit` for an expense you own, while logged
      in, renders the edit form pre-filled with that expense's current
      amount, category, date, and description
- [ ] Visiting `/expenses/<id>/edit` for a non-existent expense id returns
      a 404
- [ ] Visiting `/expenses/<id>/edit` for an expense owned by a different
      user returns a 404 (not the expense's data)
- [ ] Submitting the form with a valid amount, category, and date updates
      the existing row in `expenses` (no new row is inserted) and redirects
      to `/profile`
- [ ] The updated expense is reflected in `/profile`'s totals, top
      category, and recent transactions immediately after redirect
- [ ] Submitting with a non-numeric or zero/negative amount re-renders the
      form with an inline error and does not modify the row
- [ ] Submitting with an empty category or a category outside the fixed
      list re-renders the form with an inline error and does not modify the
      row
- [ ] Submitting with an empty date re-renders the form with an inline
      error and does not modify the row
- [ ] Submitting with a blank description succeeds (description is
      optional)
- [ ] Posting to `/expenses/<id>/edit` while logged out redirects to
      `/login` without modifying the row
- [ ] `/profile`'s Recent Transactions table shows an "Edit" link per row
      that navigates to the correct `/expenses/<id>/edit` URL
- [ ] `pytest` passes with no regressions to existing landing/auth/profile/
      add-expense route behavior
