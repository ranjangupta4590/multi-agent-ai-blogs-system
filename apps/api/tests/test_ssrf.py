"""SSRF protection security tests."""
import pytest
from app.core.errors import SSRFViolationError
from app.core.ssrf import is_ip_blocked, validate_url_safe, safe_fetch_url


def test_blocked_ip_ranges():
    """Verify loopback, RFC 1918, and link-local ranges are identified as blocked."""
    assert is_ip_blocked("127.0.0.1") is True
    assert is_ip_blocked("127.0.1.1") is True
    assert is_ip_blocked("10.0.0.1") is True
    assert is_ip_blocked("10.254.0.1") is True
    assert is_ip_blocked("172.16.0.1") is True
    assert is_ip_blocked("172.31.255.254") is True
    assert is_ip_blocked("192.168.1.1") is True
    assert is_ip_blocked("169.254.169.254") is True  # AWS / Cloud Metadata
    assert is_ip_blocked("::1") is True


def test_url_validation_blocks_internal_hosts():
    """Verify localhost and internal hostnames are blocked."""
    is_safe, msg = validate_url_safe("http://localhost:8080/admin")
    assert is_safe is False
    assert "prohibited" in msg or "blocked" in msg

    is_safe, msg = validate_url_safe("http://127.0.0.1/secret")
    assert is_safe is False

    is_safe, msg = validate_url_safe("http://169.254.169.254/latest/meta-data/")
    assert is_safe is False

    is_safe, msg = validate_url_safe("ftp://example.com/file")
    assert is_safe is False  # Unsupported scheme


@pytest.mark.asyncio
async def test_safe_fetch_blocks_ssrf():
    """Attempting to fetch a blocked URL raises SSRFViolationError."""
    with pytest.raises(SSRFViolationError):
        await safe_fetch_url("http://127.0.0.1:9090/internal-metrics")
