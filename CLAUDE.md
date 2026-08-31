# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

TASE Spread Monitor — a single-user web app that tracks the live % spread (and current price) between pairs of Tel Aviv Stock Exchange (TASE) stocks during trading hours and sends one email alert per pair when its configurable threshold is crossed. Several pairs can be monitored at once, each shown as its own card on one page. Monitoring only — no trading/order-execution logic.

**Scope (deliberately limited):**
- Any number of concurrent monitoring sessions, each a pair of stocks picked from a curated preset list (not a live exchange-wide search)
- "Start Monitoring" (always available, not gated behind anything) sets the 0% baseline for that pair; each session is independent — starting a new one never affects any other
- One email alert per session — sent once that session's spread crosses its threshold, then no more alerts for that session until it's stopped and a new one started
- A stopped session stays visible (for review) until explicitly removed
- Single *user* (no accounts/auth) — multiple concurrent sessions is not multi-tenancy, it's one person tracking several pairs at once
- Delayed (~15 min) free data via yfinance — not real-time, not paid

Out of scope — do not add without being explicitly asked: algorithmic/automatic trading, multi-user auth, SMS/push notifications, alert re-triggering/cooldown, historical charts/backtesting, a real-time paid data feed, full ticker search across the whole exchange.

## Architecture

Backend: FastAPI (Python 3.13, `backend/`). Frontend: React + TypeScript + Vite (`frontend/`). Deployment target is a single VPS where FastAPI serves both the API (`/api/*`) and the built frontend static files from the same process (see the `StaticFiles` mount in `main.py`) — no separate frontend server in production.

Key backend modules, and why they're structured this way:
- `app/market_data/` — a `MarketDataProvider` Protocol (`base.py`) + `YFinanceProvider` (`yfinance_provider.py`). This is the *only* code that talks to yfinance. It's an abstraction specifically so a future paid/real-time provider can be swapped in without touching `poller.py`, `session.py`, or the API layer. yfinance is an unofficial Yahoo Finance scraper — treat rate limits and missing/flaky data as expected, not exceptional (see the outlier-rejection check and the retry-with-backoff in `yfinance_provider.py`). `get_price()` also normalizes agorot → ILS (Yahoo reports TASE prices in agorot, 1/100 ILS) at this single choke point, so `PriceQuote.price` is always meaningful ILS everywhere downstream.
- `app/trading_calendar/` — `tase_calendar.py` (Mon–Fri trading hours in `Asia/Jerusalem`, via `zoneinfo`) + `holidays.py` (TASE closures/shortened sessions). The holiday list is best-effort and needs a yearly refresh against TASE's official calendar — see the comment at the top of `holidays.py`.
- `app/session.py` — `SessionState` + `SessionStore`: any number of independent sessions, each identified by a `uuid4` `id`, held in-memory in a dict and persisted one row per session in SQLite (`app/db.py`, table `sessions`) so active sessions survive a backend restart. A single `asyncio.Lock` guards the whole dict (not per-session locks — contention is negligible at this app's scale); reads (`snapshot`/`list_all`) don't need the lock since they're synchronous with no `await` inside. `status` is `"active"` or `"stopped"` only — "no sessions yet" is just an empty list, not a status value.
- `app/poller.py` — a background `asyncio` task (started from `main.py`'s `lifespan`) that ticks every `POLL_INTERVAL_SECONDS`. Each tick iterates every currently-active session sequentially (not `asyncio.gather` — sequential is enough at this app's scale and keeps failure isolation trivial), skipping the whole tick if TASE is closed. One session's fetch or alert-send failure is caught per-iteration and can never affect any other session in the same tick. Sends exactly one alert email per session (retries on send failure; never marks `alerted` on a failed send).
- `app/alerts/email.py` — plain SMTP via `smtplib`, no transactional email service.
- `app/config.py` — `TICKER_PRESETS` (the selectable stock list, currently TA-125 constituents resolved to verified Yahoo Finance tickers via `backend/scripts/resolve_ta125_*.py`) and `Settings` (env-based config).

REST shape: `POST /api/sessions` (create/start, never rejects for "already active" — concurrent sessions, including duplicate ticker pairs, are allowed by design), `GET /api/sessions` (list all, active and stopped), `POST /api/sessions/{id}/stop`, `DELETE /api/sessions/{id}` (remove a *stopped* session from the list — 409 if still active).

Frontend: `App.tsx` renders `AddMonitorForm` (always available, starts a new session) plus a `MonitorCard` per session from `GET /api/sessions`, polled every ~4s (`hooks/useSessionsPolling.ts`). There is no local "is active" flag anywhere — every card is purely derived from the latest poll, so a page reload mid-multi-session-state correctly resumes every card (active and stopped) rather than resetting. That list endpoint must keep `Cache-Control: no-store` (see below). `components/StockCombobox.tsx` filters the already-fetched preset list client-side by ticker or company name — no backend search endpoint, no new dependency.

## Constraints / decisions to preserve

- Market-data access must stay behind `MarketDataProvider` — don't call yfinance directly from anywhere else. `PriceQuote.price` is always ILS — don't reintroduce raw agorot values anywhere downstream.
- Multiple concurrent sessions are supported and intentional, but this is still single-*user* — don't add per-account/multi-tenant scoping (logins, session ownership by user, etc.) without being asked.
- No database beyond the one-row-per-session SQLite `sessions` table — don't introduce Postgres/an ORM/etc. for this app's current scope.
- No authentication — don't add login/accounts.
- `GET /api/sessions` must keep its `Cache-Control: no-store` header (`session_routes.py`) — a browser-cached response silently breaks the reload-mid-session behavior described above, now for every card at once.
- `SessionStore` uses one `asyncio.Lock` for the whole session dict, not per-session locks — don't add per-session locking "for correctness"; it was a deliberate simplicity call (see `session.py`), not an oversight.
- `TICKER_PRESETS` is a plain Python list, not a database table — edit `config.py` directly, and re-run `backend/scripts/resolve_ta125_*.py` if the TA-125 composition changes rather than hand-typing tickers (the scripts cross-check the resolved company name against the query, not just "does it return a price" — see their docstrings for why that check matters).

## Running locally

Backend (from `backend/`; venv already set up at `backend/.venv`):
```
.venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8099
```

Frontend (from `frontend/`):
```
npm run dev
```
Open `http://localhost:5173` — the Vite dev server proxies `/api` to `127.0.0.1:8099` (`vite.config.ts`).

Production frontend build (served by the backend): `npm run build` → `frontend/dist/`, auto-mounted by `main.py` if present.

Frontend lint: `npm run lint` (oxlint, not eslint). Frontend typecheck: `npx tsc --noEmit`.

## Tests

```
cd backend && .venv/bin/python -m pytest
```
Single test: `.venv/bin/python -m pytest tests/test_tase_calendar.py::test_friday_shortened_hours -v`. Lint: `.venv/bin/python -m pyflakes app scripts tests`.

There's no frontend unit-test framework set up — frontend changes are verified via `tsc --noEmit` plus manual/Playwright browser-driven checks, not an automated JS test suite.

## Email configuration (no secrets here)

SMTP is configured via `backend/.env` (git-ignored — never commit it), templated in `backend/.env.example` (placeholders only, tracked in git). Required variables: `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD` (a Gmail App Password, not the account password), `ALERT_FROM_EMAIL`, `ALERT_TO_EMAIL`. Loaded via `pydantic-settings` in `config.py`, relative to the process's working directory — `.env` must sit in `backend/` since every documented command above runs from there. Manual delivery test: `.venv/bin/python -m scripts.force_alert_test` (sends one real email, bypassing the poller/threshold logic).

## Git conventions

- Only commit when explicitly asked — never commit proactively.
- Stage files by name, not `git add -A`; check `git status` before committing, especially that `backend/.env` never appears.
- Create new commits rather than amending, unless told otherwise.
- Only push when explicitly asked.

## Do not do without explicit instruction

- Don't add trading/order-execution logic — this is a monitoring-only app by design.
- Don't add multi-user auth (accounts, login, per-user session ownership) or SMS/push notifications.
- Don't switch the market-data provider or call yfinance outside `app/market_data/`.
- Don't commit, or read out loud, the contents of `backend/.env`.
- Don't introduce a database, ORM, or external stock-search API for ticker selection.
- Don't add a JS test framework or a new frontend dependency (e.g. react-select, a state-management library) without checking first — the project has deliberately stayed dependency-light.
