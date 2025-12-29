"""FAISS-based vector store for efficient similarity search"""
import asyncio
import faiss
import numpy as np
import os
import json
from typing import List, Tuple, Dict, Optional
from pathlib import Path
import time

from config import VECTOR_INDEX_PATH, TIMEOUTS, MAX_RETRIEVED_CHUNKS
from .embeddings import embedding_manager
from core.workspace_paths import find_repo_root

class VectorStore:
    def __init__(self, index_path: str = str(VECTOR_INDEX_PATH)):
        self.index_path = index_path
        self.index = None
        self.dimension = 384  # Default embedding dimension
        self.document_map = {}  # Maps index positions to document info
        self.is_initialized = False
        self._lock = asyncio.Lock()

    async def initialize(self):
        """Initialize or load existing vector index"""
        async with self._lock:
            if self.is_initialized:
                return
            
            await self._load_or_create_index()
            await self._prune_missing_file_urls()
            self.is_initialized = True

    @staticmethod
    def _resolve_file_url(url: str) -> Path | None:
        if not url or not isinstance(url, str):
            return None
        if not url.startswith("file://"):
            return None

        rel = url[len("file://") :]
        rel = rel.lstrip("/\\")
        if not rel:
            return None

        repo_root = find_repo_root(Path(__file__))
        return (repo_root / Path(rel)).resolve()

    def _is_missing_file_url(self, metadata: Dict) -> bool:
        """Return True if this metadata points to a missing local file."""
        try:
            url = (metadata or {}).get("url", "")
            path = self._resolve_file_url(url)
            if path is None:
                return False
            return not path.exists()
        except Exception:
            return False

    async def _prune_missing_file_urls(self) -> None:
        """Drop vectors whose `file://...` source no longer exists by rebuilding the index."""
        if not self.index or not self.document_map:
            return

        stale_keys = [
            idx
            for idx, doc_info in self.document_map.items()
            if self._is_missing_file_url(doc_info.get("metadata", {}))
        ]
        if not stale_keys:
            return

        remaining_texts: list[str] = []
        remaining_metadata: list[dict] = []
        for idx, doc_info in self.document_map.items():
            if idx in stale_keys:
                continue
            remaining_texts.append(doc_info.get("text", ""))
            remaining_metadata.append(doc_info.get("metadata", {}))

        print(f"Pruning {len(stale_keys)} stale vector(s) for deleted local file(s)...")

        await embedding_manager.initialize()
        self.dimension = embedding_manager.get_embedding_dimension()
        self.index = faiss.IndexFlatIP(self.dimension)
        self.document_map = {}

        if remaining_texts:
            embeddings = await embedding_manager.encode_text(remaining_texts)
            norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
            zero_mask = norms == 0
            if np.any(zero_mask):
                norms = np.where(zero_mask, 1.0, norms)
            embeddings = embeddings / norms

            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, self.index.add, embeddings.astype(np.float32))

            now = time.time()
            for i, (text, meta) in enumerate(zip(remaining_texts, remaining_metadata)):
                self.document_map[i] = {"text": text, "metadata": meta, "added_at": now}

        await self._save_index()

    async def _load_or_create_index(self):
        """Load existing index or create new one"""
        index_file = f"{self.index_path}.index"
        map_file_json = f"{self.index_path}.map.json"
        
        # Security: do not load pickle maps. If an old `.map` exists, rebuild.
        legacy_pickle_map = f"{self.index_path}.map"
        if os.path.exists(legacy_pickle_map) and not os.path.exists(map_file_json):
            print(
                "Warning: Found legacy pickle map file; refusing to load it for safety. "
                "Rebuilding vector index."
            )
            await self._create_new_index()
            return

        if os.path.exists(index_file) and os.path.exists(map_file_json):
            await self._load_index(index_file, map_file_json)
        else:
            await self._create_new_index()

    async def _load_index(self, index_file: str, map_file: str):
        """Load existing FAISS index and document map"""
        try:
            loop = asyncio.get_event_loop()
            
            # Load index in thread pool
            self.index = await loop.run_in_executor(
                None, faiss.read_index, index_file
            )
            
            # Load document map (JSON; safe to parse)
            with open(map_file, 'r', encoding='utf-8') as f:
                raw = json.load(f)
                self.document_map = {int(k): v for k, v in raw.items()}
            
            self.dimension = self.index.d
            print(f"Loaded vector index with {self.index.ntotal} vectors")
            
        except Exception as e:
            print(f"Error loading index: {e}")
            await self._create_new_index()

    async def _create_new_index(self):
        """Create new FAISS index"""
        # Initialize embedding manager to get dimension
        await embedding_manager.initialize()
        self.dimension = embedding_manager.get_embedding_dimension()
        
        # Create FAISS index (using IndexFlatIP for cosine similarity)
        self.index = faiss.IndexFlatIP(self.dimension)
        self.document_map = {}
        
        print(f"Created new vector index with dimension {self.dimension}")

    async def add_documents(self, texts: List[str], metadata: List[Dict]):
        """Add documents to the vector store"""
        await self.initialize()
        
        if not texts:
            return
        
        start_time = time.time()
        
        try:
            # Generate embeddings
            embeddings = await embedding_manager.encode_text(texts)
            
            # Normalize embeddings for cosine similarity
            norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
            zero_mask = norms == 0
            if np.any(zero_mask):
                norms = np.where(zero_mask, 1.0, norms)
                print(f"Warning: {int(np.sum(zero_mask))} zero-norm embedding(s); skipping normalization for those rows")
            embeddings = embeddings / norms
            
            # Add to index
            start_idx = self.index.ntotal
            
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None, self.index.add, embeddings.astype(np.float32)
            )
            
            # Update document map
            for i, meta in enumerate(metadata):
                self.document_map[start_idx + i] = {
                    'text': texts[i],
                    'metadata': meta,
                    'added_at': time.time()
                }
            
            # Save index periodically
            if self.index.ntotal % 100 == 0:
                await self._save_index()
            
            elapsed = time.time() - start_time
            print(f"Added {len(texts)} documents in {elapsed:.2f}s")
            
        except Exception as e:
            print(f"Error adding documents: {e}")

    async def add_chunks(self, chunks: List[str], document_id: int, 
                        chunk_metadata: List[Dict] = None):
        """Add document chunks to vector store"""
        if not chunks:
            return
        
        if chunk_metadata is None:
            chunk_metadata = [{'document_id': document_id, 'chunk_index': i} 
                             for i in range(len(chunks))]
        
        # Add document_id to all metadata
        for meta in chunk_metadata:
            meta['document_id'] = document_id
        
        await self.add_documents(chunks, chunk_metadata)

    async def search(self, query: str, k: int = MAX_RETRIEVED_CHUNKS, 
                    threshold: float = 0.1) -> List[Tuple[str, float, Dict]]:
        """Search for similar documents"""
        await self.initialize()
        
        if self.index.ntotal == 0:
            return []
        
        start_time = time.time()
        
        try:
            # Generate query embedding
            query_embedding = await embedding_manager.encode_text([query])
            q_norm = np.linalg.norm(query_embedding)
            if q_norm == 0:
                print("Warning: zero-norm query embedding; returning no results")
                return []
            query_embedding = query_embedding / q_norm
            
            # Search in FAISS index
            loop = asyncio.get_event_loop()
            similarities, indices = await loop.run_in_executor(
                None, 
                self.index.search, 
                query_embedding.astype(np.float32), 
                min(k, self.index.ntotal)
            )
            
            # Filter results by threshold and prepare response
            results = []
            for sim, idx in zip(similarities[0], indices[0]):
                if sim >= threshold and idx in self.document_map:
                    doc_info = self.document_map[idx]
                    if self._is_missing_file_url(doc_info.get("metadata", {})):
                        continue
                    results.append((
                        doc_info['text'],
                        float(sim),
                        doc_info['metadata']
                    ))
            
            elapsed = time.time() - start_time
            if elapsed > TIMEOUTS["vector_search"]:
                print(f"Warning: Vector search took {elapsed:.2f}s")
            
            return results
            
        except Exception as e:
            print(f"Error searching vectors: {e}")
            return []

    async def search_by_document_id(self, document_id: int, 
                                   k: int = MAX_RETRIEVED_CHUNKS) -> List[Tuple[str, Dict]]:
        """Get chunks for a specific document"""
        await self.initialize()
        
        results = []
        for idx, doc_info in self.document_map.items():
            meta = doc_info['metadata']
            if meta.get('document_id') == document_id:
                results.append((doc_info['text'], meta))
        
        # Sort by chunk_index if available
        results.sort(key=lambda x: x[1].get('chunk_index', 0))
        return results[:k]

    async def _save_index(self):
        """Save FAISS index and document map to disk"""
        if not self.index:
            return
        
        try:
            # Ensure directory exists
            Path(self.index_path).parent.mkdir(parents=True, exist_ok=True)
            
            index_file = f"{self.index_path}.index"
            map_file = f"{self.index_path}.map.json"
            
            # Save index
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                None, faiss.write_index, self.index, index_file
            )
            
            # Save document map
            with open(map_file, 'w', encoding='utf-8') as f:
                json.dump({str(k): v for k, v in self.document_map.items()}, f, ensure_ascii=False, indent=2)
            
            print(f"Saved vector index with {self.index.ntotal} vectors")
            
        except Exception as e:
            print(f"Error saving index: {e}")

    async def get_stats(self) -> Dict:
        """Get vector store statistics"""
        await self.initialize()
        
        return {
            'total_vectors': self.index.ntotal if self.index else 0,
            'dimension': self.dimension,
            'index_size_mb': os.path.getsize(f"{self.index_path}.index") / 1024 / 1024 
                           if os.path.exists(f"{self.index_path}.index") else 0,
            'documents_count': len(set(
                doc['metadata'].get('document_id', -1) 
                for doc in self.document_map.values()
            )) if self.document_map else 0
        }

    async def remove_document(self, document_id: int):
        """Remove all chunks for a document (rebuilds index)"""
        await self.initialize()
        
        # Find indices to remove
        indices_to_remove = []
        for idx, doc_info in self.document_map.items():
            if doc_info['metadata'].get('document_id') == document_id:
                indices_to_remove.append(idx)
        
        if not indices_to_remove:
            return
        
        # Rebuild index without removed documents
        remaining_texts = []
        remaining_metadata = []
        
        for idx, doc_info in self.document_map.items():
            if idx not in indices_to_remove:
                remaining_texts.append(doc_info['text'])
                remaining_metadata.append(doc_info['metadata'])
        
        # Recreate index
        await self._create_new_index()
        
        if remaining_texts:
            await self.add_documents(remaining_texts, remaining_metadata)
        
        await self._save_index()
        print(f"Removed document {document_id} and rebuilt index")

    async def cleanup(self):
        """Save index on cleanup"""
        if self.index:
            await self._save_index()

# Global vector store instance
vector_store = VectorStore()
