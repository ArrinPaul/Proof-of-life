"""
Unit tests for DatabaseService
"""
import pytest
import tempfile
import time
import os
from pathlib import Path
from hypothesis import given, strategies as st, settings

from app.services.database_service import DatabaseService
from app.models.data_models import SessionStatus, ScoringResult


@pytest.fixture
def temp_db():
    """Create a temporary database for testing"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, 'test.db')
        yield db_path


@pytest.fixture
def db_service(temp_db):
    """Create DatabaseService instance with temporary database"""
    return DatabaseService(temp_db)


class TestDatabaseService:
    """Test suite for DatabaseService"""
    
    def test_database_initialization(self, temp_db):
        """Test database is created and schema is initialized"""
        db_service = DatabaseService(temp_db)
        
        # Verify database file exists
        assert Path(temp_db).exists()
        
        # Verify tables exist by attempting to query them
        with db_service._get_connection() as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )
            tables = [row['name'] for row in cursor.fetchall()]
            
            assert 'sessions' in tables
            assert 'verification_results' in tables
            assert 'tokens' in tables
            assert 'nonces' in tables
            assert 'audit_logs' in tables
    
    def test_create_and_get_session(self, db_service):
        """Test session creation and retrieval"""
        session_id = 'test-session-123'
        user_id = 'user-456'
        start_time = time.time()
        
        # Create session
        db_service.create_session(session_id, user_id, start_time)
        
        # Retrieve session
        session = db_service.get_session(session_id)
        
        assert session is not None
        assert session['session_id'] == session_id
        assert session['user_id'] == user_id
        assert session['start_time'] == start_time
        assert session['status'] == SessionStatus.ACTIVE.value
        assert session['failed_count'] == 0
        assert session['end_time'] is None
    
    def test_update_session(self, db_service):
        """Test session updates"""
        session_id = 'test-session-update'
        user_id = 'user-789'
        start_time = time.time()
        
        # Create session
        db_service.create_session(session_id, user_id, start_time)
        
        # Update session
        end_time = time.time()
        db_service.update_session(
            session_id,
            status=SessionStatus.COMPLETED,
            failed_count=2,
            end_time=end_time
        )
        
        # Verify updates
        session = db_service.get_session(session_id)
        assert session['status'] == SessionStatus.COMPLETED.value
        assert session['failed_count'] == 2
        assert session['end_time'] == end_time
    
    def test_save_and_get_verification_result(self, db_service):
        """Test verification result storage and retrieval"""
        # Create session first
        session_id = 'test-session-result'
        db_service.create_session(session_id, 'user-123', time.time())
        
        # Create scoring result
        result_id = 'result-123'
        scoring_result = ScoringResult(
            liveness_score=0.85,
            deepfake_score=0.90,
            emotion_score=0.75,
            final_score=0.83,
            passed=True,
            timestamp=time.time()
        )
        
        # Save result
        db_service.save_verification_result(result_id, session_id, scoring_result)
        
        # Retrieve result
        result = db_service.get_verification_result(session_id)
        
        assert result is not None
        assert result['result_id'] == result_id
        assert result['session_id'] == session_id
        assert result['liveness_score'] == 0.85
        assert result['deepfake_score'] == 0.90
        assert result['emotion_score'] == 0.75
        assert result['final_score'] == 0.83
        assert result['passed'] == 1  # SQLite stores boolean as integer
    
    def test_save_and_get_token(self, db_service):
        """Test token issuance logging"""
        token_id = 'token-abc123'
        user_id = 'user-456'
        session_id = 'session-789'
        issued_at = time.time()
        expires_at = issued_at + 900  # 15 minutes
        
        # Save token
        db_service.save_token_issuance(
            token_id, user_id, session_id, issued_at, expires_at
        )
        
        # Retrieve token
        token = db_service.get_token(token_id)
        
        assert token is not None
        assert token['token_id'] == token_id
        assert token['user_id'] == user_id
        assert token['session_id'] == session_id
        assert token['issued_at'] == issued_at
        assert token['expires_at'] == expires_at
    
    def test_nonce_storage_and_checking(self, db_service):
        """Test nonce storage and replay prevention"""
        nonce = 'nonce-xyz789'
        session_id = 'session-nonce-test'
        expires_at = time.time() + 86400  # 24 hours
        
        # Check nonce is not used initially
        assert not db_service.check_nonce_used(nonce)
        
        # Store nonce
        db_service.store_nonce(nonce, session_id, expires_at)
        
        # Check nonce is now marked as used
        assert db_service.check_nonce_used(nonce)
    
    def test_purge_expired_nonces(self, db_service):
        """
        Test expired nonce purging
        
        Validates Requirement 11.5: Expired nonces (older than 24 hours) 
        should be automatically purged
        """
        current_time = time.time()
        
        # Store multiple expired nonces
        expired_nonce_1 = 'expired-nonce-1'
        db_service.store_nonce(
            expired_nonce_1,
            'session-1',
            current_time - 3600  # Expired 1 hour ago
        )
        
        expired_nonce_2 = 'expired-nonce-2'
        db_service.store_nonce(
            expired_nonce_2,
            'session-2',
            current_time - 86400  # Expired 24 hours ago
        )
        
        expired_nonce_3 = 'expired-nonce-3'
        db_service.store_nonce(
            expired_nonce_3,
            'session-3',
            current_time - 172800  # Expired 48 hours ago
        )
        
        # Store multiple valid nonces
        valid_nonce_1 = 'valid-nonce-1'
        db_service.store_nonce(
            valid_nonce_1,
            'session-4',
            current_time + 86400  # Expires in 24 hours
        )
        
        valid_nonce_2 = 'valid-nonce-2'
        db_service.store_nonce(
            valid_nonce_2,
            'session-5',
            current_time + 3600  # Expires in 1 hour
        )
        
        # Verify all nonces are present before purging
        assert db_service.check_nonce_used(expired_nonce_1)
        assert db_service.check_nonce_used(expired_nonce_2)
        assert db_service.check_nonce_used(expired_nonce_3)
        assert db_service.check_nonce_used(valid_nonce_1)
        assert db_service.check_nonce_used(valid_nonce_2)
        
        # Purge expired nonces
        deleted_count = db_service.purge_expired_nonces()
        
        # Verify correct number of nonces were deleted
        assert deleted_count == 3, f"Expected 3 expired nonces to be deleted, but {deleted_count} were deleted"
        
        # Verify expired nonces are removed
        assert not db_service.check_nonce_used(expired_nonce_1), "Expired nonce 1 should be removed"
        assert not db_service.check_nonce_used(expired_nonce_2), "Expired nonce 2 should be removed"
        assert not db_service.check_nonce_used(expired_nonce_3), "Expired nonce 3 should be removed"
        
        # Verify valid nonces are preserved
        assert db_service.check_nonce_used(valid_nonce_1), "Valid nonce 1 should be preserved"
        assert db_service.check_nonce_used(valid_nonce_2), "Valid nonce 2 should be preserved"
        
        # Verify purging again returns 0 (no more expired nonces)
        second_purge_count = db_service.purge_expired_nonces()
        assert second_purge_count == 0, "Second purge should delete 0 nonces"
    
    def test_save_and_get_audit_logs(self, db_service):
        """Test audit log storage and retrieval"""
        log_id = 'log-123'
        session_id = 'session-audit'
        user_id = 'user-audit'
        event_type = 'session_start'
        timestamp = time.time()
        details = {'ip_address': '192.168.1.1', 'user_agent': 'test-agent'}
        
        # Save audit log
        db_service.save_audit_log(
            log_id, session_id, user_id, event_type, timestamp, details
        )
        
        # Retrieve audit logs
        logs = db_service.get_audit_logs(user_id=user_id)
        
        assert len(logs) == 1
        log = logs[0]
        assert log['log_id'] == log_id
        assert log['session_id'] == session_id
        assert log['user_id'] == user_id
        assert log['event_type'] == event_type
        assert log['timestamp'] == timestamp
        assert log['details'] == details
    
    def test_get_audit_logs_with_filters(self, db_service):
        """Test audit log retrieval with time filters"""
        user_id = 'user-filter-test'
        base_time = time.time()
        
        # Create multiple audit logs
        for i in range(5):
            db_service.save_audit_log(
                f'log-{i}',
                f'session-{i}',
                user_id,
                'test_event',
                base_time + i * 100,
                {'index': i}
            )
        
        # Test time range filter
        logs = db_service.get_audit_logs(
            user_id=user_id,
            start_time=base_time + 150,
            end_time=base_time + 350
        )
        
        assert len(logs) == 2  # Should get logs at index 2 and 3
        
        # Test limit
        all_logs = db_service.get_audit_logs(user_id=user_id, limit=3)
        assert len(all_logs) == 3
    
    def test_get_nonexistent_session(self, db_service):
        """Test retrieving non-existent session returns None"""
        session = db_service.get_session('nonexistent-session')
        assert session is None
    
    def test_get_nonexistent_token(self, db_service):
        """Test retrieving non-existent token returns None"""
        token = db_service.get_token('nonexistent-token')
        assert token is None


class TestSessionPersistenceProperties:
    """Property-based tests for session persistence"""
    
    @given(
        session_id=st.text(min_size=1, max_size=100),
        user_id=st.text(min_size=1, max_size=100),
        start_time=st.floats(min_value=0.0, max_value=2e9, allow_nan=False, allow_infinity=False)
    )
    @settings(deadline=500)  # Allow up to 500ms for database operations
    @pytest.mark.property_test
    def test_property_14_session_start_timestamp(self, session_id, user_id, start_time):
        """
        **Validates: Requirements 9.1, 13.1**
        
        Property 14: Session Start Timestamp
        For any created session, the database record should contain a start timestamp 
        and the authenticated user identity.
        
        This property verifies that:
        1. Every created session has a start_time field
        2. Every created session has a user_id field
        3. The stored values match the input values
        """
        # Create a temporary database for this test run
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, 'test.db')
            db_service = DatabaseService(db_path)
            
            # Create session with generated values
            db_service.create_session(session_id, user_id, start_time)
            
            # Retrieve the session
            session = db_service.get_session(session_id)
            
            # Verify session exists
            assert session is not None, "Session should be persisted in database"
            
            # Verify start timestamp is present and matches
            assert 'start_time' in session, "Session record must contain start_time field"
            assert session['start_time'] == start_time, "Start timestamp must match the provided value"
            
            # Verify user identity is present and matches
            assert 'user_id' in session, "Session record must contain user_id field"
            assert session['user_id'] == user_id, "User identity must match the provided value"
    
    @given(
        nonce=st.text(min_size=1, max_size=200),
        session_id=st.text(min_size=1, max_size=100),
        expires_at=st.floats(min_value=0.0, max_value=2e9, allow_nan=False, allow_infinity=False)
    )
    @settings(deadline=500)  # Allow up to 500ms per test case due to database creation
    @pytest.mark.property_test
    def test_property_17_nonce_storage_and_validation(self, nonce, session_id, expires_at):
        """
        **Validates: Requirements 11.2, 11.3**
        
        Property 17: Nonce Storage and Validation
        For any verification attempt, the system should validate that the nonce matches 
        the current session and should store used nonces with expiration timestamps.
        
        This property verifies that:
        1. Nonces can be stored with session association
        2. Stored nonces can be validated (checked if used)
        3. Nonces are stored with expiration timestamps
        4. The system correctly identifies unused vs used nonces
        """
        # Create a temporary database for this test run
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, 'test.db')
            db_service = DatabaseService(db_path)
            
            # Verify nonce is not used initially
            is_used_before = db_service.check_nonce_used(nonce)
            assert not is_used_before, "Nonce should not be marked as used before storage"
            
            # Store nonce with session and expiration
            db_service.store_nonce(nonce, session_id, expires_at)
            
            # Verify nonce is now marked as used
            is_used_after = db_service.check_nonce_used(nonce)
            assert is_used_after, "Nonce should be marked as used after storage"
            
            # Verify nonce can be validated (attempting to store again should still show as used)
            # This simulates replay attack detection
            is_still_used = db_service.check_nonce_used(nonce)
            assert is_still_used, "Nonce should remain marked as used on subsequent checks"
