"""DuckDuckGo Search Adapter - No API key required

Simple web search using DuckDuckGo. Works out of the box.
"""

import asyncio
from datetime import datetime
from typing import List
from urllib.parse import urlparse

from .base import SearchAdapter, SearchResult, SearchError


class DuckDuckGoSearchAdapter(SearchAdapter):
    """Search adapter using DuckDuckGo.

    No API key required - just install duckduckgo-search package.
    """

    def __init__(self):
        self._ddgs = None

    @property
    def provider_name(self) -> str:
        return "DuckDuckGo"

    @property
    def is_configured(self) -> bool:
        # Always configured - no API key needed
        try:
            from duckduckgo_search import DDGS
            return True
        except ImportError:
            return False

    def _ensure_client(self):
        """Lazily initialize the DuckDuckGo client."""
        if self._ddgs is not None:
            return

        try:
            from duckduckgo_search import DDGS
            self._ddgs = DDGS()
        except ImportError:
            raise SearchError(
                "duckduckgo-search package not installed. Run: pip install duckduckgo-search",
                provider=self.provider_name,
                recoverable=False
            )

    async def health_check(self) -> bool:
        """Verify we can use DuckDuckGo."""
        try:
            self._ensure_client()
            return True
        except Exception:
            return False

    async def search(self, query: str, max_results: int = 5) -> List[SearchResult]:
        """Execute a search via DuckDuckGo.

        Returns structured results with URLs, titles, and snippets.
        """
        self._ensure_client()

        try:
            # Run the synchronous DDG call in a thread
            results_raw = await asyncio.to_thread(
                self._ddgs.text,
                query,
                max_results=max_results
            )

            results = []
            for item in results_raw:
                url = item.get("href", "")
                title = item.get("title", "")
                snippet = item.get("body", "")

                if not url or not title:
                    continue

                # Extract domain
                try:
                    domain = urlparse(url).netloc
                except Exception:
                    domain = ""

                results.append(SearchResult(
                    url=url,
                    title=title,
                    snippet=snippet,
                    retrieved_at=datetime.now(),
                    provider=self.provider_name,
                    domain=domain
                ))

            return results

        except Exception as e:
            raise SearchError(
                f"Search failed: {e}",
                provider=self.provider_name,
                recoverable=True
            )

    async def cleanup(self):
        """Release resources."""
        self._ddgs = None
