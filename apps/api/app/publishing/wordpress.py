"""WordPress publishing provider implementation using WP REST API v2."""
import base64
from typing import Optional
import httpx
from app.core.errors import SSRFViolationError
from app.core.logging import logger
from app.core.ssrf import validate_url_safe
from app.publishing.base import PublishingProvider, PublishResult


class WordPressProvider(PublishingProvider):
    def __init__(self, site_url: str, username: str, application_password: str):
        self.site_url = site_url.rstrip("/")
        self.username = username
        self.application_password = application_password

    @property
    def platform_name(self) -> str:
        return "WordPress"

    def _auth_header(self) -> str:
        credentials = f"{self.username}:{self.application_password}"
        encoded = base64.b64encode(credentials.encode()).decode("utf-8")
        return f"Basic {encoded}"

    async def publish_article(
        self,
        title: str,
        content: str,
        slug: str,
        target_status: str = "draft",
        meta_description: Optional[str] = None,
        keywords: Optional[list] = None,
    ) -> PublishResult:
        # SSRF defense on destination site URL
        is_safe, msg = validate_url_safe(self.site_url)
        if not is_safe:
            raise SSRFViolationError(f"WordPress site URL rejected by SSRF guard: {msg}")

        endpoint = f"{self.site_url}/wp-json/wp/v2/posts"
        headers = {
            "Authorization": self._auth_header(),
            "Content-Type": "application/json",
            "User-Agent": "AIBlogPlatform-Publisher/1.0",
        }

        payload = {
            "title": title,
            "content": content,
            "slug": slug,
            "status": target_status,
        }
        if meta_description:
            payload["excerpt"] = meta_description

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(endpoint, headers=headers, json=payload)
                if resp.status_code in (200, 201):
                    data = resp.json()
                    return PublishResult(
                        is_success=True,
                        published_url=data.get("link"),
                        post_id=str(data.get("id")),
                        status=target_status,
                    )
                logger.error(f"WordPress publish error {resp.status_code}: {resp.text}")
                return PublishResult(
                    is_success=False,
                    status=target_status,
                    error_message=f"WordPress API returned status {resp.status_code}",
                )
        except Exception as e:
            logger.error(f"WordPress publish network exception: {e}")
            return PublishResult(
                is_success=False,
                status=target_status,
                error_message=str(e),
            )
