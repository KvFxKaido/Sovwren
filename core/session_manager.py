"""Session Manager for Sovwren - Resume Chat Feature"""
import uuid
from datetime import datetime
from typing import List, Dict, Optional

from core.database import db


class SessionManager:
    """Manages chat session lifecycle for resume feature"""
    
    def __init__(self):
        self.current_session_id: Optional[str] = None
        self._cached_sessions: List[Dict] = []
    
    async def create_session(self, model_used: str = None) -> str:
        """Create a new session and return its ID"""
        session_id = str(uuid.uuid4())
        await db.create_session(session_id, model_used)
        self.current_session_id = session_id
        return session_id
    
    async def resume_session(self, session_id_or_number: str) -> Optional[Dict]:
        """
        Resume a previous session by ID or list number.
        Returns session info with conversation history if found.
        """
        # Check if it's a number reference
        if session_id_or_number.isdigit():
            sessions = await self.list_sessions()
            idx = int(session_id_or_number) - 1  # 1-indexed
            if 0 <= idx < len(sessions):
                session_id = sessions[idx]['id']
            else:
                return None
        else:
            session_id = session_id_or_number
        
        # Get session details
        session = await db.get_session(session_id)
        if not session:
            return None
        
        # Load conversation history
        conversations = await db.get_session_conversations(session_id)
        session['conversations'] = conversations
        
        # Update current session
        self.current_session_id = session_id
        
        return session
    
    async def list_sessions(self, limit: int = 10) -> List[Dict]:
        """Get list of recent sessions with formatted display info"""
        sessions = await db.list_sessions(limit)
        result = []
        
        for i, session in enumerate(sessions, 1):
            # Format the last_active time
            last_active = session.get('last_active', '')
            if last_active:
                try:
                    dt = datetime.fromisoformat(last_active)
                    now = datetime.now()
                    
                    if dt.date() == now.date():
                        formatted_time = f"Today {dt.strftime('%I:%M %p')}"
                    elif (now.date() - dt.date()).days == 1:
                        formatted_time = "Yesterday"
                    elif (now.date() - dt.date()).days < 7:
                        formatted_time = dt.strftime('%A')  # Day name
                    else:
                        formatted_time = dt.strftime('%b %d')
                except:
                    formatted_time = str(last_active)[:10]
            else:
                formatted_time = "Unknown"
            
            result.append({
                'number': i,
                'id': session['id'],
                'name': session.get('name') or session.get('first_message_preview') or 'Unnamed session',
                'last_active': formatted_time,
                'message_count': session.get('message_count', 0),
                'model_used': session.get('model_used', 'Unknown'),
                'preview': session.get('first_message_preview', '')[:40]
            })
        
        self._cached_sessions = result
        return result
    
    async def name_session(self, name: str, session_id: str = None):
        """Set a friendly name for a session"""
        sid = session_id or self.current_session_id
        if sid:
            await db.rename_session(sid, name)
    
    async def delete_session(self, session_id_or_number: str) -> Optional[str]:
        """
        Delete a session by ID or list number.
        Returns the name/preview of deleted session, or None if not found.
        """
        # Check if it's a number reference
        if session_id_or_number.isdigit():
            sessions = await self.list_sessions()
            idx = int(session_id_or_number) - 1
            if 0 <= idx < len(sessions):
                session = sessions[idx]
                session_id = session['id']
                session_name = session.get('name', 'Unnamed')
            else:
                return None
        else:
            session_id = session_id_or_number
            session = await db.get_session(session_id)
            if not session:
                return None
            session_name = session.get('name') or session.get('first_message_preview', 'Unnamed')
        
        await db.delete_session(session_id)
        return session_name
    
    async def update_current_session(self, message_count: int = None, 
                                     first_message: str = None,
                                     model_used: str = None):
        """Update the current session metadata"""
        if self.current_session_id:
            await db.update_session(
                self.current_session_id,
                message_count=message_count,
                first_message=first_message,
                model_used=model_used
            )
    
    def get_current_session_id(self) -> Optional[str]:
        """Get the current session ID"""
        return self.current_session_id


# Global session manager instance
session_manager = SessionManager()
