"""Server-Side Request Forgery (SSRF) protection and safe HTTP client."""
import ipaddress
import socket
from urllib.parse import urlparse
from typing import Tuple
import httpx
from app.core.config import settings
from app.core.errors import SSRFViolationError
from app.core.logging import logger

BLOCKED_NETWORKS = [ipaddress.ip_network(cidr) for cidr in settings.SSRF_BLOCKED_RANGES]


def is_ip_blocked(ip_str: str) -> bool:
    """Check if an IP address falls into any blocked network range."""
    try:
        ip = ipaddress.ip_address(ip_str)
        # Check standard private, loopback, link-local, reserved properties
        if (
            ip.is_private
            or ip.is_loopback
            or ip.is_link_local
            or ip.is_multicast
            or ip.is_reserved
            or ip.is_unspecified
        ):
            return True

        # Check explicitly configured CIDR ranges
        for network in BLOCKED_NETWORKS:
            if ip in network:
                return True
        return False
    except ValueError:
        return True


def validate_url_safe(url: str) -> Tuple[bool, str]:
    """
    Validate that a URL is safe from SSRF attacks.
    Returns (is_safe, error_or_hostname).
    """
    try:
        parsed = urlparse(url)
    except Exception as e:
        return False, f"Invalid URL structure: {e}"

    if parsed.scheme.lower() not in ("http", "https"):
        return False, f"Unsupported scheme: {parsed.scheme}. Only http and https are permitted."

    hostname = parsed.hostname
    if not hostname:
        return False, "Missing hostname in URL."

    # Immediate rejection of known malicious or internal names
    blocked_hosts = {"localhost", "metadata.google.internal", "instance-data", "169.254.169.254"}
    if hostname.lower() in blocked_hosts or hostname.endswith(".localhost"):
        return False, f"Access to host '{hostname}' is prohibited."

    # DNS Resolution and IP checking
    try:
        addr_info = socket.getaddrinfo(hostname, None)
        for entry in addr_info:
            ip_str = entry[4][0]
            if is_ip_blocked(ip_str):
                return False, f"Destination resolves to blocked IP address '{ip_str}'."
    except socket.gaierror as e:
        return False, f"DNS resolution failed for '{hostname}': {e}"
    except Exception as e:
        return False, f"Host validation error: {e}"

    return True, hostname


async def safe_fetch_url(url: str, timeout: float = 10.0, max_redirects: int = 3) -> str:
    """
    Fetch content from a URL safely with SSRF checks on initial URL and redirects.
    """
    current_url = url
    for _ in range(max_redirects + 1):
        is_safe, reason = validate_url_safe(current_url)
        if not is_safe:
            logger.warning(f"SSRF violation prevented for URL '{current_url}': {reason}")
            raise SSRFViolationError(f"Security policy blocked request: {reason}")

        async with httpx.AsyncClient(timeout=timeout, follow_redirects=False) as client:
            try:
                response = await client.get(
                    current_url,
                    headers={"User-Agent": "AIBlogPlatform-ResearchAgent/1.0"}
                )
                # Check for redirect
                if response.is_redirect:
                    next_url = response.headers.get("location")
                    if not next_url:
                        break
                    # Normalize relative redirect
                    current_url = str(response.url.join(next_url))
                    continue

                response.raise_for_status()
                return response.text
            except httpx.HTTPError as e:
                logger.warning(f"HTTP request error fetching '{current_url}': {e}")
                raise

    raise SSRFViolationError("Too many redirects encountered during research fetch.")
