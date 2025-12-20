"""Gemini Search Adapter - Uses Google's grounded search

Implements the Librarian Pattern:
- Gemini is asked to FIND SOURCES, not answer questions
- Returns structured JSON with URLs, titles, and snippets
- NeMo synthesizes the final answer citing these sources

This keeps the chain of custody intact and prevents source laundering.
"""

import asyncio
import json
import os
import re
from datetime import datetime
from typing import List, Optional
from urllib.parse import urlparse

from .base import SearchAdapter, SearchResult, SearchError


# Librarian prompt template - asks for sources, not answers
LIBRARIAN_PROMPT = """You are a research librarian. Your job is to find sources, not answer questions.

For the query below, find relevant web sources and return ONLY a JSON array.
Each item must have exactly these fields:
- "url": the full URL of the source
- "title": the page title
- "snippet": a 2-sentence summary of what this source contains

Do not answer the question yourself. Do not add commentary.
Return ONLY valid JSON, nothing else.

Query: {query}

Respond with a JSON array like:
[
  {{"url": "https://...", "title": "...", "snippet": "..."}},
  {{"url": "https://...", "title": "...", "snippet": "..."}}
]"""


class GeminiSearchAdapter(SearchAdapter):
    """Search adapter using Gemini with Google Search grounding.

    Uses the google-generativeai package with grounded search enabled.
    Gemini acts as a Librarian - finding and summarizing sources,
    not answering the question directly.
    """

    def __init__(self, api_key: Optional[str] = None):
        """Initialize with API key from param or environment.

        Args:
            api_key: Gemini API key. Falls back to GEMINI_API_KEY env var.
        """
        self._api_key = api_key or os.environ.get("GEMINI_API_KEY", "")
        self._client = None
        self._model = None

    @property
    def provider_name(self) -> str:
        return "Gemini"

    @property
    def is_configured(self) -> bool:
        return bool(self._api_key)

    def _ensure_client(self):
        """Lazily initialize the Gemini client."""
        if self._client is not None:
            return

        if not self.is_configured:
            raise SearchError(
                "Gemini API key not configured. Set GEMINI_API_KEY environment variable.",
                provider=self.provider_name,
                recoverable=False
            )

        try:
            import google.generativeai as genai
            genai.configure(api_key=self._api_key)

            # Use Gemini 2.5 Flash with Google Search grounding
            self._client = genai
            self._model = genai.GenerativeModel(
                'gemini-2.5-flash',
                tools='google_search_retrieval'
            )
        except ImportError:
            raise SearchError(
                "google-generativeai package not installed. Run: pip install google-generativeai",
                provider=self.provider_name,
                recoverable=False
            )
        except Exception as e:
            raise SearchError(
                f"Failed to initialize Gemini client: {e}",
                provider=self.provider_name,
                recoverable=False
            )

    async def health_check(self) -> bool:
        """Verify we can reach Gemini API."""
        try:
            self._ensure_client()
            # Simple ping - generate a tiny response
            response = await asyncio.to_thread(
                self._model.generate_content,
                "Respond with 'ok'"
            )
            return bool(response.text)
        except Exception:
            return False

    async def search(self, query: str, max_results: int = 5) -> List[SearchResult]:
        """Execute a grounded search via Gemini.

        Uses the Librarian prompt to ask Gemini to find sources,
        not answer the question. Returns structured results
        with full provenance for the Citations Panel.
        """
        self._ensure_client()

        prompt = LIBRARIAN_PROMPT.format(query=query)

        try:
            # Run the synchronous Gemini call in a thread
            response = await asyncio.to_thread(
                self._model.generate_content,
                prompt
            )

            # Parse the JSON response
            results = self._parse_response(response.text, max_results)

            # Enrich with provenance
            for result in results:
                result.provider = self.provider_name
                result.retrieved_at = datetime.now()
                # Extract domain from URL
                try:
                    result.domain = urlparse(result.url).netloc
                except Exception:
                    result.domain = ""

            return results

        except json.JSONDecodeError as e:
            raise SearchError(
                f"Gemini returned invalid JSON: {e}",
                provider=self.provider_name,
                recoverable=True
            )
        except Exception as e:
            raise SearchError(
                f"Search failed: {e}",
                provider=self.provider_name,
                recoverable=True
            )

    def _parse_response(self, text: str, max_results: int) -> List[SearchResult]:
        """Parse Gemini's JSON response into SearchResult objects.

        Handles common LLM output quirks (markdown code blocks, etc.)
        """
        # Strip markdown code blocks if present
        text = text.strip()
        if text.startswith("```"):
            # Remove ```json or ``` prefix
            text = re.sub(r'^```(?:json)?\s*', '', text)
            text = re.sub(r'\s*```$', '', text)

        # Try to find JSON array in the response
        # Sometimes models wrap it in extra text
        json_match = re.search(r'\[[\s\S]*\]', text)
        if json_match:
            text = json_match.group(0)

        data = json.loads(text)

        if not isinstance(data, list):
            raise ValueError("Expected JSON array")

        results = []
        for item in data[:max_results]:
            if not isinstance(item, dict):
                continue

            url = item.get("url", "")
            title = item.get("title", "")
            snippet = item.get("snippet", "")

            # Skip invalid entries
            if not url or not title:
                continue

            results.append(SearchResult(
                url=url,
                title=title,
                snippet=snippet
            ))

        return results

    async def cleanup(self):
        """Release resources."""
        self._client = None
        self._model = None


# Convenience function for quick searches
async def gemini_search(query: str, api_key: Optional[str] = None, max_results: int = 5) -> List[SearchResult]:
    """Quick search using Gemini.

    Example:
        results = await gemini_search("What is RAG in AI?")
        for r in results:
            print(r.to_citation())
    """
    adapter = GeminiSearchAdapter(api_key=api_key)
    try:
        return await adapter.search(query, max_results)
    finally:
        await adapter.cleanup()
