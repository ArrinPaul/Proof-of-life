"""
Convex Database Service for Proof of Life Authentication System

This replaces the SQLite database service with Convex backend.
"""
import os
import httpx
import json
from typing import List, Optional
from app.models.data_models import Session, SessionStatus, ScoringResult, AuditLog


class DatabaseService:
    """Service for managing Convex database operations"""
    
    def __init__(self):
        """Initialize Convex database service"""
        self.deployment_url = os.getenv("CONVEX_URL", "https://keen-lion-797.convex.cloud")
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def _mutation(self, function_name: str, args: dict) -> any:
        """Execute a Convex mutation"""
        url = f"{self.deployment_url}/api/mutation"
        payload = {
            "path": function_name,
            "args": [args] if args else []
        }
        response = await self.client.post(url, json=payload)
        response.raise_for_status()
        result = response.json()
        return result.get("value")
    
    async def _query(self, function_name: str, args: dict) -> any:
        """Execute a Convex query"""
        url = f"{self.deployment_url}/api/query"
        payload = {
            "path": function_name,
            "args": [args] if args else []
        }
        response = await self.client.post(url, json=payload)
        response.raise_for_status()
        result = response.json()
        return result.get("value")
    
    # Session operations
    async def create_session(self, user_id: str) -> str:
        """Create a new session"""
        session_id = await self._mutation("sessions:create", {"user_id": user_id})
        return session_id
    
    async def get_session(self, session_id: str) -> Optional[Session]:
        """Get session by ID"""
        try:
            data = await self._query("sessions:get", {"id": session_id})
            if not data:
                return None
            return Session(
                session_id=data["_id"],
                user_id=data["user_id"],
                status=SessionStatus(data["status"]),
                start_time=data["start_time"],
                end_time=data.get("end_time"),
                failed_count=data["failed_count"]
            )
        except:
            return None
    
    async def update_session(
        self,
        session_id: str,
        status: Optional[SessionStatus] = None,
        failed_count: Optional[int] = None,
        end_time: Optional[float] = None
    ):
        """Update session"""
        args = {"id": session_id}
        if status:
            args["status"] = status.value
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
    async def store_nonce(self, session_id: str, nonce: str, expiry_seconds: int = 300):
        """Store a nonce"""
        import time
        expires_at = (time.time() + expiry_seconds) * 1000  # Convert to ms
        await self._mutation("nonces:store", {
            "session_id": session_id,
            "nonce": nonce,
            "expires_at": expires_at
        })
    
    async def check_nonce(self, session_id: str, nonce: str) -> bool:
        """Check if nonce is valid"""
        result = await self._query("nonces:validate", {
            "session_id": session_id,
            "nonce": nonce
        })
        if result:
            # Mark as used
            await self._mutation("nonces:markUsed", {"nonce": nonce})
        return result
    
    async def purge_expired_nonces(self) -> int:
        """Purge expired nonces"""
        result = await self._mutation("nonces:purgeExpired", {})
        return result
    
    # Token operations
    async def save_token(
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
            "issued_at": issued_at * 1000,  # Convert to ms
            "expires_at": expires_at * 1000
        })
    
    async def get_token(self, token: str) -> Optional[dict]:
        """Get token by value"""
        try:
            result = await self._query("tokens:get", {"token": token})
            return result
        except:
            return None
    
    # Verification results
    async def save_verification_result(self, result: ScoringResult):
        """Save verification result"""
        await self._mutation("verification_results:save", {
            "session_id": result.session_id,
            "liveness_score": result.liveness_score,
            "emotion_score": result.emotion_score,
            "deepfake_score": result.deepfake_score,
            "final_score": result.final_score,
            "passed": result.passed
        })
    
    async def get_verification_result(self, session_id: str) -> Optional[ScoringResult]:
        """Get verification result by session ID"""
        try:
            data = await self._query("verification_results:getBySession", {
                "session_id": session_id
            })
            if not data:
                return None
            return ScoringResult(
                session_id=data["session_id"],
                liveness_score=data["liveness_score"],
                emotion_score=data["emotion_score"],
                deepfake_score=data["deepfake_score"],
                final_score=data["final_score"],
                passed=data["passed"],
                timestamp=data["timestamp"] / 1000  # Convert from ms
            )
        except:
            return None
    
    # Audit logs
    async def save_audit_log(self, log: AuditLog):
        """Log an audit event"""
        args = {
            "event_type": log.event_type,
        }
        if log.session_id:
            args["session_id"] = log.session_id
        if log.user_id:
            args["user_id"] = log.user_id
        if log.details:
            args["details"] = json.dumps(log.details)
        
        await self._mutation("audit_logs:log", args)
    
    async def get_audit_logs(
        self,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None
    ) -> List[AuditLog]:
        """Get audit logs with filters"""
        if session_id:
            logs = await self._query("audit_logs:getBySession", {"session_id": session_id})
        elif user_id:
            logs = await self._query("audit_logs:getByUser", {"user_id": user_id})
        else:
            logs = await self._query("audit_logs:getRecent", {"limit": 100})
        
        result = []
        for log in logs or []:
            result.append(AuditLog(
                session_id=log.get("session_id"),
                user_id=log.get("user_id"),
                event_type=log["event_type"],
                timestamp=log["timestamp"] / 1000,  # Convert from ms
                details=json.loads(log["details"]) if log.get("details") else None
            ))
        
        # Filter by time if specified
        if start_time or end_time:
            result = [
                log for log in result
                if (not start_time or log.timestamp >= start_time) and
                   (not end_time or log.timestamp <= end_time)
            ]
        
        return result
    
    async def purge_old_audit_logs(self, days: int = 90) -> int:
        """Purge old audit logs"""
        result = await self._mutation("audit_logs:purgeOld", {"days": days})
        return result
    
    async def close(self):
        """Close the client"""
        await self.client.aclose()
