"""Overview counts per range match an independent calculation from the fixtures' expected answers."""
from collections import defaultdict
from datetime import date, timedelta

import pytest

from jobtrail.overview import range_bounds

PROCEEDING = {"Assessment", "Interview", "Offer"}
ENDED = {"Rejected", "Closed"}


def expected_counts(inbox, rng):
    today = date.today()
    start, end = range_bounds(rng, today)
    lo = start or date.min
    events = defaultdict(list)  # (company, role) -> [(status, date)]
    for h in inbox.list_headers():
        m = inbox.meta()[h.id]
        if m["kind"] == "hiring" and m["decision"] == "open":
            events[(m["company"], m["role"])].append((m["status"], h.date))
    inr = lambda d: lo <= d <= end  # noqa: E731
    return {
        "sent": sum(inr(min(d for _, d in ev)) for ev in events.values()),
        "proceeding": sum(any(s in PROCEEDING and inr(d) for s, d in ev) for ev in events.values()),
        "rejected": sum(any(s in ENDED and inr(d) for s, d in ev) for ev in events.values()),
        "active": sum(any(inr(d) for _, d in ev) for ev in events.values()),
    }


@pytest.mark.parametrize("rng", ["week", "month", "all"])
def test_counts_match_fixture_expectations(client, inbox, rng):
    client.post("/api/scan")
    got = client.get(f"/api/overview?range={rng}").json()
    assert {k: got[k] for k in ("sent", "proceeding", "rejected", "active")} == expected_counts(inbox, rng)


def test_ranges_differ_and_default_is_week(client):
    client.post("/api/scan")
    assert client.get("/api/overview").json()["range"] == "week"
    week, all_time = (client.get(f"/api/overview?range={r}").json() for r in ("week", "all"))
    assert all_time["sent"] > week["sent"]
    assert all_time["sent"] == all_time["total_all_time"]


def test_week_starts_on_monday():
    thursday = date(2026, 10, 22)
    assert range_bounds("week", thursday)[0] == thursday - timedelta(days=3)
    assert range_bounds("month", thursday)[0] == date(2026, 10, 1)


def test_empty_state(client):
    got = client.get("/api/overview?range=all").json()
    assert got["total_all_time"] == 0 and got["sent"] == 0
