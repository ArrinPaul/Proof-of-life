"""
Convex Database Service for Proof of Life Authentication System

Synchronous Convex HTTP API client that matches the same interface as the
original SQLite DatabaseService, so SessionManager and main.py can call
it without changes.
"""
import os
import httpx
import json
import time
import logging
from typing import List, Optional

from app.models.data_models import Session, SessionStatus, ScoringResult

logger = logging.getLogger(__name__)


class DatabaseService:
    """Service for managing Convex database operations (synchronous)"""

    def __init__(self):
        """Initialize Convex database service with sync HTTP client"""
        self.deployment_url = os.getenv(
            "CONVEX_URL", "https://keen-lion-797.convex.cloud"
        )
        self.client = httpx.Client(timeout=30.0)

    # -- Convex HTTP helpers --

    def _mutation(self, function_name, args):
        """Execute a Convex mutation (sync)"""
        url = f"{self.deployment_url}/api/mutation"
        payload = {"path": function_name, "args": args}
        try:
            response = self.client.post(url, json=payload)
            response.raise_for_status()
            result = response.json()
            return result.get("value")
        except Exception as e:
            logger.error(f"Convex mutation {function_name} failed: {e}")
            raise

    def _query(self, function_name, args):
        """Execute a Convex query (sync)"""
        url = f"{self.deployment_url}/api/query"
        payload = {"path": function_name, "args": args}
        try:
            response = self.client.post(url, json=payload)
            response.raise_for_status()
            result = response.json()
            return result.get("value")
        except Exception as e:
            logger.error(f"Convex query {function_name} failed: {e}")
            raise

    # -- Session operations --

    def create_session(self, session_id, user_id, start_time):
        """Create a new session record."""
        self._mutation(
            "sessions:create",
            {
                "session_id": session_id,
                "user_id": user_id,
                "start_time": start_time * 1000,
            },
        )

    def get_session(self, session_id):
        """Retrieve session by ID. Returns dict or None."""
        try:
            data = self._query("sessions:getBySessionId", {"session_id": session_id})
            if not data:
                return None
            return {
                "session_id": data.get("session_id", data.get("_id")),
                "user_id": data["user_id"],
                "start_time": data["start_time"] / 1000,
                "end_time": (data["end_time"] / 1000) if data.get("end_time") else None,
                "status": data["status"],
                "failed_count": data["failed_count"],
            }
        except Exception:
            return None

    def update_session(self, session_id, status=None, failed_count=None, end_time=None):
        """Update session fields"""
        args = {"session_id": session_id}
        if status is not None:
            args["status"] = status.value if hasattr(status, "value") else status
        if failed_count is not None:
            args["failed_count"] = failed_count
        if end_time is not None:
            args["end_time"] = end_time * 1000
        self._mutation("sessions:updateBySessionId", args)

    # -- Verification results --

    def save_verification_result(self, result_id, session_id, scoring_result):
        """Store verification result"""
        self._mutation(
            "verification_results:save",
            {
                "result_id": result_id,
                "session_id": session_id,
                "liveness_score": scoring_result.liveness_score,
                "deepfake_score": scoring_result.deepfake_score,
                "emotion_score": scoring_result.emotion_score,
                "final_score": scoring_result.final_score,
                "passed": scoring_result.passed,
                "timestamp": scoring_result.timestamp * 1000,
            },
        )

    def get_verification_result(self, session_id):
        """Retrieve verification result for a session"""
        try:
            data = self._query(
                "verification_results:getBySession", {"session_id": session_id}
            )
            if not data:
                return None
            return {
                "session_id": data["session_id"],
                "liveness_score": data["liveness_score"],
                "deepfake_score": data["deepfake_score"],
                "emotion_score": data["emotion_score"],
                "final_score": data["final_score"],
                "passed": data["passed"],
                "timestamp": data["timestamp"] / 1000,
            }
        except Exception:
            return None

    # -- Token operations --

    def save_token_issuance(self, token_id, user_id, session_id, issued_at, expires_at):
        """Log token generation"""
        self._mutation(
            "tokens:store",
            {
                "token_id": token_id,
                "user_id": user_id,
                "session_id": session_id,
                "token": token_id,
                "issued_at": issued_at * 1000,
                "expires_at": expires_at * 1000,
            },
        )

    def get_token(self, token_id):
        """Retrieve token information"""
        try:
            data = self._query("tokens:get", {"token": token_id})
            if not data:
                return None
            return {
                "token_id": data.get("token_id", data.get("token")),
                "user_id": data.get("user_id"),
                "session_id": data["session_id"],
                "issued_at": data["issued_at"] / 1000,
                "expires_at": data["expires_at"] / 1000,
            }
        except Exception:
            return None

    # -- Nonce operations (anti-replay) --

    def check_nonce_used(self, nonce):
        """Return True if nonce has already been used / exists"""
        try:
            result = self._query("nonces:exists", {"nonce": nonce})
            return bool(result)
        except Exception:
            return False

    def store_nonce(self, nonce, session_id, expires_at):
        """Record nonce to prevent replay"""
        self._mutation(
            "nonces:store",
            {
                "session_id": session_id,
                "nonce": nonce,
                "expires_at": expires_at * 1000,
            },
        )

    def purge_expired_nonces(self):
        """Remove expired nonces. Returns count deleted."""
        try:
            result = self._mutation("nonces:purgeExpired", {})
            return result or 0
        except Exception:
            return 0

    # -- Audit log operations --

    def save_audit_log(self, log_id, session_id, user_id, event_type, timestamp, details):
        """Store audit log entry"""
        self._mutation(
            "audit_logs:log",
            {
                "log_id": log_id,
                "session_id": session_id,
                "user_id": user_id,
                "event_type": event_type,
                "timestamp": timestamp * 1000,
                "details": json.dumps(details),
            },
        )

    def get_audit_logs(self, user_id=None, start_time=None, end_time=None, limit=100):
        """Retrieve audit records"""
        try:
            if user_id:
                logs = self._query("audit_logs:getByUser", {"user_id": user_id})
            else:
                logs = self._query("audit_logs:getRecent", {"limit": limit})

            results = []
            for log in logs or []:
                entry = {
                    "log_id": log.get("log_id", log.get("_id")),
                    "session_id": log.get("session_id"),
                    "user_id": log.get("user_id"),
                    "event_type": log["event_type"],
                    "timestamp": log["timestamp"] / 1000,
                    "details": json.loads(log["details"]) if log.get("details") else None,
                }
                results.append(entry)

            if start_time or end_time:
                results = [
                    r
                    for r in results
                    if (not start_time or r["timestamp"] >= start_time)
                    and (not end_time or r["timestamp"] <= end_time)
                ]
            return results
        except Exception:
            return []

    def close(self):
        """Close the HTTP client"""
        self.client.close()
