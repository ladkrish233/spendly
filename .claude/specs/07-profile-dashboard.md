# Spec: Profile Dashboard

## Overview
`/profile` currently shows only static account fields (name, email, member
since). This feature turns it into a dashboard matching the approved mockup:
an avatar/account header, three summary stat cards (total spent, transaction
count, top category), a recent-transactions table, and a by-category
breakdown with proportional bars. All numbers come from the logged-in user's
rows in the existing `expenses` table — no new user input, no new pages,
`/profile` only.

Currency is INR (₹) throughout, matching the rest of the project.

## Depends on
- Step 4 — Backend Routes for Profile Page (`.claude/specs/05-backend-routes-profile-page.md`):
  session handling and the existing `/profile` route/template this spec
  extends.
- Step 1 — Database Setup (`.claude/specs/01-database-setup.md`): the
  `expenses` table (id, user_id, amount, category, date, description,
  created_at) already exists and is seeded with demo data.

This spec does **not** depend on `.claude/specs/06-expenses-add.md` (Expenses:
Add) — that form is not yet implemented, but seeded demo expenses already
exist for the demo user, so the dashboard has real data to render today. When
`/expenses/add` ships, newly added expenses appear here automatically since
the dashboard reads directly from the `expenses` table.

## Routes
- `GET /profile` — no change to the route signature or its session-gating
  (still redirects anonymous visitors, and visitors whose session user no
  longer exists, to `/login`). The route now also fetches and passes expense
  summary data to the template.

## Database changes
No schema changes. Add these query functions to `database/db.py`:
- `get_expense_summary(user_id)` — returns a dict with:
  - `total` — `SUM(amount)` for the user (0.0 if no expenses)
  - `count` — `COUNT(*)` for the user
  - `top_category` — the category with the highest summed `amount` for the
    user (`None` if no expenses)
  - `by_category` — list of `{category, total}` dicts, one per distinct
    category the user has spent in, sorted by `total` descending
  - All aggregation done in SQL (`GROUP BY category`, `SUM`, `COUNT`) via
    parameterized queries — no averaging/summing in Python
- `get_recent_expenses(user_id, limit=5)` — the user's `limit` most recent
  expenses ordered by `date DESC, id DESC` (id as tiebreaker for same-day
  entries), parameterized `LIMIT ?`

## Templates
- **Modify:** `templates/profile.html` (still extends `base.html`):
  - **Account header** — circular avatar showing the first letter of the
    user's name (uppercased), name, email, "Member since <Month Year>"
    (reuse the existing `member_since` formatting already computed in the
    route)
  - **Stat cards row** — three cards: "Total spent" (₹, 2 decimals), 
    "Transactions" (count), "Top category" (name, or "—" if no expenses)
  - **Recent Transactions** — table with columns Date, Description, Category
    (as a small pill/badge), Amount; one row per item from
    `get_recent_expenses`; if empty, show a simple "No transactions yet" row
  - **By Category** — one row per entry in `by_category`: category name,
    a horizontal bar sized proportionally to that category's share of the
    highest category total (`width: {{ (item.total / max_total * 100) }}%`),
    and the ₹ amount; if empty, show "No expenses yet"
  - Stat cards and the two panels below (Recent Transactions, By Category)
    are laid out with CSS Grid/Flexbox, no JS — matching the "vanilla JS
    only, promote to main.js only once shared" rule (this page needs no JS)
- **No other templates change.**

## Files to change
- `app.py` — `/profile` route calls `get_expense_summary` and
  `get_recent_expenses`, passes `summary` and `recent_expenses` (plus the
  existing `user`/`member_since`) to `render_template`
- `database/db.py` — add `get_expense_summary(user_id)` and
  `get_recent_expenses(user_id, limit=5)`
- `templates/profile.html` — rebuilt per the layout above
- `static/css/profile.css` — new rules for avatar, stat cards, table, and
  category bars (all new colors/spacing via existing `--ink*`, `--paper*`,
  `--accent*`, `--border*`, `--radius-*` variables — no new hex values)

## Files to create
None.

## New dependencies
None — currency formatting done with Python's built-in `:,.2f` / Jinja
`"%.2f"|format(...)`, no new pip packages.

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterized queries only (`?` placeholders) — never f-strings in SQL
- All aggregation (SUM/COUNT/GROUP BY/ORDER BY/LIMIT) happens in SQL inside
  `database/db.py`, not by looping over rows in `app.py` or the template
- No DB logic inline in `app.py` — route only calls `db.py` functions and
  renders the template
- Currency displayed as ₹ (INR), 2 decimal places, matching
  [[project_currency]] convention — never `$`
- Use only CSS variables already defined in `static/css/style.css` — never
  hardcode new hex values in `profile.css`
- `templates/profile.html` continues to extend `base.html`
- Every internal link uses `url_for()` — never hardcode URLs
- Vanilla JS only if any interactivity is added — none is required for this
  static dashboard, so no JS should be added at all
- Do not touch `/expenses/add`, `/expenses/<id>/edit`, `/expenses/<id>/delete`,
  or the registration/login/logout routes — out of scope for this step
- Do not add pagination, filtering, sorting controls, or date-range
  selection — out of scope; this is a fixed read-only summary view

## Definition of done
- [ ] Visiting `/profile` while logged in as the seeded demo user
      (`demo@spendly.com` / `demo123`) shows the correct total spent,
      transaction count, and top category computed from the seeded data
- [ ] Recent Transactions shows the demo user's 5 most recent expenses,
      most recent first, with correct date/description/category/amount
- [ ] By Category shows one bar per distinct category the demo user has
      spent in, sorted highest-spend first, each bar's width proportional
      to its share of the top category's total
- [ ] A newly registered user with zero expenses sees "₹0.00" total,
      "0" transactions, "—" top category, and the empty states for the two
      panels — no errors, no division-by-zero on the category bar width
- [ ] All amounts render as ₹ with 2 decimal places
- [ ] `/profile` while logged out still redirects to `/login` (unchanged
      behavior)
- [ ] `pytest` passes with no regressions to existing auth/profile tests,
      plus new tests covering the summary data (populated and empty states)
