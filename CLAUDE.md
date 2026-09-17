# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

TASE Spread Monitor — a single-user web app with two independent monitoring features for Tel Aviv Stock Exchange (TASE) stocks: **pair-spread monitoring** (live % spread and price between two stocks, alert once a configurable threshold is crossed) and **moving-average watches** (per-stock golden/death cross on two SMAs, checked once daily, re-alerting on every new crossover). Both features show as cards on one page. Monitoring only — no trading/order-execution logic.

**Pair-spread scope (deliberately limited):**
- Any number of concurrent monitoring sessions, each a pair of stocks picked from a curated preset list (not a live exchange-wide search)
- "Start Monitoring" (always available, not gated behind anything) sets the 0% baseline for that pair; each session is independent — starting a new one never affects any other
- One email alert per session — sent once that session's spread crosses its threshold, then no more alerts for that session until it's stopped and a new one started
- A stopped session stays visible (for review) until explicitly removed
- Delayed (~15 min) free data via yfinance — not real-time, not paid

**Moving-average watch scope:**
- One stock per watch (not a pair), a short-period and long-period SMA (both user-configurable, default 5/13)
- Checked once per trading day, a configurable delay after TASE close (`ma_check_delay_minutes`) — not continuously, unlike pair-spread sessions
- Re-alerts on every new golden/death crossover (the opposite of pair-spread's one-shot-then-silent behavior — a deliberate difference between the two features, not an inconsistency)
- Fully isolated from pair-spread: own table (`ma_watches`), own store, own poller, own API namespace (`/api/ma-watches`) — see Architecture below

Single *user* throughout (no accounts/auth) — multiple concurrent sessions/watches is not multi-tenancy, it's one person tracking several things at once.

Out of scope — do not add without being explicitly asked: algorithmic/automatic trading, multi-user auth, SMS/push notifications, backtesting UI, a real-time paid data feed, full ticker search across the whole exchange, additional technical indicators beyond moving averages (RSI/MACD/Bollinger etc.). (Historical price charting *is* built — see the MA watch chart below — this line means don't go beyond what's already there without being asked.)

## Architecture

Backend: FastAPI (Python 3.13, `backend/`). Frontend: React + TypeScript + Vite (`frontend/`). Deployment target is a single VPS where FastAPI serves both the API (`/api/*`) and the built frontend static files from the same process (see the `StaticFiles` mount in `main.py`) — no separate frontend server in production.

Key backend modules, and why they're structured this way:
- `app/market_data/` — a `MarketDataProvider` Protocol (`base.py`) + `YFinanceProvider` (`yfinance_provider.py`). This is the *only* code that talks to yfinance. It's an abstraction specifically so a future paid/real-time provider can be swapped in without touching `poller.py`, `session.py`, or the API layer. yfinance is an unofficial Yahoo Finance scraper — treat rate limits and missing/flaky data as expected, not exceptional (see the outlier-rejection check and the retry-with-backoff in `yfinance_provider.py`). `get_price()` also normalizes agorot → ILS (Yahoo reports TASE prices in agorot, 1/100 ILS) at this single choke point, so `PriceQuote.price` is always meaningful ILS everywhere downstream.
- `app/trading_calendar/` — `tase_calendar.py` (Mon–Fri trading hours in `Asia/Jerusalem`, via `zoneinfo`) + `holidays.py` (TASE closures/shortened sessions). The holiday list is best-effort and needs a yearly refresh against TASE's official calendar — see the comment at the top of `holidays.py`.
- `app/session.py` — `SessionState` + `SessionStore`: any number of independent sessions, each identified by a `uuid4` `id`, held in-memory in a dict and persisted one row per session in SQLite (`app/db.py`, table `sessions`) so active sessions survive a backend restart. A single `asyncio.Lock` guards the whole dict (not per-session locks — contention is negligible at this app's scale); reads (`snapshot`/`list_all`) don't need the lock since they're synchronous with no `await` inside. `status` is `"active"` or `"stopped"` only — "no sessions yet" is just an empty list, not a status value.
- `app/poller.py` — a background `asyncio` task (started from `main.py`'s `lifespan`) that ticks every `POLL_INTERVAL_SECONDS`. Each tick iterates every currently-active session sequentially (not `asyncio.gather` — sequential is enough at this app's scale and keeps failure isolation trivial), skipping the whole tick if TASE is closed. One session's fetch or alert-send failure is caught per-iteration and can never affect any other session in the same tick. Sends exactly one alert email per session (retries on send failure; never marks `alerted` on a failed send).
- `app/alerts/email.py` — plain SMTP via `smtplib`, no transactional email service. Pair-spread-specific (takes a `SessionState`); the MA watch feature has its own separate sender, see below.
- `app/config.py` — `TICKER_PRESETS` (the selectable stock list, currently TA-125 constituents resolved to verified Yahoo Finance tickers via `backend/scripts/resolve_ta125_*.py`) and `Settings` (env-based config).

REST shape: `POST /api/sessions` (create/start, never rejects for "already active" — concurrent sessions, including duplicate ticker pairs, are allowed by design), `GET /api/sessions` (list all, active and stopped), `POST /api/sessions/{id}/stop`, `DELETE /api/sessions/{id}` (remove a *stopped* session from the list — 409 if still active).

Frontend: `App.tsx` renders `AddMonitorForm` (always available, starts a new session) plus a `MonitorCard` per session from `GET /api/sessions`, polled every ~4s (`hooks/useSessionsPolling.ts`). There is no local "is active" flag anywhere — every card is purely derived from the latest poll, so a page reload mid-multi-session-state correctly resumes every card (active and stopped) rather than resetting. That list endpoint must keep `Cache-Control: no-store` (see below). `components/StockCombobox.tsx` filters the already-fetched preset list client-side by ticker or company name — no backend search endpoint, no new dependency.

### Moving-average watch feature (`app/ma/`)

Deliberately isolated from the pair-spread feature above — own table, own store, own poller, own routes, own frontend section — so it can evolve without risk to pair-spread code. The only things it shares are read-only infrastructure: `MarketDataProvider` (extended, see below), `db.py`'s connection helper, `deps.py`'s singleton pattern, and CSS classes reused as-is by the frontend cards.

- `app/market_data/base.py` / `yfinance_provider.py` — `MarketDataProvider` gained `get_history(ticker, num_periods) -> list[PriceQuote]` (oldest-first daily closes, already ILS-converted, raises `MarketDataUnavailable` if fewer than `num_periods` rows come back). Fetches via `yf.Ticker(ticker).history(start=, end=, interval="1d", auto_adjust=True)` — explicit dates, not `period="Nd"` strings (undocumented for arbitrary day counts) — with a `num_periods * 2.0 + 30` calendar-day buffer to absorb weekends/holidays. **That ratio is empirically measured, not theoretical**: real TASE data on Yahoo runs from a ~1.6 calendar:trading-day ratio at a 1-year window up to ~1.83 at 15+ years (worse than a naive weekends-only estimate, and it doesn't level off at the smaller windows this was first tuned for) — the original `1.6 + 20` constants under-requested calendar days once the chart feature (below) started asking for multi-year windows, causing spurious `MarketDataUnavailable` errors on requests that should have succeeded. Fixing the ratio was judged a legitimate bug fix, not a weakening of the strict row-count guard itself (which stays exactly as strict — this only affects how many calendar days get requested *before* that check runs). Has its own retry loop (`_fetch_history_with_retry`), deliberately not sharing `get_price()`'s `_fetch_price_with_retry` (that one's pinned by existing tests). Does **not** feed into `_check_outlier`/`_last_good_price` — those stay scoped to live-tick jump detection only.
- `app/ma/state.py` — `MAWatchState` + `MAWatchStore`, same concurrency model as `SessionStore` (one `asyncio.Lock`, dict-backed, SQLite table `ma_watches`), but with two **separate** update methods — `apply_check_result` (success, always advances `last_checked_date`) and `apply_check_error` (failure/deferral, never advances it) — instead of one method with an optional error param, so a failed check structurally cannot look like a successful one.
- `app/ma/poller.py` — a second, independent background task (`ma_poller_loop`, own `ma_poll_interval_seconds` setting, default 15 min) — NOT the same loop as pair-spread's `poller.py`. Each tick: is today a trading day and are we past close + `ma_check_delay_minutes`? If not, no-op. Otherwise, for each active watch not yet checked today, fetch `long_period` closes, and **verify the latest close is actually dated today** (TASE-local) before trusting it — Yahoo's EOD bar isn't always published the instant the market closes, and silently classifying against a stale (yesterday's) close would be a real, silent correctness bug. If stale, defer via `apply_check_error` (retried later the same day); if fresh, classify golden/death, compare against `last_cross_direction`, and alert only on a real change (first-ever check just establishes a baseline, never alerts).
- `app/ma/email.py` — separate `send_ma_alert_email`, not a shared helper with `alerts/email.py`.
- `app/ma/routes.py` — `POST /api/ma-watches`, `GET /api/ma-watches` (`Cache-Control: no-store`, same reason as `/api/sessions`), `POST /api/ma-watches/{id}/stop`, `DELETE /api/ma-watches/{id}`. Unlike pair-spread's `POST /api/sessions`, watch creation does **not** synchronously fetch/classify — it just persists with `last_checked_date=None`; the poller's existing first-check logic handles baselining whenever its next eligible pass occurs.

Frontend: `AddMAWatchForm.tsx` (reuses `StockCombobox` for the single-ticker picker) + `MAWatchCard.tsx` + `hooks/useMAWatchesPolling.ts`, rendered as a second section in `App.tsx` below the pair-spread cards, same "purely derived from the latest poll" pattern.

#### Historical price + moving-average chart

`GET /api/ma-watches/chart?ticker=&short_period=&long_period=&range=` (in `app/ma/routes.py`) is **stateless** — not tied to a watch id — so it serves both an in-progress `AddMAWatchForm` preview (before a watch is even created) and a persisted `MAWatchCard`'s view identically. `app/ma/chart.py` holds the pure logic: a range→trading-days table (`1W=5 … 5Y=1260`), `trailing_sma()` (a full rolling-array SMA, deliberately separate from `poller.py`'s single-scalar `mean()` — never shared, never imported by each other), and `build_chart_points()`. The over-fetch-then-slice strategy: request `range_days + max(short_period, long_period)` periods via the existing `get_history()`, compute rolling SMAs over the *whole* fetched series, then slice to just the last `range_days` points — so every displayed point has full SMA lookback, not just the ones after enough history accumulates within the visible window. `get_history()`'s strict shortfall guard is preserved; a real shortfall (e.g. 5Y + a large long_period exceeding a thinly-listed ticker's available history) surfaces as a clean `422`, not a silently-shrunk range or a retry loop.

Frontend: `MAChart.tsx` (data/state — owns the range selection, debounces period-input changes, fetches via an `AbortController`-guarded effect) + `ChartRangeSelector.tsx` (the 6 preset buttons) + `MAChartSvg.tsx` (pure hand-rolled inline SVG — no charting library, matching the dependency-light convention below). Colors validated via the dataviz skill's `validate_palette.js` (all-pairs safe: price blue `#2a78d6`, short SMA orange `#eb6834`, long SMA aqua `#1baf7a`); aqua is under 3:1 contrast on the light surface so it's used for the line/swatch only, never as text color. **Critical wiring detail**: `MAChart` must be driven by primitive `ticker`/`shortPeriod`/`longPeriod` props, never a whole `watch` object — `useMAWatchesPolling` returns a fresh object reference every ~4s poll tick even when nothing changed, so keying the fetch effect off the object would refetch forever. Both `AddMAWatchForm.tsx` and `MAWatchCard.tsx` pass the three primitives explicitly for this reason.

## Constraints / decisions to preserve

- Market-data access must stay behind `MarketDataProvider` — don't call yfinance directly from anywhere else. `PriceQuote.price` is always ILS — don't reintroduce raw agorot values anywhere downstream.
- Multiple concurrent sessions are supported and intentional, but this is still single-*user* — don't add per-account/multi-tenant scoping (logins, session ownership by user, etc.) without being asked.
- No database beyond the plain SQLite tables already in `db.py` (`sessions`, `ma_watches`) — don't introduce Postgres/an ORM/etc. for this app's current scope.
- No authentication — don't add login/accounts.
- `GET /api/sessions` must keep its `Cache-Control: no-store` header (`session_routes.py`) — a browser-cached response silently breaks the reload-mid-session behavior described above, now for every card at once.
- `SessionStore` uses one `asyncio.Lock` for the whole session dict, not per-session locks — don't add per-session locking "for correctness"; it was a deliberate simplicity call (see `session.py`), not an oversight.
- `TICKER_PRESETS` is a plain Python list, not a database table — edit `config.py` directly, and re-run `backend/scripts/resolve_ta125_*.py` if the TA-125 composition changes rather than hand-typing tickers (the scripts cross-check the resolved company name against the query, not just "does it return a price" — see their docstrings for why that check matters).
- The MA watch feature must stay isolated from pair-spread — don't merge `ma_watches` into the `sessions` table, don't have `app/ma/poller.py` share a loop with `app/poller.py`, don't reuse `alerts/email.py`'s `send_alert_email` for MA alerts. A few duplicated lines (retry loops, SMTP boilerplate) is the accepted cost of that isolation, not something to "clean up" later.
- `app/ma/poller.py` must verify a fetched close is actually dated "today" (TASE-local) before trusting it, and never advance `last_checked_date` on a failed or deferred check — this is the guard against Yahoo's EOD-bar publish lag silently causing a wrong-day classification. Don't remove or weaken this check.
- MA watch creation (`POST /api/ma-watches`) must stay asynchronous — no synchronous price/history fetch at creation time, unlike pair-spread sessions. Let the daily poller's existing first-check logic establish the baseline.
- The chart endpoint (`GET /api/ma-watches/chart`) stays stateless (ticker/periods as query params, not a watch id) — don't make it require an existing watch; the `AddMAWatchForm` preview depends on it working before a watch exists.
- Don't lower `yfinance_provider.py`'s `CALENDAR_DAYS_PER_TRADING_DAY`/`HOLIDAY_PAD_DAYS` back toward the original `1.6`/`20` — those were empirically wrong for multi-year windows (see Architecture above); if you need to retune them, re-measure against real data first, the same way this fix was derived.
- No new frontend charting dependency for `MAChartSvg.tsx` — it's deliberately hand-rolled SVG, matching the dependency-light rule below.

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
