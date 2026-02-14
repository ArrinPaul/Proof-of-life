"""
In-Memory Database Service for Proof of Life Authentication System

Thread-safe in-memory store that provides the same interface used by
SessionManager and main.py. Works without any external dependencies.
For production, swap back to Convex or another persistent backend.
"""
import json
import time
import logging
import threading
from typing import List, Optional

from app.models.data_models import Session, SessionStatus, ScoringResult

logger = logging.getLogger(__name__)


class DatabaseService:
    """In-memory database service — no external dependencies required."""

    def __init__(self):
        self._lock = threading.Lock()
        self._sessions: dict = {}          # session_id -> dict
        self._verification_results: dict = {}  # session_id -> dict
        self._tokens: dict = {}            # token_id -> dict
        self._nonces: dict = {}            # nonce -> dict
        self._audit_logs: list = []        # list of dicts
        logger.info("DatabaseService initialized (in-memory store)")

    # -- Session operations --

    def create_session(self, session_id, user_id, start_time):
        """Create a new session record."""
        with self._lock:
            self._sessions[session_id] = {
                "session_id": session_id,
                "user_id": user_id,
                "start_time": start_time,
                "end_time": None,
                "status": "active",
                "failed_count": 0,
            }
        logger.info(f"Session created: {session_id}")

    def get_session(self, session_id):
        """Retrieve session by ID. Returns dict or None."""
        with self._lock:
            data = self._sessions.get(session_id)
            if data:
                return dict(data)  # return a copy
            return None

    def update_session(self, session_id, status=None, failed_count=None, end_time=None):
        """Update session fields"""
        with self._lock:
            session = self._sessions.get(session_id)
            if not session:
                return
            if status is not None:
                session["status"] = status.value if hasattr(status, "value") else status
            if failed_count is not None:
                session["failed_count"] = failed_count
            if end_time is not None:
                session["end_time"] = end_time

    # -- Verification results --

    def save_verification_result(self, result_id, session_id, scoring_result):
        """Store verification result"""
        with self._lock:
            self._verification_results[session_id] = {
                "result_id": result_id,
                "session_id": session_id,
                "liveness_score": scoring_result.liveness_score,
                "deepfake_score": scoring_result.deepfake_score,
                "emotion_score": scoring_result.emotion_score,
                "final_score": scoring_result.final_score,
                "passed": scoring_result.passed,
                "timestamp": scoring_result.timestamp,
            }

    def get_verification_result(self, session_id):
        """Retrieve verification result for a session"""
        with self._lock:
            data = self._verification_results.get(session_id)
            if data:
                return dict(data)
            return None

    # -- Token operations --

    def save_token_issuance(self, token_id, user_id, session_id, issued_at, expires_at):
        """Log token generation"""
        with self._lock:
            self._tokens[token_id] = {
                "token_id": token_id,
                "user_id": user_id,
                "session_id": session_id,
                "issued_at": issued_at,
                "expires_at": expires_at,
            }

    def get_token(self, token_id):
        """Retrieve token information"""
        with self._lock:
            data = self._tokens.get(token_id)
            if data:
                return dict(data)
            return None

    # -- Nonce operations (anti-replay) --

    def check_nonce_used(self, nonce):
        """Return True if nonce has already been used / exists"""
        with self._lock:
            return nonce in self._nonces

    def store_nonce(self, nonce, session_id, expires_at):
        """Record nonce to prevent replay"""
        with self._lock:
            self._nonces[nonce] = {
                "session_id": session_id,
                "nonce": nonce,
                "expires_at": expires_at,
            }

    def purge_expired_nonces(self):
        """Remove expired nonces. Returns count deleted."""
        now = time.time()
        with self._lock:
            expired = [k for k, v in self._nonces.items() if v["expires_at"] < now]
            for k in expired:
                del self._nonces[k]
            return len(expired)

    # -- Audit log operations --

    def save_audit_log(self, log_id, session_id, user_id, event_type, timestamp, details):
        """Store audit log entry"""
        with self._lock:
            self._audit_logs.append({
                "log_id": log_id,
                "session_id": session_id,
                "user_id": user_id,
                "event_type": event_type,
                "timestamp": timestamp,
                "details": details if isinstance(details, dict) else json.loads(details) if details else None,
            })

    def get_audit_logs(self, user_id=None, start_time=None, end_time=None, limit=100):
        """Retrieve audit records"""
        with self._lock:
            logs = list(self._audit_logs)

        if user_id:
            logs = [l for l in logs if l.get("user_id") == user_id]
        if start_time:
            logs = [l for l in logs if l["timestamp"] >= start_time]
        if end_time:
            logs = [l for l in logs if l["timestamp"] <= end_time]

        return logs[-limit:]

    def close(self):
        """No-op for in-memory store"""
        pass
