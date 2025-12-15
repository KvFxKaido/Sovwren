"""Database operations for Jarvis AI Agent"""
import sqlite3
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import asyncio
import aiosqlite
from config import DATABASE_PATH

class Database:
    def __init__(self, db_path: str = str(DATABASE_PATH)):
        self.db_path = db_path
        self._connection = None
        self._setup_complete = False

    async def initialize(self):
        """Initialize database and create tables"""
        if self._setup_complete:
            return
            
        async with aiosqlite.connect(self.db_path) as db:
            await self._create_tables(db)
            await db.commit()
        
        self._setup_complete = True

    async def _create_tables(self, db):
        """Create all necessary tables"""
        # Conversations table
        await db.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                user_message TEXT NOT NULL,
                ai_response TEXT NOT NULL,
                model_used TEXT NOT NULL,
                context_used TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                embedding_vector BLOB
            )
        """)

        # Documents table for scraped/ingested content
        await db.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                url TEXT,
                title TEXT,
                content TEXT NOT NULL,
                content_type TEXT DEFAULT 'text',
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Document chunks for RAG
        await db.execute("""
            CREATE TABLE IF NOT EXISTS document_chunks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                document_id INTEGER,
                chunk_text TEXT NOT NULL,
                chunk_index INTEGER,
                embedding_vector BLOB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (document_id) REFERENCES documents (id)
            )
        """)

        # Models tracking
        await db.execute("""
            CREATE TABLE IF NOT EXISTS models (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                model_name TEXT UNIQUE NOT NULL,
                is_available BOOLEAN DEFAULT TRUE,
                last_used TIMESTAMP,
                usage_count INTEGER DEFAULT 0,
                avg_response_time REAL DEFAULT 0.0,
                metadata TEXT
            )
        """)

        # User preferences
        await db.execute("""
            CREATE TABLE IF NOT EXISTS user_preferences (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Sessions table for resume chat feature
        await db.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                message_count INTEGER DEFAULT 0,
                first_message_preview TEXT,
                model_used TEXT
            )
        """)

        # Protocol Events table (Code Pilot spec: store events, not interpretations)
        # Stores: consent_checkpoint, rupture_logged, pattern_ticket_created,
        #         mode_changed, lens_changed, idleness_toggled, context_band_transition
        await db.execute("""
            CREATE TABLE IF NOT EXISTS protocol_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                event_type TEXT NOT NULL,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_id) REFERENCES sessions (id)
            )
        """)

        # Create indexes for performance
        await db.execute("CREATE INDEX IF NOT EXISTS idx_conversations_session ON conversations(session_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_documents_url ON documents(url)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_chunks_document ON document_chunks(document_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_sessions_last_active ON sessions(last_active DESC)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_protocol_events_session ON protocol_events(session_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_protocol_events_type ON protocol_events(event_type)")

    async def add_conversation(self, session_id: str, user_message: str, 
                             ai_response: str, model_used: str, 
                             context_used: Optional[str] = None) -> int:
        """Add a conversation record"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                INSERT INTO conversations (session_id, user_message, ai_response, model_used, context_used)
                VALUES (?, ?, ?, ?, ?)
            """, (session_id, user_message, ai_response, model_used, context_used))
            
            await db.commit()
            return cursor.lastrowid

    async def add_document(self, url: str, title: str, content: str, 
                          content_type: str = 'text', metadata: Dict = None) -> int:
        """Add a document record"""
        metadata_json = json.dumps(metadata) if metadata else None
        
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                INSERT OR REPLACE INTO documents (url, title, content, content_type, metadata)
                VALUES (?, ?, ?, ?, ?)
            """, (url, title, content, content_type, metadata_json))
            
            await db.commit()
            return cursor.lastrowid

    async def add_document_chunk(self, document_id: int, chunk_text: str, 
                               chunk_index: int) -> int:
        """Add a document chunk"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                INSERT INTO document_chunks (document_id, chunk_text, chunk_index)
                VALUES (?, ?, ?)
            """, (document_id, chunk_text, chunk_index))
            
            await db.commit()
            return cursor.lastrowid

    async def get_recent_conversations(self, session_id: str, limit: int = 10) -> List[Dict]:
        """Get recent conversations for context"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT user_message, ai_response, model_used, created_at
                FROM conversations 
                WHERE session_id = ?
                ORDER BY created_at DESC 
                LIMIT ?
            """, (session_id, limit))
            
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def get_documents_by_query(self, query: str, limit: int = 5) -> List[Dict]:
        """Search documents by content (basic text search)"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT id, title, content, url, metadata
                FROM documents 
                WHERE content LIKE ? OR title LIKE ?
                ORDER BY last_accessed DESC
                LIMIT ?
            """, (f"%{query}%", f"%{query}%", limit))
            
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def get_document_by_url(self, url: str) -> Optional[Dict]:
        """Get a document by exact URL (used to avoid duplicate ingestion)."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT id, title, url, metadata, created_at, last_accessed
                FROM documents
                WHERE url = ?
                LIMIT 1
            """, (url,))

            row = await cursor.fetchone()
            return dict(row) if row else None

    async def update_model_stats(self, model_name: str, response_time: float):
        """Update model usage statistics"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT OR REPLACE INTO models (model_name, last_used, usage_count, avg_response_time)
                VALUES (?, CURRENT_TIMESTAMP, 
                    COALESCE((SELECT usage_count FROM models WHERE model_name = ?), 0) + 1,
                    COALESCE((SELECT avg_response_time FROM models WHERE model_name = ?), 0) * 0.8 + ? * 0.2
                )
            """, (model_name, model_name, model_name, response_time))
            
            await db.commit()

    async def get_available_models(self) -> List[str]:
        """Get list of available models"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                SELECT model_name FROM models 
                WHERE is_available = TRUE
                ORDER BY usage_count DESC
            """)
            
            rows = await cursor.fetchall()
            return [row[0] for row in rows]

    async def set_preference(self, key: str, value: str):
        """Set user preference"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT OR REPLACE INTO user_preferences (key, value, updated_at)
                VALUES (?, ?, CURRENT_TIMESTAMP)
            """, (key, value))
            
            await db.commit()

    async def get_preference(self, key: str, default: str = None) -> str:
        """Get user preference"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                SELECT value FROM user_preferences WHERE key = ?
            """, (key,))
            
            row = await cursor.fetchone()
            return row[0] if row else default

    async def cleanup_old_data(self, days: int = 30):
        """Clean up old conversation data"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                DELETE FROM conversations 
                WHERE created_at < datetime('now', '-' || ? || ' days')
            """, (days,))
            
            await db.commit()

    # ==================== Session Management ====================
    
    async def create_session(self, session_id: str, model_used: str = None) -> str:
        """Create a new session record"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT OR IGNORE INTO sessions (id, model_used, created_at, last_active)
                VALUES (?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            """, (session_id, model_used))
            await db.commit()
        return session_id

    async def update_session(self, session_id: str, message_count: int = None, 
                            first_message: str = None, model_used: str = None):
        """Update session metadata"""
        async with aiosqlite.connect(self.db_path) as db:
            updates = ["last_active = CURRENT_TIMESTAMP"]
            params = []
            
            if message_count is not None:
                updates.append("message_count = ?")
                params.append(message_count)
            
            if first_message is not None:
                # Auto-generate name from first message if no name set
                preview = first_message[:50] + "..." if len(first_message) > 50 else first_message
                updates.append("first_message_preview = ?")
                params.append(preview)
                # Also set as auto-name if no name exists
                updates.append("name = COALESCE(name, ?)")
                params.append(preview[:30] + "..." if len(preview) > 30 else preview)
            
            if model_used is not None:
                updates.append("model_used = ?")
                params.append(model_used)
            
            params.append(session_id)
            
            await db.execute(f"""
                UPDATE sessions SET {', '.join(updates)} WHERE id = ?
            """, params)
            await db.commit()

    async def list_sessions(self, limit: int = 10) -> List[Dict]:
        """Get recent sessions for resume feature"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT id, name, created_at, last_active, message_count, 
                       first_message_preview, model_used
                FROM sessions 
                WHERE message_count > 0
                ORDER BY last_active DESC 
                LIMIT ?
            """, (limit,))
            
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    async def get_session(self, session_id: str) -> Optional[Dict]:
        """Get session details by ID"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT id, name, created_at, last_active, message_count, 
                       first_message_preview, model_used
                FROM sessions WHERE id = ?
            """, (session_id,))
            
            row = await cursor.fetchone()
            return dict(row) if row else None

    async def rename_session(self, session_id: str, name: str):
        """Rename a session"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                UPDATE sessions SET name = ?, last_active = CURRENT_TIMESTAMP 
                WHERE id = ?
            """, (name, session_id))
            await db.commit()

    async def delete_session(self, session_id: str):
        """Delete a session and its conversations"""
        async with aiosqlite.connect(self.db_path) as db:
            # Delete conversations first
            await db.execute("DELETE FROM conversations WHERE session_id = ?", (session_id,))
            # Delete protocol events
            await db.execute("DELETE FROM protocol_events WHERE session_id = ?", (session_id,))
            # Delete session
            await db.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
            await db.commit()

    async def count_sessions(self) -> int:
        """Get total count of sessions with messages"""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                SELECT COUNT(*) FROM sessions WHERE message_count > 0
            """)
            row = await cursor.fetchone()
            return row[0] if row else 0

    async def delete_all_sessions(self):
        """Delete ALL sessions and their conversations"""
        async with aiosqlite.connect(self.db_path) as db:
            # Delete all conversations
            await db.execute("DELETE FROM conversations")
            # Delete all protocol events
            await db.execute("DELETE FROM protocol_events")
            # Delete all sessions
            await db.execute("DELETE FROM sessions")
            await db.commit()

    async def get_session_conversations(self, session_id: str) -> List[Dict]:
        """Get all conversations for a session (for resume)"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute("""
                SELECT user_message, ai_response, model_used, created_at
                FROM conversations 
                WHERE session_id = ?
                ORDER BY created_at ASC
            """, (session_id,))
            
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]

    # ==================== Protocol Event Logging ====================
    # Code Pilot spec: "Persist Protocol Events (Not Meanings)"
    # Store: consent_checkpoint, rupture_logged, pattern_ticket_created,
    #        mode_changed, lens_changed, idleness_toggled, context_band_transition
    # Do NOT store: interpretations, summaries, emotional labels

    async def log_protocol_event(self, session_id: str, event_type: str,
                                  metadata: Dict = None) -> int:
        """
        Log a protocol event.

        Valid event_types:
            - consent_checkpoint
            - rupture_logged
            - pattern_ticket_created
            - mode_changed
            - lens_changed
            - idleness_toggled
            - context_band_transition

        metadata examples:
            - mode_changed: {"from": "Workshop", "to": "Sanctuary"}
            - context_band_transition: {"from": "Medium", "to": "High"}
            - idleness_toggled: {"state": true}
            - pattern_ticket_created: {"title": "...", "file": "..."}
        """
        metadata_json = json.dumps(metadata) if metadata else None

        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                INSERT INTO protocol_events (session_id, event_type, metadata)
                VALUES (?, ?, ?)
            """, (session_id, event_type, metadata_json))

            await db.commit()
            return cursor.lastrowid

    async def get_session_events(self, session_id: str,
                                  event_type: str = None,
                                  limit: int = 50) -> List[Dict]:
        """Get protocol events for a session, optionally filtered by type."""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row

            if event_type:
                cursor = await db.execute("""
                    SELECT id, event_type, metadata, created_at
                    FROM protocol_events
                    WHERE session_id = ? AND event_type = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                """, (session_id, event_type, limit))
            else:
                cursor = await db.execute("""
                    SELECT id, event_type, metadata, created_at
                    FROM protocol_events
                    WHERE session_id = ?
                    ORDER BY created_at DESC
                    LIMIT ?
                """, (session_id, limit))

            rows = await cursor.fetchall()
            results = []
            for row in rows:
                event = dict(row)
                # Parse metadata JSON
                if event.get('metadata'):
                    try:
                        event['metadata'] = json.loads(event['metadata'])
                    except json.JSONDecodeError:
                        pass
                results.append(event)
            return results

    async def get_event_counts(self, session_id: str) -> Dict[str, int]:
        """Get counts of each event type for a session (useful for session summary)."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                SELECT event_type, COUNT(*) as count
                FROM protocol_events
                WHERE session_id = ?
                GROUP BY event_type
            """, (session_id,))

            rows = await cursor.fetchall()
            return {row[0]: row[1] for row in rows}


# Global database instance
db = Database()
