"""Abstract base class for search adapters (Friction Class VI compliant)

Design principles:
- Search APIs are dynamic indexers, not oracles
- All results return structured data with provenance
- No blending of sources invisibly
- Chain of custody preserved via explicit URLs and timestamps
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass
class SearchResult:
    """A single search result with full provenance.

    This is the atomic unit returned by all search adapters.
    Sovwren injects these into context as if they were local files,
    then synthesizes answers citing specific URLs.
    """
    url: str
    title: str
    snippet: str  # 2-3 sentence summary

    # Provenance (Friction Class VI: reproducibility)
    retrieved_at: datetime = field(default_factory=datetime.now)
    provider: str = ""  # Which search adapter returned this

    # Optional enrichment
    domain: str = ""
    content_hash: Optional[str] = None  # For reproducibility checks

    def to_context_block(self) -> str:
        """Format this result for injection into Sovwren's context.

        Returns a structured block that makes the source explicit
        and prevents source laundering.
        """
        return f"""[Source: {self.url}]
Title: {self.title}
{self.snippet}
---"""

    def to_citation(self) -> str:
        """Format for Citations Panel display."""
        return f"- [{self.title}]({self.url})"

    def to_dict(self) -> dict:
        """Serialize for storage/caching."""
        return {
            "url": self.url,
            "title": self.title,
            "snippet": self.snippet,
            "retrieved_at": self.retrieved_at.isoformat(),
            "provider": self.provider,
            "domain": self.domain,
            "content_hash": self.content_hash
        }


class SearchAdapter(ABC):
    """Abstract base class for all search adapters.

    Implementations must:
    1. Return structured SearchResult objects (not raw text)
    2. Include provider attribution
    3. Handle errors gracefully without silent fallback
    4. Respect rate limits

    The adapter is a Librarian, not an Oracle:
    - It finds sources and returns metadata
    - It does NOT synthesize answers
    - Sovwren does the synthesis, citing the sources
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Human-readable name for this search provider."""
        pass

    @property
    @abstractmethod
    def is_configured(self) -> bool:
        """Check if this adapter has valid API credentials."""
        pass

    @abstractmethod
    async def search(self, query: str, max_results: int = 5) -> List[SearchResult]:
        """Execute a search query using the Librarian pattern.

        The prompt sent to the API should be:
        "Find sources for {query} and return them as structured data
        with URL, title, and a 2-sentence summary snippet."

        NOT: "What is {query}?" (that's Oracle mode, violates Class VI)

        Args:
            query: The search query from the Steward
            max_results: Maximum number of results to return

        Returns:
            List of SearchResult objects with full provenance

        Raises:
            SearchError: On API failures (never silent fallback)
        """
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """Verify the adapter can reach its API endpoint."""
        pass

    async def cleanup(self):
        """Release any held resources (sessions, etc.)."""
        pass


class SearchError(Exception):
    """Raised when a search operation fails.

    Errors are surfaced, not swallowed (Friction Class I compliance).
    """
    def __init__(self, message: str, provider: str, recoverable: bool = False):
        self.message = message
        self.provider = provider
        self.recoverable = recoverable
        super().__init__(f"[{provider}] {message}")
