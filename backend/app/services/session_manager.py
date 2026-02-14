"""
Session Manager for Proof of Life Authentication System

Manages verification sessions including creation, timeout checking,
failure tracking, and session termination.
"""
import time
import uuid
from typing import Optional

from app.models.data_models import (
    Session, SessionStatus, Challenge, ChallengeResult
)
from app.services.database_service import DatabaseService


class SessionManager:
    """Manages verification sessions with timeout and failure tracking"""
    
    MAX_SESSION_DURATION_SECONDS = 300  # 5 minutes
    MAX_CONSECUTIVE_FAILURES = 8
    CHALLENGE_TIMEOUT_SECONDS = 10
    
    def __init__(self, database_service: DatabaseService):
        """
        Initialize session manager
        
        Args:
            database_service: Database service for persistence
        """
        self.db = database_service
    
    def create_session(self, user_id: str) -> Session:
        """
        Initialize new verification session with unique ID
        
        Args:
            user_id: Authenticated user identifier
            
        Returns:
            New Session object with unique session_id
        """
        session_id = str(uuid.uuid4())
        start_time = time.time()
        
        # Create session in database
        self.db.create_session(session_id, user_id, start_time)
        
        # Log session creation
        log_id = str(uuid.uuid4())
        self.db.save_audit_log(
            log_id=log_id,
            session_id=session_id,
            user_id=user_id,
            event_type="session_created",
            timestamp=start_time,
            details={"action": "session_created"}
        )
        
        # Return session object
        return Session(
            session_id=session_id,
            user_id=user_id,
            start_time=start_time,
            challenges=[],
            completed_challenges=[],
            failed_count=0,
            status=SessionStatus.ACTIVE
        )
    
    def update_session(
        self,
        session_id: str,
        challenge_result: ChallengeResult
    ) -> Session:
        """
        Record challenge completion and update failure count
        
        Args:
            session_id: Session identifier
            challenge_result: Result of challenge verification
            
        Returns:
            Updated Session object
        """
        # Get current session from database
        session_data = self.db.get_session(session_id)
        if not session_data:
            raise ValueError(f"Session {session_id} not found")
        
        # Update failure count if challenge failed
        failed_count = session_data['failed_count']
        if not challenge_result.completed:
            failed_count += 1
        else:
            # Reset consecutive failures on success
            failed_count = 0
        
        # Update database
        self.db.update_session(
            session_id=session_id,
            failed_count=failed_count
        )
        
        # Log challenge result
        log_id = str(uuid.uuid4())
        self.db.save_audit_log(
            log_id=log_id,
            session_id=session_id,
            user_id=session_data['user_id'],
            event_type="challenge_completed" if challenge_result.completed else "challenge_failed",
            timestamp=challenge_result.timestamp,
            details={
                "challenge_id": challenge_result.challenge_id,
                "completed": challenge_result.completed,
                "confidence": challenge_result.confidence
            }
        )
        
        # Return updated session (simplified - in real implementation would track all challenges)
        return Session(
            session_id=session_id,
            user_id=session_data['user_id'],
            start_time=session_data['start_time'],
            challenges=[],  # Would be populated from database in full implementation
            completed_challenges=[],  # Would be populated from database in full implementation
            failed_count=failed_count,
            status=SessionStatus(session_data['status'])
        )
    
    def check_timeout(self, session_id: str) -> bool:
        """
        Verify session hasn't exceeded time limits
        
        Args:
            session_id: Session identifier
            
        Returns:
            True if session has timed out, False otherwise
        """
        session_data = self.db.get_session(session_id)
        if not session_data:
            return True  # Non-existent session is considered timed out
        
        current_time = time.time()
        elapsed_time = current_time - session_data['start_time']
        
        return elapsed_time > self.MAX_SESSION_DURATION_SECONDS
    
    def check_failure_limit(self, session_id: str) -> bool:
        """
        Check if session has exceeded maximum consecutive failures
        
        Args:
            session_id: Session identifier
            
        Returns:
            True if failure limit exceeded, False otherwise
        """
        session_data = self.db.get_session(session_id)
        if not session_data:
            return True
        
        return session_data['failed_count'] >= self.MAX_CONSECUTIVE_FAILURES
    
    def terminate_session(self, session_id: str, reason: str) -> None:
        """
        End session and log termination reason
        
        Args:
            session_id: Session identifier
            reason: Reason for termination (e.g., "timeout", "max_failures", "completed")
        """
        session_data = self.db.get_session(session_id)
        if not session_data:
            return  # Session doesn't exist, nothing to terminate
        
        end_time = time.time()
        
        # Determine final status based on reason
        if reason == "timeout":
            status = SessionStatus.TIMEOUT
        elif reason in ["max_failures", "failed"]:
            status = SessionStatus.FAILED
        elif reason == "completed":
            status = SessionStatus.COMPLETED
        else:
            status = SessionStatus.FAILED
        
        # Update session in database
        self.db.update_session(
            session_id=session_id,
            status=status,
            end_time=end_time
        )
        
        # Log termination
        log_id = str(uuid.uuid4())
        self.db.save_audit_log(
            log_id=log_id,
            session_id=session_id,
            user_id=session_data['user_id'],
            event_type="session_terminated",
            timestamp=end_time,
            details={
                "reason": reason,
                "status": status.value,
                "duration": end_time - session_data['start_time']
            }
        )
