"""Tests for the Google Health provider (providers/google_health.py)."""

import pytest
from unittest.mock import MagicMock, patch

from tokenbridge._client import TokenBridge
from tokenbridge.providers.google_health import (
    GoogleHealth,
    _flatten,
    _summarise_sleep,
    _summarise_rr,
)


@pytest.fixture
def tb():
    return TokenBridge(
        url="https://test.supabase.co/functions/v1",
        api_key="test-key",
    )


@pytest.fixture
def gh(tb):
    return GoogleHealth(tb)


def _make_point(start_seconds: int, end_seconds: int, extra: dict = None) -> dict:
    """Build a minimal data point as the Google Health API returns it."""
    pt = {
        "startTime": {"seconds": str(start_seconds), "nanos": 0},
        "endTime":   {"seconds": str(end_seconds),   "nanos": 0},
    }
    if extra:
        pt.update(extra)
    return pt


def _mock_api(points: list, next_page: str = None):
    """Return a mock requests.Response containing the given data points."""
    mock = MagicMock()
    mock.status_code = 200
    body = {"dataPoints": points}
    if next_page:
        body["nextPageToken"] = next_page
    mock.json.return_value = body
    mock.raise_for_status = MagicMock()
    return mock


def _mock_token(tb, token: str = "tok_test"):
    mock = MagicMock()
    mock.json.return_value = {"access_token": token}
    mock.raise_for_status = MagicMock()
    return patch("tokenbridge._client.requests.post", return_value=mock)


# ── fetch ─────────────────────────────────────────────────────────────────────

def test_fetch_empty_response(gh, tb):
    with _mock_token(tb):
        with patch("tokenbridge.providers.google_health.requests.get",
                   return_value=_mock_api([])):
            result = gh.fetch_sleep("p001", "2026-05-01", "2026-05-31")
    assert result == []


def test_fetch_returns_flattened_dicts(gh, tb):
    # 2026-05-10 00:00 UTC in epoch seconds
    start = 1746835200
    end   = start + 28800  # 8 hours

    with _mock_token(tb):
        with patch("tokenbridge.providers.google_health.requests.get",
                   return_value=_mock_api([_make_point(start, end)])):
            result = gh.fetch_sleep("p001", "2026-05-01", "2026-05-31")

    assert len(result) == 1
    assert "startTime.seconds" in result[0]
    assert result[0]["startTime.seconds"] == str(start)


def test_fetch_filters_outside_window(gh, tb):
    inside  = 1746835200   # 2026-05-10
    outside = 1740787200   # 2026-03-01 — outside May window

    with _mock_token(tb):
        with patch("tokenbridge.providers.google_health.requests.get",
                   return_value=_mock_api([
                       _make_point(inside,  inside  + 3600),
                       _make_point(outside, outside + 3600),
                   ])):
            result = gh.fetch_sleep("p001", "2026-05-01", "2026-05-31")

    assert len(result) == 1
    assert result[0]["startTime.seconds"] == str(inside)


def test_fetch_paginates(gh, tb):
    start = 1746835200
    page1 = _mock_api([_make_point(start, start + 3600)], next_page="tok_page2")
    page2 = _mock_api([_make_point(start + 86400, start + 86400 + 3600)])

    with _mock_token(tb):
        with patch("tokenbridge.providers.google_health.requests.get",
                   side_effect=[page1, page2]):
            result = gh.fetch_sleep("p001", "2026-05-01", "2026-05-31")

    assert len(result) == 2


# ── summary ───────────────────────────────────────────────────────────────────

def test_summary_structure(gh, tb):
    with _mock_token(tb):
        with patch("tokenbridge.providers.google_health.requests.get",
                   return_value=_mock_api([])):
            s = gh.summary("p001", "2026-05-01", "2026-05-31")

    assert "sleep" in s
    assert "respiratory_rate" in s
    assert s["period_days"] == 31
    assert s["sleep"]["n"] == 0
    assert s["sleep"]["coverage_pct"] == 0.0


# ── _flatten ──────────────────────────────────────────────────────────────────

def test_flatten_nested_dict():
    result = _flatten({"a": {"b": 1, "c": 2}})
    assert result == {"a.b": 1, "a.c": 2}


def test_flatten_list():
    result = _flatten({"vals": [10, 20]})
    assert result == {"vals.0": 10, "vals.1": 20}


def test_flatten_scalar():
    assert _flatten("hello", prefix="key") == {"key": "hello"}


# ── _summarise helpers ────────────────────────────────────────────────────────

def test_summarise_sleep_empty():
    s = _summarise_sleep([], 30)
    assert s["n"] == 0
    assert s["coverage_pct"] == 0.0


def test_summarise_sleep_coverage():
    # Two sessions on different days
    sessions = [
        {"startTime.seconds": "1746835200"},  # 2026-05-10
        {"startTime.seconds": "1746921600"},  # 2026-05-11
    ]
    s = _summarise_sleep(sessions, 31)
    assert s["n"] == 2
    assert s["days_with_data"] == 2
    assert s["coverage_pct"] == pytest.approx(2 / 31 * 100, abs=0.1)


def test_summarise_rr_empty():
    r = _summarise_rr([], 30)
    assert r["n"] == 0


def test_summarise_rr_filters_implausible_values():
    # Value of 100 is not a plausible respiratory rate
    measurements = [{"startTime.seconds": "1746835200", "value.0.fpVal": "100"}]
    r = _summarise_rr(measurements, 30)
    assert "mean" not in r   # no valid values extracted
