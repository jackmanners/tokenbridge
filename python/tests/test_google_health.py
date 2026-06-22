"""Tests for the Google Health provider (providers/google_health.py)."""

import pytest
from unittest.mock import MagicMock, patch

from tokenbridge._client import TokenBridge
from tokenbridge.providers.google_health import GoogleHealth, _flatten, _validate_dates


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
    pt = {
        "startTime": {"seconds": str(start_seconds), "nanos": 0},
        "endTime":   {"seconds": str(end_seconds),   "nanos": 0},
    }
    if extra:
        pt.update(extra)
    return pt


def _mock_api(points: list, next_page: str = None):
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
    mock.status_code = 200
    mock.json.return_value = {"access_token": token}
    mock.raise_for_status = MagicMock()
    return patch("tokenbridge._client.requests.post", return_value=mock)


# ── Date validation ───────────────────────────────────────────────────────────

def test_validate_dates_valid():
    _validate_dates("2026-05-01", "2026-05-31")  # should not raise


def test_validate_dates_bad_format():
    with pytest.raises(ValueError, match="YYYY-MM-DD"):
        _validate_dates("01-05-2026", "2026-05-31")


def test_validate_dates_end_before_start():
    with pytest.raises(ValueError, match="start_date"):
        _validate_dates("2026-06-01", "2026-05-01")


def test_validate_dates_same_day_ok():
    _validate_dates("2026-05-01", "2026-05-01")  # same day is allowed


# ── fetch ─────────────────────────────────────────────────────────────────────

def test_fetch_empty_response(gh, tb):
    with _mock_token(tb):
        with patch("tokenbridge.providers.google_health.requests.get",
                   return_value=_mock_api([])):
            result = gh.fetch("p001", "sleep", "2026-05-01", "2026-05-31")
    assert result == []


def test_fetch_returns_flattened_dicts(gh, tb):
    start = 1746835200  # 2026-05-10 UTC
    end   = start + 28800

    with _mock_token(tb):
        with patch("tokenbridge.providers.google_health.requests.get",
                   return_value=_mock_api([_make_point(start, end)])):
            result = gh.fetch("p001", "sleep", "2026-05-01", "2026-05-31")

    assert len(result) == 1
    assert "startTime.seconds" in result[0]
    assert result[0]["startTime.seconds"] == str(start)


def test_fetch_paginates(gh, tb):
    start = 1746835200
    page1 = _mock_api([_make_point(start, start + 3600)], next_page="tok_page2")
    page2 = _mock_api([_make_point(start + 86400, start + 86400 + 3600)])

    with _mock_token(tb):
        with patch("tokenbridge.providers.google_health.requests.get",
                   side_effect=[page1, page2]):
            result = gh.fetch("p001", "sleep", "2026-05-01", "2026-05-31")

    assert len(result) == 2


def test_fetch_reuses_provided_token(gh):
    """Passing a token skips the TokenBridge round-trip."""
    with patch("tokenbridge.providers.google_health.requests.get",
               return_value=_mock_api([])) as mock_get:
        gh.fetch("p001", "sleep", "2026-05-01", "2026-05-31", token="pre_fetched")
    mock_get.assert_called_once()


def test_fetch_invalid_date_raises(gh):
    with pytest.raises(ValueError):
        gh.fetch("p001", "sleep", "not-a-date", "2026-05-31", token="tok")


# ── data_completeness ─────────────────────────────────────────────────────────

def test_data_completeness_default_types(gh, tb):
    """Default data_types = sleep / steps / heart-rate-variability."""
    with _mock_token(tb):
        with patch("tokenbridge.providers.google_health.requests.get",
                   return_value=_mock_api([])):
            rows = gh.data_completeness(["p001"], "2026-05-01", "2026-05-31")

    types = {r["data_type"] for r in rows}
    assert "sleep" in types
    assert "steps" in types
    assert "heart-rate-variability" in types


def test_data_completeness_custom_types(gh, tb):
    with _mock_token(tb):
        with patch("tokenbridge.providers.google_health.requests.get",
                   return_value=_mock_api([])):
            rows = gh.data_completeness(
                ["p001", "p002"], "2026-05-01", "2026-05-31",
                data_types=["sleep", "steps"],
            )

    assert len(rows) == 4  # 2 users × 2 types
    assert all(r["data_type"] in ("sleep", "steps") for r in rows)


# ── _flatten ──────────────────────────────────────────────────────────────────

def test_flatten_nested_dict():
    result = _flatten({"a": {"b": 1, "c": 2}})
    assert result == {"a.b": 1, "a.c": 2}


def test_flatten_list():
    result = _flatten({"vals": [10, 20]})
    assert result == {"vals.0": 10, "vals.1": 20}


def test_flatten_scalar():
    assert _flatten("hello", prefix="key") == {"key": "hello"}
