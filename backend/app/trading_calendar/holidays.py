"""TASE full-closure holidays and shortened-session windows.

Two different confidence levels here, deliberately kept separate:

- TASE_SHORTENED_SESSIONS_2026 dates/hours are confirmed from TASE's own
  published schedule (interim days of Passover and Sukkot).
- TASE_FULL_CLOSURE_DATES_2026 is best-effort from a third-party holiday
  aggregator (calendarlabs.com), NOT yet cross-checked against TASE's own
  official vacation-schedule PDF. A missing/wrong date here just means the
  poller may attempt (and safely fail/skip on) a closed-market tick -- not a
  safety-critical bug -- but this list MUST be verified against
  https://www.tase.co.il/en/content/knowledge_center/trading_vacation_schedule/
  before relying on it, and refreshed every year (Jewish calendar dates shift).
"""

from __future__ import annotations

from datetime import date, time

TASE_FULL_CLOSURE_DATES_2026: set[date] = {
    date(2026, 4, 1),  # Passover eve
    date(2026, 4, 2),  # Passover, 1st day
    date(2026, 4, 7),  # Passover eve (7th day)
    date(2026, 4, 8),  # Passover, last day
    date(2026, 4, 21),  # Memorial Day
    date(2026, 4, 22),  # Independence Day
    date(2026, 5, 21),  # Shavuot eve
    date(2026, 5, 22),  # Shavuot
    date(2026, 9, 11),  # Rosh Hashanah eve
    date(2026, 9, 13),  # Rosh Hashanah (2nd day)
    date(2026, 9, 20),  # Yom Kippur eve
    date(2026, 9, 21),  # Yom Kippur
    date(2026, 9, 25),  # Sukkot eve
    date(2026, 9, 26),  # Sukkot, 1st day
    date(2026, 10, 2),  # Shmini Atzeret / Simchat Torah
}

# Confirmed via TASE's official schedule: interim (chol hamoed) days of
# Passover and Sukkot run a shortened session.
TASE_SHORTENED_SESSIONS_2026: dict[date, tuple[time, time]] = {
    date(2026, 4, 3): (time(9, 59), time(13, 34)),
    date(2026, 4, 5): (time(9, 59), time(13, 34)),
    date(2026, 4, 6): (time(9, 59), time(13, 34)),
    date(2026, 9, 27): (time(9, 59), time(13, 34)),
    date(2026, 9, 28): (time(9, 59), time(13, 34)),
    date(2026, 9, 29): (time(9, 59), time(13, 34)),
    date(2026, 9, 30): (time(9, 59), time(13, 34)),
    date(2026, 10, 1): (time(9, 59), time(13, 34)),
}
