"""
Session Manager for Multi-Turn Clinical Intake & Conversational Clarification.

Maintains multi-turn conversational state, accumulates patient symptoms across
follow-up questions, and links interview history to the final triage pipeline result.
"""

from __future__ import annotations

import threading
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional


class TriageSession:
    """
    State container for a multi-turn patient triage session.
    """

    def __init__(self, session_id: Optional[str] = None, initial_input: str = ""):
        self.session_id: str = session_id or f"SES-{uuid.uuid4().hex[:8].upper()}"
        self.created_at: str = datetime.now().isoformat()
        self.updated_at: str = self.created_at
        self.history: List[Dict[str, Any]] = []
        self.accumulated_text: str = initial_input.strip()
        self.patient_state: Dict[str, Any] = {}
        self.clarification_questions: List[Dict[str, Any]] = []
        self.status: str = "INITIALIZED"  # INITIALIZED, AWAITING_CLARIFICATION, TRIAGED
        self.pipeline_result: Optional[Dict] = None

        if initial_input:
            self.add_message("user", initial_input)

    def add_message(
        self,
        role: str,
        content: str,
        metadata: Optional[Dict] = None,
    ) -> None:
        """Add a conversation turn to the session history."""
        entry = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {},
        }
        self.history.append(entry)
        self.updated_at = entry["timestamp"]

    def append_user_input(self, text: str) -> str:
        """Append user response to accumulated clinical context."""
        text = text.strip()
        if not text:
            return self.accumulated_text
        self.add_message("user", text)
        if self.accumulated_text:
            self.accumulated_text = f"{self.accumulated_text}. {text}"
        else:
            self.accumulated_text = text
        return self.accumulated_text

    def set_clarification(
        self,
        prompt: str,
        questions: List[Dict[str, Any]],
        quick_replies: Optional[List[str]] = None,
    ) -> None:
        """Record an agent clarifying turn."""
        self.status = "AWAITING_CLARIFICATION"
        self.clarification_questions = questions
        self.add_message(
            "assistant",
            prompt,
            metadata={
                "questions": questions,
                "quick_replies": quick_replies or [],
            },
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize session state for REST API or CLI transport."""
        return {
            "session_id": self.session_id,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "turn_count": len(self.history),
            "accumulated_text": self.accumulated_text,
            "history": self.history,
            "clarification_questions": self.clarification_questions,
            "patient_state": self.patient_state,
        }


class TriageSessionManager:
    """
    Thread-safe in-memory session manager for clinical interviews.
    """

    _instance = None
    _lock = threading.Lock()

    def __new__(cls) -> TriageSessionManager:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._sessions = {}
                    cls._instance._sessions_lock = threading.Lock()
        return cls._instance

    def create_session(self, initial_input: str = "") -> TriageSession:
        """Create a new conversational session."""
        session = TriageSession(initial_input=initial_input)
        with self._sessions_lock:
            self._sessions[session.session_id] = session
        return session

    def get_session(self, session_id: str) -> Optional[TriageSession]:
        """Retrieve an existing session by ID."""
        with self._sessions_lock:
            return self._sessions.get(session_id)

    def get_or_create(
        self, session_id: Optional[str] = None, initial_input: str = ""
    ) -> TriageSession:
        """Get existing session or create a new one."""
        if session_id:
            session = self.get_session(session_id)
            if session:
                return session
        return self.create_session(initial_input)

    def delete_session(self, session_id: str) -> bool:
        """Remove a session from storage."""
        with self._sessions_lock:
            if session_id in self._sessions:
                del self._sessions[session_id]
                return True
            return False

    def reset_all(self) -> None:
        """Reset all active sessions (useful for tests)."""
        with self._sessions_lock:
            self._sessions.clear()
