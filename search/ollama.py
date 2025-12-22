"""Ollama Web Search Adapter - Cloud-based search via Ollama API

Requires:
- Free Ollama account
- OLLAMA_API_KEY environment variable

Docs: https://docs.ollama.com/capabilities/web-search
"""

import os
from datetime import datetime
from typing import List, Optional
from urllib.parse import urlparse

import httpx

from .base import SearchAdapter, SearchResult, SearchError


class OllamaSearchAdapter(SearchAdapter):
    """Search adapter using Ollama's Web Search API.

    This is a cloud API (not local Ollama) that provides web search
    with structured results. Requires an API key from ollama.com.
    """

    API_URL = "https://ollama.com/api/web_search"

    def __init__(self, api_key: Optional[str] = None):
        self._api_key = api_key or os.getenv("OLLAMA_API_KEY")
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def provider_name(self) -> str:
        return "Ollama"

    @property
    def is_configured(self) -> bool:
        return bool(self._api_key)

    def _ensure_client(self):
        """Lazily initialize the HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=30.0,
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json"
                }
            )

    async def health_check(self) -> bool:
        """Verify we can reach the Ollama API."""
        if not self.is_configured:
            return False

        try:
            self._ensure_client()
            # Do a minimal search to verify connectivity
            response = await self._client.post(
                self.API_URL,
                json={"query": "test", "max_results": 1}
            )
            return response.status_code == 200
        except Exception:
            return False

    async def search(self, query: str, max_results: int = 5) -> List[SearchResult]:
        """Execute a search via Ollama Web Search API.

        Returns structured results with URLs, titles, and snippets.
        """
        if not self.is_configured:
            raise SearchError(
                "OLLAMA_API_KEY not set. Get one at ollama.com",
                provider=self.provider_name,
                recoverable=False
            )

        self._ensure_client()

        try:
            # Ollama caps at 10 results
            capped_max = min(max_results, 10)

            response = await self._client.post(
                self.API_URL,
                json={
                    "query": query,
                    "max_results": capped_max
                }
            )

            if response.status_code == 401:
                raise SearchError(
                    "Invalid API key",
                    provider=self.provider_name,
                    recoverable=False
                )

            if response.status_code != 200:
                raise SearchError(
                    f"API returned {response.status_code}: {response.text}",
                    provider=self.provider_name,
                    recoverable=True
                )

            data = response.json()
            results = []

            # Ollama returns: results[] with url, title, content
            for item in data.get("results", []):
                url = item.get("url", "")
                title = item.get("title", "")
                snippet = item.get("content", "")

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

        except SearchError:
            raise
        except httpx.TimeoutException:
            raise SearchError(
                "Request timed out",
                provider=self.provider_name,
                recoverable=True
            )
        except Exception as e:
            raise SearchError(
                f"Search failed: {e}",
                provider=self.provider_name,
                recoverable=True
            )

    async def cleanup(self):
        """Release HTTP client resources."""
        if self._client:
            await self._client.aclose()
            self._client = None
