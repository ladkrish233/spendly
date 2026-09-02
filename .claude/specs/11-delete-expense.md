# Spec: Delete Expense

## Overview
`GET /expenses/<id>/delete` is currently a stub in `app.py` that returns the
plain string `"Delete expense — coming in Step 9"`. This feature replaces it
with a real, session-gated delete action: a `POST /expenses/<id>/delete`
route removes the matching row from the `expenses` table for the logged-in
user, guarded by a JS confirmation dialog so a stray click can't silently
destroy data. This completes the basic CRUD set for expenses (add — Step 9,
edit — Step 10, delete — Step 11), giving users full control over the
expense history that drives the `/profile` dashboard.

## Depends on
- Step 10 — Edit Expense (`.claude/specs/10-edit-expense.md`, merged to
  `master`): the `get_expense_by_id(expense_id, user_id)` helper this
  feature reuses for the same ownership check, and the "Actions" column
  already added to `templates/profile.html`'s Recent Transactions table.
- Step 5 — Backend Routes for Profile Page
  (`.claude/specs/05-backend-routes-profile-page.md`): session handling
  (`session["user_id"]`), the `/login` redirect pattern.
- Step 1 — Database Setup (`.claude/specs/01-database-setup.md`): the
  `expenses` table already exists in `database/db.py`'s `init_db()`. No
  schema changes are needed for this step.

## Routes
- `POST /expenses/<int:id>/delete` — logged-in only; redirect anonymous
  visitors to `/login` (same pattern as `/profile`); look up the expense via
  the existing `get_expense_by_id(id, user_id)` helper — if it doesn't
  exist or doesn't belong to `session["user_id"]`, `abort(404)`; on success,
  delete the row via a new `delete_expense()` helper in `database/db.py`
  and redirect to `/profile`. The existing stub is `GET`-only; change it to
  `methods=["POST"]` — a destructive action must not be triggerable by a
  plain GET (accidental crawling, prefetching, or a bare link click).

## Database changes
No schema changes — the `expenses` table already exists in
`database/db.py`'s `init_db()`. Add one new query function to
`database/db.py`:
- `delete_expense(expense_id, user_id)` — parameterized
  `DELETE FROM expenses WHERE id = ? AND user_id = ?`, matching the
  ownership-scoped `WHERE` pattern already used by `update_expense`; commits

## Templates
- **Create:** none
- **Modify:** `templates/profile.html` — the Recent Transactions table's
  Actions cell (currently just the "Edit" link added in Step 10) gets a
  second, adjacent action: a small `<form method="POST"
  action="{{ url_for('delete_expense', id=expense['id']) }}">` containing a
  submit button styled as a text link (e.g. class `link-button`, a new
  minimal CSS rule in `static/css/style.css` that makes a `<button>` look
  like the existing `<a>` links — reuse `--ink`/`--accent` CSS variables,
  no hardcoded hex), with `onsubmit="return confirm('Delete this expense?')"`
  on the `<form>` so a user can't delete with a single stray click. A `POST`
  form is required here (not a GET link) because this is a destructive,
  state-changing action.

## Files to change
- `app.py` — implement `POST` for `/expenses/<int:id>/delete`, replacing
  the current `GET`-only stub; import `delete_expense` from `database.db`
- `database/db.py` — add `delete_expense(expense_id, user_id)`
- `templates/profile.html` — add the delete form/button next to the
  existing Edit link in the Actions column
- `static/css/style.css` — add a minimal `.link-button` rule so the delete
  `<button>` matches the visual style of the adjacent "Edit" `<a>` (reset
  border/background/padding/font, reuse existing `--ink`/`--accent`
  variables and hover behavior)

## Files to create
None.

## New dependencies
None — the confirmation dialog uses the browser's built-in `confirm()`,
no new JS library.

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterized queries only (`?` placeholders) — never f-strings in SQL
- All DB access goes through `database/db.py` — no inline SQL in `app.py`
- Passwords hashed with werkzeug (unaffected by this feature — codebase-
  wide rule still applies)
- `/expenses/<id>/delete` must redirect anonymous visitors to `/login`,
  exactly like `/profile`, `/expenses/add`, and `/expenses/<id>/edit`
- An expense that doesn't exist, or belongs to a different user, must
  `abort(404)` — reuse `get_expense_by_id`, never write a second, separate
  lookup query
- `delete_expense`'s `DELETE` must be scoped to both `id` and `user_id` in
  the `WHERE` clause — defense in depth alongside the route-level ownership
  check, matching the pattern already established by `update_expense`
- The delete action must be a `POST`, never a `GET` — no route decorator
  should allow `GET` to trigger a deletion
- Use CSS variables already defined in `static/css/style.css` — never
  hardcode new hex values for the `.link-button` style
- Every internal link/form action uses `url_for()` — never hardcode URLs
- No new pip packages; no new JS frameworks — `confirm()` only, inline in
  `templates/profile.html` (no dedicated confirmation page/template)
- Do not touch `/expenses/add` or `/expenses/<id>/edit` — out of scope for
  this step

## Definition of done
- [ ] Visiting `/expenses/<id>/delete` with a `GET` request no longer
      returns the old stub string and is not a valid way to delete an
      expense (route only accepts `POST`)
- [ ] Submitting the delete form while logged out redirects to `/login`
      without deleting the row
- [ ] Submitting the delete form for a non-existent expense id returns a
      404
- [ ] Submitting the delete form for an expense owned by a different user
      returns a 404 and does not delete that user's row
- [ ] Submitting the delete form for an expense you own removes that row
      from `expenses` and redirects to `/profile`
- [ ] After deletion, `/profile`'s totals, top category, and recent
      transactions no longer include the deleted expense
- [ ] `/profile`'s Recent Transactions table shows a "Delete" action next
      to "Edit" for each row, and clicking it triggers a browser
      confirmation dialog before submitting
- [ ] `pytest` passes with no regressions to existing landing/auth/profile/
      add-expense/edit-expense route behavior
