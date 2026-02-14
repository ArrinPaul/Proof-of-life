"""
Database service for Proof of Life Authentication System

Handles all database operations including session management, verification results,
token tracking, nonce storage, and audit logging.
"""
import sqlite3
import json
import time
from pathlib import Path
from typing import List, Optional
from contextlib import contextmanager

from app.models.data_models import (
    Session, SessionStatus, ScoringResult, AuditLog
)


class DatabaseService:
    """Service for managing SQLite database operations"""
    
    def __init__(self, db_path: str):
        """
        Initialize database service
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._memory_conn = None  # Store connection for :memory: databases
        self._ensure_database_exists()
    
    def _ensure_database_exists(self):
        """Create database directory and initialize schema if needed"""
        # Handle in-memory databases
        if self.db_path == ":memory:":
            self._initialize_schema()
            return
        
        db_file = Path(self.db_path)
        db_file.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize schema if database doesn't exist
        if not db_file.exists():
            self._initialize_schema()
    
    def _initialize_schema(self):
        """Initialize database schema from schema.sql"""
        schema_path = Path(__file__).parent.parent.parent / 'schema.sql'
        
        with open(schema_path, 'r') as f:
            schema_sql = f.read()
        
        with self._get_connection() as conn:
            conn.executescript(schema_sql)
            conn.commit()
    
    @contextmanager
    def _get_connection(self):
        """Context manager for database connections"""
        # For in-memory databases, reuse the same connection
        if self.db_path == ":memory:":
            if self._memory_conn is None:
                self._memory_conn = sqlite3.connect(self.db_path)
                self._memory_conn.row_factory = sqlite3.Row
            yield self._memory_conn
        else:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            try:
                yield conn
            finally:
                conn.close()
    
    # Session operations
    
    def create_session(self, session_id: str, user_id: str, start_time: float) -> None:
        """
        Create a new session record
        
        Args:
            session_id: Unique session identifier
            user_id: User identifier
            start_time: Session start timestamp
        """
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO sessions (session_id, user_id, start_time, status, failed_count)
                VALUES (?, ?, ?, ?, ?)
                """,
                (session_id, user_id, start_time, SessionStatus.ACTIVE.value, 0)
            )
            conn.commit()
    
    def get_session(self, session_id: str) -> Optional[dict]:
        """
        Retrieve session by ID
        
        Args:
            session_id: Session identifier
            
        Returns:
            Session data as dictionary or None if not found
        """
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT session_id, user_id, start_time, end_time, status, failed_count
                FROM sessions
                WHERE session_id = ?
                """,
                (session_id,)
            )
            row = cursor.fetchone()
            
            if row:
                return dict(row)
            return None
    
    def update_session(
        self,
        session_id: str,
        status: Optional[SessionStatus] = None,
        failed_count: Optional[int] = None,
        end_time: Optional[float] = None
    ) -> None:
        """
        Update session fields
        
        Args:
            session_id: Session identifier
            status: New session status
            failed_count: Updated failure count
            end_time: Session end timestamp
        """
        updates = []
        params = []
        
        if status is not None:
            updates.append("status = ?")
            params.append(status.value)
        
        if failed_count is not None:
            updates.append("failed_count = ?")
            params.append(failed_count)
        
        if end_time is not None:
            updates.append("end_time = ?")
            params.append(end_time)
        
        if not updates:
            return
        
        params.append(session_id)
        
        with self._get_connection() as conn:
            conn.execute(
                f"UPDATE sessions SET {', '.join(updates)} WHERE session_id = ?",
                params
            )
            conn.commit()
    
    # Verification results operations
    
    def save_verification_result(
        self,
        result_id: str,
        session_id: str,
        scoring_result: ScoringResult
    ) -> None:
        """
        Store verification result
        
        Args:
            result_id: Unique result identifier
            session_id: Associated session ID
            scoring_result: Scoring result data
        """
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO verification_results 
                (result_id, session_id, liveness_score, deepfake_score, 
                 emotion_score, final_score, passed, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    result_id,
                    session_id,
                    scoring_result.liveness_score,
                    scoring_result.deepfake_score,
                    scoring_result.emotion_score,
                    scoring_result.final_score,
                    scoring_result.passed,
                    scoring_result.timestamp
                )
            )
            conn.commit()
    
    def get_verification_result(self, session_id: str) -> Optional[dict]:
        """
        Retrieve verification result for a session
        
        Args:
            session_id: Session identifier
            
        Returns:
            Verification result as dictionary or None if not found
        """
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT result_id, session_id, liveness_score, deepfake_score,
                       emotion_score, final_score, passed, timestamp
                FROM verification_results
                WHERE session_id = ?
                """,
                (session_id,)
            )
            row = cursor.fetchone()
            
            if row:
                return dict(row)
            return None
    
    # Token operations
    
    def save_token_issuance(
        self,
        token_id: str,
        user_id: str,
        session_id: str,
        issued_at: float,
        expires_at: float
    ) -> None:
        """
        Log token generation
        
        Args:
            token_id: Unique token identifier
            user_id: User identifier
            session_id: Associated session ID
            issued_at: Token issuance timestamp
            expires_at: Token expiration timestamp
        """
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO tokens (token_id, user_id, session_id, issued_at, expires_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (token_id, user_id, session_id, issued_at, expires_at)
            )
            conn.commit()
    
    def get_token(self, token_id: str) -> Optional[dict]:
        """
        Retrieve token information
        
        Args:
            token_id: Token identifier
            
        Returns:
            Token data as dictionary or None if not found
        """
        with self._get_connection() as conn:
            cursor = conn.execute(
                """
                SELECT token_id, user_id, session_id, issued_at, expires_at
                FROM tokens
                WHERE token_id = ?
                """,
                (token_id,)
            )
            row = cursor.fetchone()
            
            if row:
                return dict(row)
            return None
    
    # Nonce operations (anti-replay protection)
    
    def check_nonce_used(self, nonce: str) -> bool:
        """
        Verify nonce hasn't been used
        
        Args:
            nonce: Nonce to check
            
        Returns:
            True if nonce has been used, False otherwise
        """
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT COUNT(*) as count FROM nonces WHERE nonce = ?",
                (nonce,)
            )
            row = cursor.fetchone()
            return row['count'] > 0
    
    def store_nonce(
        self,
        nonce: str,
        session_id: str,
        expires_at: float
    ) -> None:
        """
        Record nonce to prevent replay
        
        Args:
            nonce: Nonce value
            session_id: Associated session ID
            expires_at: Nonce expiration timestamp
        """
        created_at = time.time()
        
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO nonces (nonce, session_id, created_at, expires_at)
                VALUES (?, ?, ?, ?)
                """,
                (nonce, session_id, created_at, expires_at)
            )
            conn.commit()
    
    def purge_expired_nonces(self) -> int:
        """
        Remove nonces older than 24 hours
        
        Returns:
            Number of nonces deleted
        """
        current_time = time.time()
        
        with self._get_connection() as conn:
            cursor = conn.execute(
                "DELETE FROM nonces WHERE expires_at < ?",
                (current_time,)
            )
            conn.commit()
            return cursor.rowcount
    
    # Audit log operations
    
    def save_audit_log(
        self,
        log_id: str,
        session_id: str,
        user_id: str,
        event_type: str,
        timestamp: float,
        details: dict
    ) -> None:
        """
        Store audit log entry
        
        Args:
            log_id: Unique log identifier
            session_id: Associated session ID
            user_id: User identifier
            event_type: Type of event
            timestamp: Event timestamp
            details: Additional event details
        """
        details_json = json.dumps(details)
        
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO audit_logs 
                (log_id, session_id, user_id, event_type, timestamp, details)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (log_id, session_id, user_id, event_type, timestamp, details_json)
            )
            conn.commit()
    
    def get_audit_logs(
        self,
        user_id: Optional[str] = None,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
        limit: int = 100
    ) -> List[dict]:
        """
        Retrieve audit records
        
        Args:
            user_id: Filter by user ID (optional)
            start_time: Filter by start timestamp (optional)
            end_time: Filter by end timestamp (optional)
            limit: Maximum number of records to return
            
        Returns:
            List of audit log entries
        """
        query = "SELECT log_id, session_id, user_id, event_type, timestamp, details FROM audit_logs WHERE 1=1"
        params = []
        
        if user_id:
            query += " AND user_id = ?"
            params.append(user_id)
        
        if start_time:
            query += " AND timestamp >= ?"
            params.append(start_time)
        
        if end_time:
            query += " AND timestamp <= ?"
            params.append(end_time)
        
        query += " ORDER BY timestamp DESC LIMIT ?"
        params.append(limit)
        
        with self._get_connection() as conn:
            cursor = conn.execute(query, params)
            rows = cursor.fetchall()
            
            results = []
            for row in rows:
                log_dict = dict(row)
                # Parse JSON details
                if log_dict['details']:
                    log_dict['details'] = json.loads(log_dict['details'])
                results.append(log_dict)
            
            return results
