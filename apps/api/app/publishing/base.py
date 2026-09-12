"""PublishingProvider abstraction for CMS syndication."""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class PublishResult:
    is_success: bool
    published_url: Optional[str] = None
    post_id: Optional[str] = None
    status: str = "draft"  # draft, publish
    error_message: Optional[str] = None


class PublishingProvider(ABC):
    @property
    @abstractmethod
    def platform_name(self) -> str:
        """Name of the CMS platform (e.g. 'WordPress', 'Ghost', 'Webflow')."""
        pass

    @abstractmethod
    async def publish_article(
        self,
        title: str,
        content: str,
        slug: str,
        target_status: str = "draft",
        meta_description: Optional[str] = None,
        keywords: Optional[list] = None,
    ) -> PublishResult:
        """Publish or schedule post to the external CMS."""
        pass
