"""
Unit tests for SessionManager

Tests session creation, timeout checking, failure tracking, and termination.
"""
import pytest
import time
import tempfile
import os
from pathlib import Path
from hypothesis import given, strategies as st, settings

from app.services.database_service import DatabaseService
from app.services.session_manager import SessionManager
from app.models.data_models import ChallengeResult, SessionStatus


@pytest.fixture
def temp_db():
    """Create a temporary database for testing"""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = os.path.join(tmpdir, 'test.db')
        yield db_path


@pytest.fixture
def db_service(temp_db):
    """Create a database service with test database"""
    return DatabaseService(temp_db)


@pytest.fixture
def session_manager(db_service):
    """Create a session manager with test database"""
    return SessionManager(db_service)


class TestSessionCreation:
    """Tests for session creation"""
    
    def test_create_session_generates_unique_id(self, session_manager):
        """Test that create_session generates a unique session ID"""
        session1 = session_manager.create_session("user1")
        session2 = session_manager.create_session("user1")
        
        assert session1.session_id != session2.session_id
    
    def test_create_session_sets_user_id(self, session_manager):
        """Test that create_session associates user ID with session"""
        user_id = "test_user_123"
        session = session_manager.create_session(user_id)
        
        assert session.user_id == user_id
    
    def test_create_session_sets_start_time(self, session_manager):
        """Test that create_session records start timestamp"""
        before = time.time()
        session = session_manager.create_session("user1")
        after = time.time()
        
        assert before <= session.start_time <= after
    
    def test_create_session_initializes_status(self, session_manager):
        """Test that new session has ACTIVE status"""
        session = session_manager.create_session("user1")
        
        assert session.status == SessionStatus.ACTIVE
    
    def test_create_session_initializes_failed_count(self, session_manager):
        """Test that new session has zero failed count"""
        session = session_manager.create_session("user1")
        
        assert session.failed_count == 0
    
    def test_create_session_persists_to_database(self, session_manager, db_service):
        """Test that session is saved to database"""
        session = session_manager.create_session("user1")
        
        # Retrieve from database
        db_session = db_service.get_session(session.session_id)
        
        assert db_session is not None
        assert db_session['session_id'] == session.session_id
        assert db_session['user_id'] == "user1"
    
    def test_create_session_logs_creation(self, session_manager, db_service):
        """Test that session creation is logged"""
        session = session_manager.create_session("user1")
        
        # Check audit logs
        logs = db_service.get_audit_logs(user_id="user1")
        
        assert len(logs) > 0
        assert any(log['event_type'] == 'session_created' for log in logs)


class TestSessionUpdate:
    """Tests for session update with challenge results"""
    
    def test_update_session_increments_failure_count(self, session_manager):
        """Test that failed challenge increments failure count"""
        session = session_manager.create_session("user1")
        
        failed_result = ChallengeResult(
            challenge_id="challenge1",
            completed=False,
            confidence=0.3,
            timestamp=time.time()
        )
        
        updated_session = session_manager.update_session(session.session_id, failed_result)
        
        assert updated_session.failed_count == 1
    
    def test_update_session_resets_failure_count_on_success(self, session_manager):
        """Test that successful challenge resets consecutive failure count"""
        session = session_manager.create_session("user1")
        
        # Fail once
        failed_result = ChallengeResult(
            challenge_id="challenge1",
            completed=False,
            confidence=0.3,
            timestamp=time.time()
        )
        session_manager.update_session(session.session_id, failed_result)
        
        # Then succeed
        success_result = ChallengeResult(
            challenge_id="challenge2",
            completed=True,
            confidence=0.9,
            timestamp=time.time()
        )
        updated_session = session_manager.update_session(session.session_id, success_result)
        
        assert updated_session.failed_count == 0
    
    def test_update_session_tracks_consecutive_failures(self, session_manager):
        """Test that consecutive failures are tracked correctly"""
        session = session_manager.create_session("user1")
        
        for i in range(3):
            failed_result = ChallengeResult(
                challenge_id=f"challenge{i}",
                completed=False,
                confidence=0.3,
                timestamp=time.time()
            )
            updated_session = session_manager.update_session(session.session_id, failed_result)
        
        assert updated_session.failed_count == 3
    
    def test_update_session_logs_challenge_result(self, session_manager, db_service):
        """Test that challenge results are logged"""
        session = session_manager.create_session("user1")
        
        result = ChallengeResult(
            challenge_id="challenge1",
            completed=True,
            confidence=0.85,
            timestamp=time.time()
        )
        
        session_manager.update_session(session.session_id, result)
        
        # Check audit logs
        logs = db_service.get_audit_logs(user_id="user1")
        
        challenge_logs = [log for log in logs if 'challenge' in log['event_type']]
        assert len(challenge_logs) > 0
    
    def test_update_session_raises_on_invalid_session(self, session_manager):
        """Test that updating non-existent session raises error"""
        result = ChallengeResult(
            challenge_id="challenge1",
            completed=True,
            confidence=0.85,
            timestamp=time.time()
        )
        
        with pytest.raises(ValueError):
            session_manager.update_session("invalid_session_id", result)


class TestTimeoutChecking:
    """Tests for session timeout checking"""
    
    def test_check_timeout_returns_false_for_new_session(self, session_manager):
        """Test that new session is not timed out"""
        session = session_manager.create_session("user1")
        
        assert not session_manager.check_timeout(session.session_id)
    
    def test_check_timeout_returns_true_after_max_duration(self, session_manager, db_service):
        """Test that session times out after 2 minutes"""
        session = session_manager.create_session("user1")
        
        # Manually set start time to 3 minutes ago
        past_time = time.time() - 180  # 3 minutes ago
        db_service.update_session(session.session_id, end_time=None)
        
        # Update start time in database directly
        with db_service._get_connection() as conn:
            conn.execute(
                "UPDATE sessions SET start_time = ? WHERE session_id = ?",
                (past_time, session.session_id)
            )
            conn.commit()
        
        assert session_manager.check_timeout(session.session_id)
    
    def test_check_timeout_returns_true_for_nonexistent_session(self, session_manager):
        """Test that non-existent session is considered timed out"""
        assert session_manager.check_timeout("nonexistent_session")
    
    def test_check_timeout_boundary_at_120_seconds(self, session_manager, db_service):
        """Test timeout boundary at exactly 120 seconds"""
        session = session_manager.create_session("user1")
        
        # Set start time to exactly 120 seconds ago
        boundary_time = time.time() - 120
        
        with db_service._get_connection() as conn:
            conn.execute(
                "UPDATE sessions SET start_time = ? WHERE session_id = ?",
                (boundary_time, session.session_id)
            )
            conn.commit()
        
        # At exactly 120 seconds, should be timed out (> not >=)
        assert session_manager.check_timeout(session.session_id)


class TestFailureLimit:
    """Tests for consecutive failure limit checking"""
    
    def test_check_failure_limit_returns_false_initially(self, session_manager):
        """Test that new session has not exceeded failure limit"""
        session = session_manager.create_session("user1")
        
        assert not session_manager.check_failure_limit(session.session_id)
    
    def test_check_failure_limit_returns_true_at_three_failures(self, session_manager):
        """Test that 3 consecutive failures triggers limit"""
        session = session_manager.create_session("user1")
        
        # Fail 3 times
        for i in range(3):
            failed_result = ChallengeResult(
                challenge_id=f"challenge{i}",
                completed=False,
                confidence=0.3,
                timestamp=time.time()
            )
            session_manager.update_session(session.session_id, failed_result)
        
        assert session_manager.check_failure_limit(session.session_id)
    
    def test_check_failure_limit_returns_false_at_two_failures(self, session_manager):
        """Test that 2 failures does not trigger limit"""
        session = session_manager.create_session("user1")
        
        # Fail 2 times
        for i in range(2):
            failed_result = ChallengeResult(
                challenge_id=f"challenge{i}",
                completed=False,
                confidence=0.3,
                timestamp=time.time()
            )
            session_manager.update_session(session.session_id, failed_result)
        
        assert not session_manager.check_failure_limit(session.session_id)
    
    def test_check_failure_limit_returns_true_for_nonexistent_session(self, session_manager):
        """Test that non-existent session is considered over limit"""
        assert session_manager.check_failure_limit("nonexistent_session")


class TestSessionTimeoutScenarios:
    """
    Unit tests for session timeout scenarios
    
    Tests 2-minute session timeout enforcement and 3 consecutive failure termination.
    **Requirements: 9.4, 9.5**
    """
    
    def test_session_timeout_enforcement_at_2_minutes(self, session_manager, db_service):
        """
        Test that session is terminated after 2 minutes (120 seconds)
        
        **Validates: Requirement 9.4 - Total session duration timeout**
        """
        session = session_manager.create_session("user1")
        
        # Simulate session running for 121 seconds (just over 2 minutes)
        past_time = time.time() - 121
        
        with db_service._get_connection() as conn:
            conn.execute(
                "UPDATE sessions SET start_time = ? WHERE session_id = ?",
                (past_time, session.session_id)
            )
            conn.commit()
        
        # Check that session has timed out
        is_timed_out = session_manager.check_timeout(session.session_id)
        assert is_timed_out, "Session should be timed out after 2 minutes"
        
        # Terminate the session due to timeout
        session_manager.terminate_session(session.session_id, "timeout")
        
        # Verify session status is TIMEOUT
        db_session = db_service.get_session(session.session_id)
        assert db_session['status'] == SessionStatus.TIMEOUT.value
        assert db_session['end_time'] is not None
    
    def test_session_not_timed_out_before_2_minutes(self, session_manager, db_service):
        """
        Test that session is NOT terminated before 2 minutes
        
        **Validates: Requirement 9.4 - Session should remain active within time limit**
        """
        session = session_manager.create_session("user1")
        
        # Simulate session running for 119 seconds (just under 2 minutes)
        past_time = time.time() - 119
        
        with db_service._get_connection() as conn:
            conn.execute(
                "UPDATE sessions SET start_time = ? WHERE session_id = ?",
                (past_time, session.session_id)
            )
            conn.commit()
        
        # Check that session has NOT timed out
        is_timed_out = session_manager.check_timeout(session.session_id)
        assert not is_timed_out, "Session should NOT be timed out before 2 minutes"
    
    def test_session_timeout_at_exact_boundary(self, session_manager, db_service):
        """
        Test timeout behavior at exactly 120 seconds boundary
        
        **Validates: Requirement 9.4 - Precise timeout enforcement**
        """
        session = session_manager.create_session("user1")
        
        # Set start time to exactly 120 seconds ago
        boundary_time = time.time() - 120
        
        with db_service._get_connection() as conn:
            conn.execute(
                "UPDATE sessions SET start_time = ? WHERE session_id = ?",
                (boundary_time, session.session_id)
            )
            conn.commit()
        
        # At exactly 120 seconds, should be timed out (elapsed > MAX_DURATION)
        is_timed_out = session_manager.check_timeout(session.session_id)
        assert is_timed_out, "Session should be timed out at exactly 120 seconds"
    
    def test_three_consecutive_failures_termination(self, session_manager, db_service):
        """
        Test that session is terminated after 3 consecutive failures
        
        **Validates: Requirement 9.5 - Consecutive failure limit**
        """
        session = session_manager.create_session("user1")
        
        # Fail 3 consecutive challenges
        for i in range(3):
            failed_result = ChallengeResult(
                challenge_id=f"challenge{i}",
                completed=False,
                confidence=0.2,
                timestamp=time.time()
            )
            session_manager.update_session(session.session_id, failed_result)
        
        # Check that failure limit is exceeded
        is_over_limit = session_manager.check_failure_limit(session.session_id)
        assert is_over_limit, "Session should exceed failure limit after 3 consecutive failures"
        
        # Terminate the session due to max failures
        session_manager.terminate_session(session.session_id, "max_failures")
        
        # Verify session status is FAILED
        db_session = db_service.get_session(session.session_id)
        assert db_session['status'] == SessionStatus.FAILED.value
        assert db_session['end_time'] is not None
        
        # Verify termination was logged with correct reason
        logs = db_service.get_audit_logs(user_id="user1")
        termination_logs = [log for log in logs if log['event_type'] == 'session_terminated']
        assert len(termination_logs) > 0
        assert termination_logs[0]['details']['reason'] == 'max_failures'
    
    def test_two_consecutive_failures_not_terminated(self, session_manager):
        """
        Test that session is NOT terminated after only 2 consecutive failures
        
        **Validates: Requirement 9.5 - Failure limit is exactly 3**
        """
        session = session_manager.create_session("user1")
        
        # Fail 2 consecutive challenges
        for i in range(2):
            failed_result = ChallengeResult(
                challenge_id=f"challenge{i}",
                completed=False,
                confidence=0.2,
                timestamp=time.time()
            )
            session_manager.update_session(session.session_id, failed_result)
        
        # Check that failure limit is NOT exceeded
        is_over_limit = session_manager.check_failure_limit(session.session_id)
        assert not is_over_limit, "Session should NOT exceed failure limit with only 2 failures"
    
    def test_consecutive_failures_reset_on_success(self, session_manager):
        """
        Test that consecutive failure count resets after a successful challenge
        
        **Validates: Requirement 9.5 - Consecutive failures (not total failures)**
        """
        session = session_manager.create_session("user1")
        
        # Fail 2 times
        for i in range(2):
            failed_result = ChallengeResult(
                challenge_id=f"challenge{i}",
                completed=False,
                confidence=0.2,
                timestamp=time.time()
            )
            session_manager.update_session(session.session_id, failed_result)
        
        # Then succeed once
        success_result = ChallengeResult(
            challenge_id="challenge_success",
            completed=True,
            confidence=0.9,
            timestamp=time.time()
        )
        updated_session = session_manager.update_session(session.session_id, success_result)
        
        # Failure count should be reset to 0
        assert updated_session.failed_count == 0, "Consecutive failures should reset after success"
        
        # Now fail 2 more times (total 4 failures, but only 2 consecutive)
        for i in range(2):
            failed_result = ChallengeResult(
                challenge_id=f"challenge_after{i}",
                completed=False,
                confidence=0.2,
                timestamp=time.time()
            )
            session_manager.update_session(session.session_id, failed_result)
        
        # Should NOT exceed limit (only 2 consecutive failures)
        is_over_limit = session_manager.check_failure_limit(session.session_id)
        assert not is_over_limit, "Should not exceed limit with 2 consecutive failures after reset"
    
    def test_timeout_and_failure_combined_scenario(self, session_manager, db_service):
        """
        Test scenario where both timeout and failure conditions could apply
        
        **Validates: Requirements 9.4, 9.5 - Multiple termination conditions**
        """
        session = session_manager.create_session("user1")
        
        # Fail 2 challenges
        for i in range(2):
            failed_result = ChallengeResult(
                challenge_id=f"challenge{i}",
                completed=False,
                confidence=0.2,
                timestamp=time.time()
            )
            session_manager.update_session(session.session_id, failed_result)
        
        # Simulate time passing (over 2 minutes)
        past_time = time.time() - 125
        with db_service._get_connection() as conn:
            conn.execute(
                "UPDATE sessions SET start_time = ? WHERE session_id = ?",
                (past_time, session.session_id)
            )
            conn.commit()
        
        # Both conditions should be checkable
        is_timed_out = session_manager.check_timeout(session.session_id)
        is_over_limit = session_manager.check_failure_limit(session.session_id)
        
        assert is_timed_out, "Session should be timed out"
        assert not is_over_limit, "Session should not be over failure limit (only 2 failures)"
        
        # Timeout takes precedence in this scenario
        session_manager.terminate_session(session.session_id, "timeout")
        
        db_session = db_service.get_session(session.session_id)
        assert db_session['status'] == SessionStatus.TIMEOUT.value


class TestSessionTermination:
    """Tests for session termination"""
    
    def test_terminate_session_updates_status_for_timeout(self, session_manager, db_service):
        """Test that timeout termination sets TIMEOUT status"""
        session = session_manager.create_session("user1")
        
        session_manager.terminate_session(session.session_id, "timeout")
        
        db_session = db_service.get_session(session.session_id)
        assert db_session['status'] == SessionStatus.TIMEOUT.value
    
    def test_terminate_session_updates_status_for_max_failures(self, session_manager, db_service):
        """Test that max_failures termination sets FAILED status"""
        session = session_manager.create_session("user1")
        
        session_manager.terminate_session(session.session_id, "max_failures")
        
        db_session = db_service.get_session(session.session_id)
        assert db_session['status'] == SessionStatus.FAILED.value
    
    def test_terminate_session_updates_status_for_completed(self, session_manager, db_service):
        """Test that completed termination sets COMPLETED status"""
        session = session_manager.create_session("user1")
        
        session_manager.terminate_session(session.session_id, "completed")
        
        db_session = db_service.get_session(session.session_id)
        assert db_session['status'] == SessionStatus.COMPLETED.value
    
    def test_terminate_session_sets_end_time(self, session_manager, db_service):
        """Test that termination records end timestamp"""
        session = session_manager.create_session("user1")
        
        before = time.time()
        session_manager.terminate_session(session.session_id, "completed")
        after = time.time()
        
        db_session = db_service.get_session(session.session_id)
        assert db_session['end_time'] is not None
        assert before <= db_session['end_time'] <= after
    
    def test_terminate_session_logs_termination(self, session_manager, db_service):
        """Test that termination is logged with reason"""
        session = session_manager.create_session("user1")
        
        session_manager.terminate_session(session.session_id, "timeout")
        
        # Check audit logs
        logs = db_service.get_audit_logs(user_id="user1")
        
        termination_logs = [log for log in logs if log['event_type'] == 'session_terminated']
        assert len(termination_logs) > 0
        assert termination_logs[0]['details']['reason'] == 'timeout'
    
    def test_terminate_session_handles_nonexistent_session(self, session_manager):
        """Test that terminating non-existent session doesn't raise error"""
        # Should not raise exception
        session_manager.terminate_session("nonexistent_session", "timeout")
    
    def test_terminate_session_logs_duration(self, session_manager, db_service):
        """Test that termination logs session duration"""
        session = session_manager.create_session("user1")
        
        # Wait a bit
        time.sleep(0.1)
        
        session_manager.terminate_session(session.session_id, "completed")
        
        # Check audit logs
        logs = db_service.get_audit_logs(user_id="user1")
        
        termination_logs = [log for log in logs if log['event_type'] == 'session_terminated']
        assert len(termination_logs) > 0
        assert 'duration' in termination_logs[0]['details']
        assert termination_logs[0]['details']['duration'] > 0



# ============================================================================
# Property-Based Tests
# ============================================================================

class TestPropertyUniqueSessionGeneration:
    """
    Property-Based Tests for Session Generation
    
    **Validates: Requirements 1.2**
    """
    
    @given(
        user_ids=st.lists(
            st.text(
                min_size=1, 
                max_size=50,
                alphabet=st.characters(
                    blacklist_categories=('Cs',),  # Exclude surrogate characters
                    blacklist_characters=['\x00']  # Exclude null bytes
                )
            ),
            min_size=2,
            max_size=100
        )
    )
    @settings(deadline=None)  # Disable deadline for database operations
    @pytest.mark.property_test
    def test_property_unique_session_generation(self, user_ids):
        """
        Property 1: Unique Session Generation
        
        For any successful authentication, the system should generate a unique 
        session identifier that differs from all other active session identifiers.
        
        **Validates: Requirements 1.2**
        """
        # Create temporary database for this test run
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, 'test.db')
            db_service = DatabaseService(db_path)
            session_manager = SessionManager(db_service)
            
            # Generate sessions for all user IDs
            session_ids = set()
            sessions = []
            
            for user_id in user_ids:
                session = session_manager.create_session(user_id)
                sessions.append(session)
                
                # Property: Each session ID must be unique
                assert session.session_id not in session_ids, \
                    f"Duplicate session ID generated: {session.session_id}"
                
                session_ids.add(session.session_id)
            
            # Additional verification: All session IDs should be distinct
            assert len(session_ids) == len(user_ids), \
                "Number of unique session IDs does not match number of sessions created"
            
            # Verify each session is properly associated with its user
            for session, user_id in zip(sessions, user_ids):
                assert session.user_id == user_id, \
                    f"Session {session.session_id} not properly associated with user {user_id}"
                
                # Verify session exists in database
                db_session = db_service.get_session(session.session_id)
                assert db_session is not None, \
                    f"Session {session.session_id} not found in database"
                assert db_session['user_id'] == user_id, \
                    f"Database session user_id mismatch for session {session.session_id}"
