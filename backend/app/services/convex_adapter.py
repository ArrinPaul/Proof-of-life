"""
Convex Database Adapter

This adapter provides a bridge between the existing database service
and Convex backend. It maintains the same interface while using Convex
for data storage instead of SQLite.
"""

import os
import httpx
from typing import Optional, Dict, Any, List
from datetime import datetime


class ConvexAdapter:
    """Adapter for Convex database operations"""
    
    def __init__(self):
        self.deployment_url = os.getenv("CONVEX_URL", "")
        self.client = httpx.AsyncClient(base_url=self.deployment_url)
    
    async def _mutation(self, function_name: str, args: Dict[str, Any]) -> Any:
        """Execute a Convex mutation"""
        response = await self.client.post(
            f"/api/mutation/{function_name}",
            json={"args": args}
        )
        response.raise_for_status()
        return response.json()
    
    async def _query(self, function_name: str, args: Dict[str, Any]) -> Any:
        """Execute a Convex query"""
        response = await self.client.post(
            f"/api/query/{function_name}",
            json={"args": args}
        )
        response.raise_for_status()
        return response.json()
    
    # Session operations
    async def create_session(self, user_id: str) -> str:
        """Create a new session"""
        result = await self._mutation("sessions:create", {"user_id": user_id})
        return result
    
    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get session by ID"""
        try:
            result = await self._query("sessions:get", {"id": session_id})
            return result
        except:
            return None
    
    async def update_session(
        self,
        session_id: str,
        status: Optional[str] = None,
        failed_count: Optional[int] = None,
        end_time: Optional[float] = None
    ):
        """Update session"""
        args = {"id": session_id}
        if status is not None:
            args["status"] = status
        if failed_count is not None:
            args["failed_count"] = failed_count
        if end_time is not None:
            args["end_time"] = end_time
        
        await self._mutation("sessions:update", args)
    
    async def check_timeout(self, session_id: str) -> bool:
        """Check if session has timed out"""
        result = await self._query("sessions:checkTimeout", {"id": session_id})
        return result
    
    async def terminate_session(self, session_id: str, reason: str):
        """Terminate a session"""
        await self._mutation("sessions:terminate", {
            "id": session_id,
            "reason": reason
        })
    
    # Nonce operations
    async def store_nonce(
        self,
        session_id: str,
        nonce: str,
        expires_at: float
    ):
        """Store a nonce"""
        await self._mutation("nonces:store", {
            "session_id": session_id,
            "nonce": nonce,
            "expires_at": expires_at
        })
    
    async def validate_nonce(self, session_id: str, nonce: str) -> bool:
        """Validate a nonce"""
        result = await self._query("nonces:validate", {
            "session_id": session_id,
            "nonce": nonce
        })
        return result
    
    async def mark_nonce_used(self, nonce: str):
        """Mark nonce as used"""
        await self._mutation("nonces:markUsed", {"nonce": nonce})
    
    async def purge_expired_nonces(self) -> int:
        """Purge expired nonces"""
        result = await self._mutation("nonces:purgeExpired", {})
        return result
    
    # Token operations
    async def store_token(
        self,
        session_id: str,
        token: str,
        issued_at: float,
        expires_at: float
    ):
        """Store a token"""
        await self._mutation("tokens:store", {
            "session_id": session_id,
            "token": token,
            "issued_at": issued_at,
            "expires_at": expires_at
        })
    
    async def get_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Get token by value"""
        try:
            result = await self._query("tokens:get", {"token": token})
            return result
        except:
            return None
    
    async def get_token_by_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get token by session ID"""
        try:
            result = await self._query("tokens:getBySession", {"session_id": session_id})
            return result
        except:
            return None
    
    # Verification results
    async def save_verification_result(
        self,
        session_id: str,
        liveness_score: float,
        emotion_score: float,
        deepfake_score: float,
        final_score: float,
        passed: bool
    ):
        """Save verification result"""
        await self._mutation("verification_results:save", {
            "session_id": session_id,
            "liveness_score": liveness_score,
            "emotion_score": emotion_score,
            "deepfake_score": deepfake_score,
            "final_score": final_score,
            "passed": passed
        })
    
    async def get_verification_result(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get verification result by session ID"""
        try:
            result = await self._query("verification_results:getBySession", {
                "session_id": session_id
            })
            return result
        except:
            return None
    
    # Audit logs
    async def log_audit_event(
        self,
        event_type: str,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        details: Optional[str] = None
    ):
        """Log an audit event"""
        args = {"event_type": event_type}
        if session_id:
            args["session_id"] = session_id
        if user_id:
            args["user_id"] = user_id
        if details:
            args["details"] = details
        
        await self._mutation("audit_logs:log", args)
    
    async def get_audit_logs_by_session(self, session_id: str) -> List[Dict[str, Any]]:
        """Get audit logs for a session"""
        result = await self._query("audit_logs:getBySession", {"session_id": session_id})
        return result or []
    
    async def get_audit_logs_by_user(self, user_id: str) -> List[Dict[str, Any]]:
        """Get audit logs for a user"""
        result = await self._query("audit_logs:getByUser", {"user_id": user_id})
        return result or []
    
    async def get_recent_audit_logs(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent audit logs"""
        result = await self._query("audit_logs:getRecent", {"limit": limit})
        return result or []
    
    async def purge_old_audit_logs(self, days: int = 90) -> int:
        """Purge old audit logs"""
        result = await self._mutation("audit_logs:purgeOld", {"days": days})
        return result
    
    async def close(self):
        """Close the client"""
        await self.client.aclose()
