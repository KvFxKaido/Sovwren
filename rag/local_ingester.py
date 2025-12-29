"""Local document ingester for Sovwren files.

Scans workspace directories and ingests markdown/text files into the RAG system.
Designed for the symbolic corpus vision from RAG-ROADMAP.md:
- Bookmarks
- Framework protocols
- Session logs
- Lore documents
"""
import asyncio
import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Set
from datetime import datetime

from .retriever import rag_retriever
from .vector_store import vector_store
from core.workspace_paths import find_repo_root


class LocalIngester:
    """Ingest local files into the RAG system."""

    # Default patterns to include
    DEFAULT_PATTERNS = ["**/*.md", "**/*.txt"]

    # Patterns to exclude (relative to workspace root)
    EXCLUDE_PATTERNS = [
        "**/node_modules/**",
        "**/.git/**",
        "**/venv/**",
        "**/__pycache__/**",
        "**/Sunset/**",  # Archived versions
        "**/Archive/**",  # Historical versions
        "**/*.pyc",
        "**/package-lock.json",
    ]

    # Files to skip by name
    SKIP_FILES = {
        "package-lock.json",
        "yarn.lock",
        ".gitignore",
        ".dockerignore",
    }

    # Minimum content length to bother indexing
    MIN_CONTENT_LENGTH = 100

    def __init__(self, workspace_root: str = None):
        self.workspace_root = Path(workspace_root) if workspace_root else find_repo_root(Path(__file__))
        self.ingested_files: Set[str] = set()
        self.stats = {
            "files_scanned": 0,
            "files_ingested": 0,
            "files_skipped": 0,
            "chunks_created": 0,
            "errors": []
        }

    def _should_exclude(self, file_path: Path) -> bool:
        """Check if file should be excluded."""
        rel_path = str(file_path.relative_to(self.workspace_root))

        # Check skip list
        if file_path.name in self.SKIP_FILES:
            return True

        # Check exclude patterns
        for pattern in self.EXCLUDE_PATTERNS:
            # Simple glob-style matching
            pattern_parts = pattern.replace("**", ".*").replace("*", "[^/\\\\]*")
            if re.match(pattern_parts, rel_path, re.IGNORECASE):
                return True

        return False

    def _extract_metadata(self, content: str, file_path: Path) -> Dict:
        """Extract metadata from file content and path."""
        metadata = {
            "source": "local_file",
            "file_path": str(file_path),
            "file_name": file_path.name,
            "file_type": file_path.suffix.lower(),
            "ingested_at": datetime.now().isoformat(),
        }

        # Detect document type from path
        rel_path = str(file_path.relative_to(self.workspace_root)).lower()

        if "bookmark" in rel_path:
            metadata["doc_type"] = "bookmark"
        elif "sovwren framework" in rel_path or "sovwren-framework" in rel_path:
            metadata["doc_type"] = "framework"
        elif "claude" in rel_path or "gemini" in rel_path or "agents" in rel_path:
            metadata["doc_type"] = "node_context"
        else:
            metadata["doc_type"] = "general"

        # Try to extract bookmark-specific metadata
        if metadata["doc_type"] == "bookmark":
            metadata.update(self._extract_bookmark_metadata(content))

        # Extract title from first heading or filename
        title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
        if title_match:
            metadata["title"] = title_match.group(1).strip()
        else:
            # Use filename without extension
            metadata["title"] = file_path.stem.replace("-", " ").replace("_", " ")

        return metadata

    def _extract_bookmark_metadata(self, content: str) -> Dict:
        """Extract bookmark-specific metadata."""
        bookmark_meta = {}

        # Look for common bookmark fields
        patterns = {
            "seed": r'Seed:\s*["\']?(.+?)["\']?\s*$',
            "function": r'Function:\s*(.+?)(?:\n|$)',
            "tags": r'Tags:\s*\[(.+?)\]',
            "timestamp": r'Timestamp:\s*(.+?)(?:\n|$)',
            "decay_policy": r'Decay Policy:\s*(.+?)(?:\n|$)',
        }

        for field, pattern in patterns.items():
            match = re.search(pattern, content, re.MULTILINE | re.IGNORECASE)
            if match:
                value = match.group(1).strip()
                if field == "tags":
                    # Parse tag array
                    bookmark_meta[field] = [t.strip().strip('"\'') for t in value.split(",")]
                else:
                    bookmark_meta[field] = value

        return bookmark_meta

    async def ingest_file(self, file_path: Path) -> Optional[int]:
        """Ingest a single file into the RAG system."""
        try:
            # Read file content
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()

            # Skip if too short
            if len(content.strip()) < self.MIN_CONTENT_LENGTH:
                self.stats["files_skipped"] += 1
                return None

            # Extract metadata
            metadata = self._extract_metadata(content, file_path)

            # Get relative path for cleaner display
            rel_path = str(file_path.relative_to(self.workspace_root))

            # Ingest into RAG system
            document_id = await rag_retriever.add_document(
                content=content,
                title=metadata.get("title", file_path.stem),
                url=f"file://{rel_path}",  # Use file:// URL for local files
                metadata=metadata
            )

            self.ingested_files.add(str(file_path))
            self.stats["files_ingested"] += 1

            return document_id

        except Exception as e:
            self.stats["errors"].append(f"{file_path}: {str(e)}")
            return None

    async def ingest_directory(self, directory: Path = None,
                               patterns: List[str] = None,
                               recursive: bool = True) -> Dict:
        """Ingest all matching files from a directory."""
        directory = directory or self.workspace_root
        patterns = patterns or self.DEFAULT_PATTERNS

        # Reset stats for this run
        self.stats = {
            "files_scanned": 0,
            "files_ingested": 0,
            "files_skipped": 0,
            "chunks_created": 0,
            "errors": []
        }

        files_to_ingest = []

        # Collect files matching patterns
        for pattern in patterns:
            if recursive:
                matches = directory.glob(pattern)
            else:
                matches = directory.glob(pattern.replace("**/", ""))

            for file_path in matches:
                if file_path.is_file() and not self._should_exclude(file_path):
                    files_to_ingest.append(file_path)

        # Remove duplicates
        files_to_ingest = list(set(files_to_ingest))
        self.stats["files_scanned"] = len(files_to_ingest)

        print(f"Found {len(files_to_ingest)} files to ingest...")

        # Ingest files with progress
        for i, file_path in enumerate(files_to_ingest):
            if (i + 1) % 10 == 0:
                print(f"  Progress: {i + 1}/{len(files_to_ingest)}")

            await self.ingest_file(file_path)

        # Get final stats from vector store
        rag_stats = await rag_retriever.get_stats()
        self.stats["total_vectors"] = rag_stats.get("vector_store", {}).get("total_vectors", 0)

        return self.stats

    async def ingest_sovwren_corpus(self) -> Dict:
        """Ingest the full Sovwren symbolic corpus.

        RAG is scoped to the workspace folder to keep context focused.
        """
        print("=" * 50)
        print("SOVWREN CORPUS INGESTION")
        print("=" * 50)

        # Define corpus directories with their document types
        # RAG is scoped to workspace folder only
        corpus_dirs = [
            # Canonical bookmark location is `workspace/bookmarks/` (lowercase).
            ("workspace/bookmarks", ["**/*.txt", "**/*.md"]),
        ]

        total_stats = {
            "files_scanned": 0,
            "files_ingested": 0,
            "files_skipped": 0,
            "errors": [],
            "by_type": {}
        }

        for subdir, patterns in corpus_dirs:
            target_dir = self.workspace_root / subdir if subdir != "." else self.workspace_root

            if not target_dir.exists():
                print(f"  Skipping {subdir} (not found)")
                continue

            print(f"\nIngesting: {subdir}")
            print("-" * 30)

            # For root directory, don't recurse into subdirs
            recursive = subdir != "."

            stats = await self.ingest_directory(
                directory=target_dir,
                patterns=patterns,
                recursive=recursive
            )

            # Aggregate stats
            total_stats["files_scanned"] += stats["files_scanned"]
            total_stats["files_ingested"] += stats["files_ingested"]
            total_stats["files_skipped"] += stats["files_skipped"]
            total_stats["errors"].extend(stats["errors"])
            total_stats["by_type"][subdir] = stats["files_ingested"]

            print(f"  Ingested: {stats['files_ingested']} files")

        # Save the index to disk
        print("\nSaving index to disk...")
        await vector_store._save_index()

        # Final stats
        rag_stats = await rag_retriever.get_stats()
        total_stats["total_vectors"] = rag_stats.get("vector_store", {}).get("total_vectors", 0)

        print("\n" + "=" * 50)
        print("INGESTION COMPLETE")
        print("=" * 50)
        print(f"Total files scanned: {total_stats['files_scanned']}")
        print(f"Total files ingested: {total_stats['files_ingested']}")
        print(f"Total vectors in index: {total_stats['total_vectors']}")

        if total_stats["errors"]:
            print(f"\nErrors ({len(total_stats['errors'])}):")
            for err in total_stats["errors"][:5]:
                print(f"  - {err}")
            if len(total_stats["errors"]) > 5:
                print(f"  ... and {len(total_stats['errors']) - 5} more")

        return total_stats

    async def ingest_single_path(self, path: str) -> Dict:
        """Ingest a single file or directory by path."""
        target = Path(path)

        if not target.exists():
            # Try relative to workspace
            target = self.workspace_root / path

        if not target.exists():
            return {"error": f"Path not found: {path}"}

        if target.is_file():
            doc_id = await self.ingest_file(target)
            # Save index after ingestion
            await vector_store._save_index()
            return {
                "files_ingested": 1 if doc_id else 0,
                "document_id": doc_id
            }
        else:
            result = await self.ingest_directory(target)
            # Save index after ingestion
            await vector_store._save_index()
            return result


# Global ingester instance
local_ingester = LocalIngester()
