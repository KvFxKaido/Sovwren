"""Search Manager - Coordinates search adapters and Search Gate state

This is the main interface for the TUI to interact with external search.
It enforces Friction Class VI principles:
- Consent required (gate must be explicitly opened)
- Results are structured, not blended
- Provider attribution is always visible
"""

import asyncio
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Tuple

from config import SEARCH_GATE_DEFAULT
from .base import SearchAdapter, SearchResult, SearchError
from .duckduckgo import DuckDuckGoSearchAdapter
from .ollama import OllamaSearchAdapter


@dataclass
class SearchGateState:
    """Current state of the Search Gate.

    Visible in the TUI status bar to satisfy Class VI visibility requirements.
    """
    enabled: bool = False  # Local-only by default
    provider: str = ""  # Which adapter is active
    last_query: str = ""
    last_query_time: Optional[datetime] = None
    result_count: int = 0

    def status_text(self) -> str:
        """Format for TUI status bar."""
        if not self.enabled:
            return "Local"
        return f"Web ({self.provider})"


class SearchManager:
    """Manages search adapters and enforces Search Gate consent.

    Usage:
        manager = SearchManager()

        # Check if search is available
        if manager.is_available:
            # Open the gate (requires explicit consent)
            manager.open_gate()

            # Perform search
            results = await manager.search("What is RAG?")

            # Format for context injection
            context = manager.format_for_context(results)

            # Format for Citations Panel
            citations = manager.format_citations(results)

            # Close gate when done (optional - stays open for session)
            manager.close_gate()
    """

    def __init__(self):
        self._adapters: dict[str, SearchAdapter] = {}
        self._active_adapter: Optional[str] = None
        self._state = SearchGateState()

        # Initialize available adapters
        self._init_adapters()

        # Set default state from config
        if SEARCH_GATE_DEFAULT == "web":
            self.open_gate()

    def _init_adapters(self):
        """Initialize available search adapters based on configured API keys."""
        # DuckDuckGo - no API key needed, always available
        ddg = DuckDuckGoSearchAdapter()
        if ddg.is_configured:
            self._adapters["DuckDuckGo"] = ddg

        # Ollama - requires OLLAMA_API_KEY
        ollama = OllamaSearchAdapter()
        if ollama.is_configured:
            self._adapters["Ollama"] = ollama

        # Set first available adapter as default
        if self._adapters:
            self._active_adapter = list(self._adapters.keys())[0]

    @property
    def is_available(self) -> bool:
        """Check if any search adapter is configured."""
        return bool(self._adapters)

    @property
    def is_enabled(self) -> bool:
        """Check if Search Gate is currently open."""
        return self._state.enabled

    @property
    def state(self) -> SearchGateState:
        """Get current Search Gate state for TUI display."""
        return self._state

    @property
    def available_providers(self) -> List[str]:
        """List of configured search providers."""
        return list(self._adapters.keys())

    def open_gate(self, provider: Optional[str] = None) -> bool:
        """Open the Search Gate (enable web search).

        This is a consent action - Friction Class VI requires explicit opt-in.

        Args:
            provider: Specific provider to use, or None for default

        Returns:
            True if gate opened successfully
        """
        if not self._adapters:
            return False

        if provider and provider in self._adapters:
            self._active_adapter = provider
        elif not self._active_adapter:
            self._active_adapter = list(self._adapters.keys())[0]

        self._state.enabled = True
        self._state.provider = self._active_adapter
        return True

    def close_gate(self):
        """Close the Search Gate (return to local-only mode)."""
        self._state.enabled = False
        self._state.provider = ""
        self._state.result_count = 0

    def toggle_gate(self) -> bool:
        """Toggle Search Gate state. Returns new state."""
        if self._state.enabled:
            self.close_gate()
        else:
            self.open_gate()
        return self._state.enabled

    async def search(self, query: str, max_results: int = 5) -> Tuple[List[SearchResult], Optional[str]]:
        """Execute a search query.

        The gate must be open (consent given) for this to work.

        Args:
            query: The search query
            max_results: Maximum results to return

        Returns:
            Tuple of (results, error_message)
            If error_message is not None, results will be empty
        """
        if not self._state.enabled:
            return [], "Search Gate is closed. Open the gate to enable web search."

        if not self._active_adapter or self._active_adapter not in self._adapters:
            return [], "No search provider configured."

        adapter = self._adapters[self._active_adapter]

        try:
            results = await adapter.search(query, max_results)

            # Update state
            self._state.last_query = query
            self._state.last_query_time = datetime.now()
            self._state.result_count = len(results)

            return results, None

        except SearchError as e:
            return [], str(e)
        except Exception as e:
            return [], f"Search failed: {e}"

    async def health_check(self) -> dict[str, bool]:
        """Check health of all configured adapters.

        Returns dict of {provider_name: is_healthy}
        """
        results = {}
        for name, adapter in self._adapters.items():
            try:
                results[name] = await adapter.health_check()
            except Exception:
                results[name] = False
        return results

    def format_for_context(self, results: List[SearchResult]) -> str:
        """Format search results for injection into NeMo's context.

        This is how the Librarian pattern completes:
        - Results become structured context blocks
        - NeMo reads these and synthesizes an answer
        - NeMo cites the specific URLs in its response

        Returns:
            Formatted string for context injection
        """
        if not results:
            return ""

        blocks = [r.to_context_block() for r in results]
        header = f"[Web Search Results - {len(results)} sources found]\n\n"
        return header + "\n".join(blocks)

    def format_citations(self, results: List[SearchResult]) -> str:
        """Format results for the Citations Panel display.

        Returns markdown-formatted list of citations.
        """
        if not results:
            return "No sources found."

        citations = [r.to_citation() for r in results]
        return "\n".join(citations)

    async def cleanup(self):
        """Release resources from all adapters."""
        for adapter in self._adapters.values():
            await adapter.cleanup()


# Global search manager instance
search_manager = SearchManager()
