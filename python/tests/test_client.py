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


def _mock_post(status: int = 200, body: dict = None):
    body = body or {"access_token": "tok_abc123", "expires_at": "2026-06-19T00:00:00Z", "refreshed": False}
    mock = MagicMock()
    mock.status_code = status
    mock.json.return_value = body
    mock.text = str(body)
    mock.raise_for_status = MagicMock(
        side_effect=None if status < 400 else Exception(f"HTTP {status}")
    )
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
    with patch("tokenbridge._client.requests.post", return_value=_mock_post()):
        token = tb.get_token("p001")
    assert token == "tok_abc123"


def test_get_token_missing_raises_with_auth_url(tb):
    """404 → error includes user ID and auth URL."""
    mock = _mock_post(status=404, body={"error": "not found"})
    with patch("tokenbridge._client.requests.post", return_value=mock):
        with pytest.raises(RuntimeError) as exc:
            tb.get_token("unknown")
    msg = str(exc.value)
    assert "unknown" in msg
    assert "auth-start" in msg   # auth URL included in error


def test_get_token_expired_raises_with_reauth_url(tb):
    """401 → error tells user to re-authorise and includes auth URL."""
    mock = _mock_post(status=401, body={"error": "refresh failed"})
    with patch("tokenbridge._client.requests.post", return_value=mock):
        with pytest.raises(RuntimeError) as exc:
            tb.get_token("p001")
    msg = str(exc.value)
    assert "p001" in msg
    assert "auth-start" in msg


def test_get_token_unexpected_body_raises(tb):
    """200 but no access_token key → RuntimeError."""
    mock = _mock_post(body={"something": "else"})
    with patch("tokenbridge._client.requests.post", return_value=mock):
        with pytest.raises(RuntimeError, match="Unexpected response"):
            tb.get_token("p001")


# ── Provider proxy ────────────────────────────────────────────────────────────

def test_google_proxy_repr(tb):
    assert "google-health" in repr(tb.google)


def test_withings_proxy_repr(tb):
    assert "withings" in repr(tb.withings)


def test_unknown_provider_raises(tb):
    with pytest.raises(ValueError, match="Unknown provider"):
        tb.fetch("p001", "sleep", "2026-05-01", "2026-05-31", provider="nonexistent")
