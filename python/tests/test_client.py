"""Tests for TokenBridge platform client (_client.py)."""

import pytest
from unittest.mock import MagicMock, patch

from tokenbridge._client import TokenBridge


@pytest.fixture
def tb():
    return TokenBridge(
        url="https://test.supabase.co/functions/v1",
        api_key="test-key",
    )


def _mock_token_resp(extra: dict = None):
    data = {
        "access_token": "tok_abc123",
        "expires_at":   "2026-06-19T00:00:00Z",
        "refreshed":    False,
        "scopes":       ["https://www.googleapis.com/auth/googlehealth.sleep.readonly"],
    }
    if extra:
        data.update(extra)
    mock = MagicMock()
    mock.json.return_value = data
    mock.raise_for_status = MagicMock()
    return mock


# ── Construction ──────────────────────────────────────────────────────────────

def test_raises_without_url():
    with pytest.raises(RuntimeError, match="TOKENBRIDGE_URL"):
        TokenBridge(url="", api_key="key")


def test_raises_without_api_key():
    with pytest.raises(RuntimeError, match="TOKENBRIDGE_API_KEY"):
        TokenBridge(url="https://example.com", api_key="")


# ── Auth URLs ─────────────────────────────────────────────────────────────────

def test_auth_url_contains_user_id(tb):
    url = tb.auth_url("p001")
    assert "user_id=p001" in url
    assert "provider=google-health" in url
    assert "auth-start" in url


def test_auth_url_custom_provider(tb):
    url = tb.auth_url("p001", provider="withings")
    assert "provider=withings" in url


def test_auth_urls_returns_dict(tb):
    urls = tb.auth_urls(["p001", "p002", "p003"])
    assert set(urls.keys()) == {"p001", "p002", "p003"}
    assert "p002" in urls["p002"]


def test_auth_urls_empty_list(tb):
    assert tb.auth_urls([]) == {}


# ── Token retrieval ───────────────────────────────────────────────────────────

def test_get_token_success(tb):
    with patch("tokenbridge._client.requests.post", return_value=_mock_token_resp()):
        token = tb.get_token("p001")
    assert token == "tok_abc123"


def test_get_token_missing_raises(tb):
    mock = MagicMock()
    mock.json.return_value = {"error": "user not found"}
    mock.text = '{"error": "user not found"}'
    mock.raise_for_status = MagicMock()

    with patch("tokenbridge._client.requests.post", return_value=mock):
        with pytest.raises(RuntimeError, match="No access_token"):
            tb.get_token("unknown")


def test_token_status_excludes_raw_token(tb):
    with patch("tokenbridge._client.requests.post", return_value=_mock_token_resp()):
        status = tb.token_status("p001")
    assert "access_token" not in status
    assert "expires_at" in status
    assert "refreshed" in status
    assert "scopes" in status


def test_token_status_missing_keys_skipped(tb):
    with patch("tokenbridge._client.requests.post",
               return_value=_mock_token_resp({"scopes": None})):
        status = tb.token_status("p001")
    # scopes key should still appear (value is None, key exists in response)
    assert "expires_at" in status
