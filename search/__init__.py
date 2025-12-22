"""Search adapters for the Search Gate (Friction Class VI)

This module provides structured retrieval via external APIs,
implementing the Librarian Pattern:

    Steward -> Search Gate (consent) -> NeMo -> Librarian prompt -> Search API
                                                                        |
                                               JSON: {url, title, snippet}
                                                                        |
    Citations Panel <- Context injection <- NeMo synthesizes answer citing sources

The local model (NeMo) never trusts the API's answer directly.
It uses the API as a dynamic indexer, preserving chain of custody.
"""

from .base import SearchAdapter, SearchResult, SearchError
from .duckduckgo import DuckDuckGoSearchAdapter
from .ollama import OllamaSearchAdapter
from .manager import SearchManager, SearchGateState, search_manager

__all__ = [
    "SearchAdapter",
    "SearchResult",
    "SearchError",
    "DuckDuckGoSearchAdapter",
    "OllamaSearchAdapter",
    "SearchManager",
    "SearchGateState",
    "search_manager",
]
