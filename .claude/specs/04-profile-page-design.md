# Spec: Profile Page Design

## Overview
The Profile page gives a logged-in user a place to view their account details (name, email, member-since date) within Spendly. It is the fourth step of the roadmap and is a read/display-focused page rather than an editing surface — it establishes the authenticated-page pattern (nav, layout, data access) that later expense-management steps (Steps 7-9) will build on.

## Depends on
**BLOCKING: Step 3 (Login and Logout) is not yet implemented.**

Current state of the codebase:
- `app.py` has no `secret_key` set, no `flask.session` usage anywhere, and no `login_required`-style decorator.
- `/login` and `/register` are GET-only routes that just render templates — there is no POST handler, no password verification, and no session creation.
- `/logout` is a plain string stub (`"Logout — coming in Step 3"`).
- There is no spec file for Step 2 (Registration) or Step 3 (Login/Logout) in `.claude/specs/`, even though route stubs for them already exist.

The Profile page cannot know *which* user to display without a session. **Do not begin implementing this spec until Step 3 (session-based login/logout) is implemented and merged.** When Step 3 lands, it should provide:
- `session["user_id"]` set on successful login, cleared on logout
- A reusable way to require login on a route (decorator or inline check) that redirects anonymous visitors to `/login`

This spec assumes that infrastructure will exist by the time Step 4 is implemented, and defines Profile's routes against it.

## Routes
- `GET /profile` — display the logged-in user's name, email, and member-since date — logged-in only (redirect to `/login` if no `session["user_id"]`)

No edit/update route is in scope for this step — profile editing is not part of Step 4.

## Database changes
No database changes. The existing `users` table (`id`, `name`, `email`, `password_hash`, `created_at`) already has every field this page displays. No new columns, tables, or constraints are needed.

`database/db.py` will need one new helper function (data access only, per CLAUDE.md — never inline SQL in routes):
- `get_user_by_id(user_id)` — `SELECT id, name, email, created_at FROM users WHERE id = ?`, returns a single row or `None`

## Templates
- **Create:** `templates/profile.html` — extends `base.html`; displays name, email, and formatted member-since date in a card, following the visual pattern of `.auth-card` / `.legal-card` (bordered card, `var(--radius-md)`, `var(--paper-card)` background)
- **Modify:** `templates/base.html` — the nav currently hardcodes "Sign in" / "Get started" links regardless of auth state. Once Step 3 provides session state, the nav must conditionally show "Profile" / "Sign out" for logged-in users and "Sign in" / "Get started" for anonymous visitors. (If Step 3's spec already covers this nav change, this spec should not duplicate it — coordinate with whatever Step 3 actually implements.)

## Files to change
- `app.py` — implement the `/profile` route (currently a string stub) to require login and render `templates/profile.html`
- `database/db.py` — add `get_user_by_id(user_id)`
- `templates/base.html` — nav conditional on login state (only if not already handled by Step 3)

## Files to create
- `templates/profile.html`
- `static/css/profile.css` — page-specific styles, if the card layout needs anything beyond what `style.css` already provides (per CLAUDE.md, prefer reusing existing classes like `.auth-card`/`.legal-card` before adding new CSS)

## New dependencies
No new dependencies.

## Rules for implementation
- No SQLAlchemy or ORMs
- Parameterised queries only
- Passwords hashed with werkzeug (n/a to this step directly, but no route in this spec should ever touch `password_hash` in a response)
- Use CSS variables — never hardcode hex values
- All templates extend `base.html`
- `/profile` must redirect anonymous visitors to `/login`, not throw an error or expose data
- Do not implement `/logout` as part of this spec — it belongs to Step 3
- Do not implement profile editing — out of scope for Step 4

## Definition of done
- [ ] Visiting `/profile` while logged out redirects to `/login`
- [ ] Visiting `/profile` while logged in (once Step 3 session handling exists) renders `templates/profile.html` with the correct name, email, and member-since date for the session's user
- [ ] `get_user_by_id()` exists in `database/db.py` and uses a parameterized query
- [ ] No route in `app.py` contains inline SQL — all queries go through `database/db.py`
- [ ] `profile.html` extends `base.html` and uses only `url_for()` for internal links
- [ ] Page renders correctly with no hardcoded hex colors (inspect CSS — only `var(--...)` used)
- [ ] `pytest` passes with no regressions
