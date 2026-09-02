# Spec: Date Filter for Profile Page

## Overview
`/profile` (built in `.claude/specs/07-profile-dashboard.md`) currently shows
stats, recent transactions, and a category breakdown computed over a user's
*entire* expense history, with no way to narrow the view to a specific time
window. This feature adds an optional date-range filter (start date, end
date) to `/profile` so a user can see their totals, top category, and
transaction list scoped to a period they choose (e.g. "this month"), while
still defaulting to all-time data when no filter is applied. It builds
directly on the existing dashboard rather than introducing a new page.

Currency remains INR (₹) throughout, matching the rest of the project.

## Depends on
- `.claude/specs/07-profile-dashboard.md` (Profile Dashboard) — this spec
  extends the existing `get_expense_summary`, `get_recent_expenses`, and
  `profile.html` layout built there. That spec explicitly listed
  date-range selection as out of scope for itself, which is why it's being
  addressed here.
- `.claude/specs/05-backend-routes-profile-page.md` — session handling and
  the `/profile` session-gating pattern this spec reuses unchanged.
- `.claude/specs/01-database-setup.md` — the existing `expenses` table
  (id, user_id, amount, category, date, description, created_at), verified
  directly in `database/db.py`. No schema changes needed.

## Routes
- `GET /profile` — no new route; existing route gains optional `start_date`
  and `end_date` query string parameters (e.g.
  `/profile?start_date=2026-08-01&end_date=2026-08-31`), both in `YYYY-MM-DD`
  format to match the `expenses.date` column. Still logged-in only, same
  redirect-to-`/login` guard as today. When both are absent, behavior is
  unchanged from spec 07 (all-time data).

## Database changes
No schema changes — the `expenses` table already exists. Modify existing
functions in `database/db.py` to accept optional filtering, keeping all
aggregation in SQL:
- `get_expense_summary(user_id, start_date=None, end_date=None)` — same
  return shape as today (`total`, `count`, `top_category`, `by_category`).
  When `start_date`/`end_date` are provided, add `AND date >= ?` / `AND date
  <= ?` to the existing parameterized `WHERE user_id = ?` clauses on both the
  totals query and the by-category query. When a bound is `None`, that
  clause is omitted entirely (not passed as `NULL`).
- `get_recent_expenses(user_id, limit=5, start_date=None, end_date=None)` —
  same behavior: append the same optional `date >= ?` / `date <= ?`
  conditions to the existing parameterized query, ordering and `LIMIT`
  unchanged.

## Templates
- **Modify:** `templates/profile.html` (still extends `base.html`):
  - Add a small filter form above the stat cards: two `<input type="date">`
    fields (`name="start_date"`, `name="end_date"`), a "Filter" submit
    button, and a "Clear" link back to plain `/profile` (only shown when a
    filter is active)
  - Form uses `method="GET" action="{{ url_for('profile') }}"` so the
    filtered view is a normal, bookmarkable/shareable URL
  - Re-populate both date inputs from the current query string
    (`value="{{ request.args.get('start_date', '') }}"`, same for
    `end_date`) so the filter persists visually after submission
  - When a filter is active, show a small text note near the stat cards
    (e.g. "Showing expenses from <start_date> to <end_date>") so it's clear
    the numbers aren't all-time
  - Stat cards, Recent Transactions, and By Category sections are unchanged
    in structure — they just render whatever `summary`/`recent_expenses`
    the route now passes in (filtered or not)
- **No other templates change.**

## Files to change
- `app.py` — `/profile` route reads `start_date`/`end_date` from
  `request.args`, passes them through to `get_expense_summary` and
  `get_recent_expenses`
- `database/db.py` — extend `get_expense_summary` and `get_recent_expenses`
  with the optional `start_date`/`end_date` parameters described above
- `templates/profile.html` — add the filter form and the active-filter note
- `static/css/profile.css` — styles for the new filter form (reuse existing
  `--ink*`/`--paper*`/`--accent*`/`--border*`/`--radius-*` variables)

## Files to create
None.

## New dependencies
No new dependencies. Date comparison is done as ISO-format (`YYYY-MM-DD`)
string comparison in SQLite, which sorts correctly lexicographically — no
`datetime` parsing needed in Python for the filter itself. The existing
`<input type="date">` browser control already constrains input format.

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterized queries only (`?` placeholders) — never f-strings in SQL
- Passwords hashed with werkzeug (unaffected by this feature; no auth code
  changes)
- Use CSS variables — never hardcode hex values in `profile.css`
- All templates extend `base.html`
- All aggregation and filtering (SUM/COUNT/GROUP BY/date comparison) happens
  in SQL inside `database/db.py`, not by looping over rows in `app.py` or
  the template
- No DB logic inline in `app.py` — route only reads query params, calls
  `db.py` functions, and renders the template
- If `start_date` is after `end_date`, treat it as an invalid range: ignore
  both filters and fall back to all-time data (fail soft, no 500 error)
- If either date param is present but fails to match `YYYY-MM-DD`, ignore
  the filter entirely and fall back to all-time data — do not raise
- Every internal link/form action uses `url_for()` — never hardcode URLs
- Vanilla JS only if any interactivity is added — none is required (plain
  GET form submission), so no JS should be added at all
- Do not touch `/expenses/add`, `/expenses/<id>/edit`,
  `/expenses/<id>/delete`, or the registration/login/logout routes — out of
  scope for this step
- Do not add pagination or sorting controls — out of scope; only the
  date-range filter is in scope

## Definition of done
- [ ] Visiting `/profile` with no query params shows all-time data,
      identical to current behavior
- [ ] Visiting `/profile?start_date=2026-09-01&end_date=2026-09-30` as the
      seeded demo user shows totals, top category, and recent transactions
      scoped to only that range
- [ ] The date inputs on the page reflect the `start_date`/`end_date` values
      currently in the URL after a filtered submission
- [ ] A "Clear" link is shown only when a filter is active, and returns to
      plain `/profile` with all-time data
- [ ] A filtered range with zero matching expenses shows ₹0.00 total, "0"
      transactions, "—" top category, and the existing empty states — no
      errors, no division-by-zero
- [ ] Submitting `start_date` after `end_date` does not error — it falls
      back to all-time data
- [ ] Submitting a malformed date value does not error — it falls back to
      all-time data
- [ ] `/profile` (filtered or not) while logged out still redirects to
      `/login`
- [ ] `pytest` passes with no regressions to existing auth/profile tests,
      plus new tests covering filtered/unfiltered/invalid-range/empty-result
      cases
