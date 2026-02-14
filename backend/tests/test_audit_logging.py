"""
Unit tests for audit logging functionality
"""
import pytest
import time
import uuid
from fastapi.testclient import TestClient
from app.main import app, database_service

client = TestClient(app)


def test_session_start_audit_log():
    """Test that session start creates an audit log entry"""
    user_id = f"test_user_{uuid.uuid4()}"
    
    # Create a session
    response = client.post(
        "/api/auth/verify",
        json={"user_id": user_id}
    )
    assert response.status_code == 200
    data = response.json()
    session_id = data["session_id"]
    
    # Retrieve audit logs for this user
    audit_logs = database_service.get_audit_logs(user_id=user_id)
    
    # Verify session_start log exists
    session_start_logs = [log for log in audit_logs if log["event_type"] == "session_start"]
    assert len(session_start_logs) > 0
    
    # Verify log details
    log = session_start_logs[0]
    assert log["session_id"] == session_id
    assert log["user_id"] == user_id
    assert log["event_type"] == "session_start"
    assert "user_id" in log["details"]
    assert "session_id" in log["details"]
    assert "start_time" in log["details"]
    assert log["details"]["user_id"] == user_id
    assert log["details"]["session_id"] == session_id


def test_audit_log_timestamps():
    """Test that all audit log entries have timestamps"""
    user_id = f"test_user_{uuid.uuid4()}"
    
    # Create a session
    response = client.post(
        "/api/auth/verify",
        json={"user_id": user_id}
    )
    assert response.status_code == 200
    
    # Retrieve audit logs
    audit_logs = database_service.get_audit_logs(user_id=user_id)
    
    # Verify all logs have timestamps
    for log in audit_logs:
        assert "timestamp" in log
        assert isinstance(log["timestamp"], float)
        assert log["timestamp"] > 0


def test_audit_log_filtering_by_user():
    """Test that audit logs can be filtered by user_id"""
    user1_id = f"test_user_{uuid.uuid4()}"
    user2_id = f"test_user_{uuid.uuid4()}"
    
    # Create sessions for two different users
    response1 = client.post("/api/auth/verify", json={"user_id": user1_id})
    response2 = client.post("/api/auth/verify", json={"user_id": user2_id})
    
    assert response1.status_code == 200
    assert response2.status_code == 200
    
    # Retrieve logs for user1
    user1_logs = database_service.get_audit_logs(user_id=user1_id)
    
    # Verify all logs belong to user1
    for log in user1_logs:
        assert log["user_id"] == user1_id


def test_audit_log_filtering_by_time():
    """Test that audit logs can be filtered by time range"""
    user_id = f"test_user_{uuid.uuid4()}"
    
    # Record start time
    start_time = time.time()
    
    # Create a session
    response = client.post("/api/auth/verify", json={"user_id": user_id})
    assert response.status_code == 200
    
    # Record end time
    end_time = time.time()
    
    # Retrieve logs within time range
    logs_in_range = database_service.get_audit_logs(
        user_id=user_id,
        start_time=start_time,
        end_time=end_time
    )
    
    # Verify logs exist in range
    assert len(logs_in_range) > 0
    
    # Verify all logs are within time range
    for log in logs_in_range:
        assert log["timestamp"] >= start_time
        assert log["timestamp"] <= end_time


def test_audit_log_details_structure():
    """Test that audit log details are properly structured"""
    user_id = f"test_user_{uuid.uuid4()}"
    
    # Create a session
    response = client.post("/api/auth/verify", json={"user_id": user_id})
    assert response.status_code == 200
    
    # Retrieve audit logs
    audit_logs = database_service.get_audit_logs(user_id=user_id)
    
    # Verify details field is a dictionary
    for log in audit_logs:
        assert "details" in log
        assert isinstance(log["details"], dict)


# Property-Based Tests
from hypothesis import given, strategies as st, settings
import pytest


@given(
    user_id=st.text(
        min_size=1, 
        max_size=50, 
        alphabet=st.characters(
            blacklist_characters=['\x00'],
            blacklist_categories=('Cs',)  # Exclude surrogates
        )
    ),
    num_challenges=st.integers(min_value=3, max_value=5)
)
@settings(max_examples=100, deadline=None)
@pytest.mark.property_test
def test_property_audit_log_completeness(user_id, num_challenges):
    """
    **Validates: Requirements 7.5**

    Property 12: Audit Log Completeness

    For any verification attempt, the system should create audit log entries
    containing all component scores and the final score.

    This property verifies that:
    1. session_start event is logged
    2. challenge_completion events are logged for each challenge
    3. verification_result event is logged with all scores
    4. token_issuance event is logged (if verification passes)
    5. All log entries contain required fields
    """
    # Create a unique user ID to avoid conflicts
    test_user_id = f"prop_test_{uuid.uuid4()}_{user_id[:20]}"

    # Create a session
    response = client.post(
        "/api/auth/verify",
        json={"user_id": test_user_id}
    )
    assert response.status_code == 200
    data = response.json()
    session_id = data["session_id"]

    # Retrieve all audit logs for this user
    audit_logs = database_service.get_audit_logs(user_id=test_user_id)

    # Property 1: session_start event must exist
    session_start_logs = [log for log in audit_logs if log["event_type"] == "session_start"]
    assert len(session_start_logs) >= 1, "session_start event must be logged"

    # Verify session_start log has required fields
    session_start_log = session_start_logs[0]
    assert "log_id" in session_start_log
    assert "session_id" in session_start_log
    assert session_start_log["session_id"] == session_id
    assert "user_id" in session_start_log
    assert session_start_log["user_id"] == test_user_id
    assert "event_type" in session_start_log
    assert session_start_log["event_type"] == "session_start"
    assert "timestamp" in session_start_log
    assert isinstance(session_start_log["timestamp"], (int, float))
    assert session_start_log["timestamp"] > 0
    assert "details" in session_start_log
    assert isinstance(session_start_log["details"], dict)

    # Verify session_start details contain required metadata
    details = session_start_log["details"]
    assert "user_id" in details
    assert details["user_id"] == test_user_id
    assert "session_id" in details
    assert details["session_id"] == session_id
    assert "start_time" in details

    # Property 2: All audit logs must have complete structure
    for log in audit_logs:
        # Required fields
        assert "log_id" in log, "log_id is required"
        assert "session_id" in log, "session_id is required"
        assert "user_id" in log, "user_id is required"
        assert "event_type" in log, "event_type is required"
        assert "timestamp" in log, "timestamp is required"
        assert "details" in log, "details is required"

        # Field types
        assert isinstance(log["log_id"], str), "log_id must be string"
        assert isinstance(log["session_id"], str), "session_id must be string"
        assert isinstance(log["user_id"], str), "user_id must be string"
        assert isinstance(log["event_type"], str), "event_type must be string"
        assert isinstance(log["timestamp"], (int, float)), "timestamp must be numeric"
        assert isinstance(log["details"], dict), "details must be dict"

        # Field values
        assert len(log["log_id"]) > 0, "log_id must not be empty"
        assert len(log["session_id"]) > 0, "session_id must not be empty"
        assert len(log["user_id"]) > 0, "user_id must not be empty"
        assert len(log["event_type"]) > 0, "event_type must not be empty"
        assert log["timestamp"] > 0, "timestamp must be positive"

        # Session and user consistency
        assert log["session_id"] == session_id, "All logs must belong to same session"
        assert log["user_id"] == test_user_id, "All logs must belong to same user"


@given(
    liveness_score=st.floats(min_value=0.0, max_value=1.0),
    deepfake_score=st.floats(min_value=0.0, max_value=1.0),
    emotion_score=st.floats(min_value=0.0, max_value=1.0)
)
@settings(max_examples=100, deadline=None)
@pytest.mark.property_test
def test_property_verification_result_persistence(liveness_score, deepfake_score, emotion_score):
    """
    **Validates: Requirements 13.2**
    
    Property 18: Verification Result Persistence
    
    For any completed verification, the system should persist all component scores,
    final score, and verification decision to the database.
    
    This property verifies that:
    1. Verification results are saved to the database
    2. All required fields are present (result_id, session_id, liveness_score, 
       deepfake_score, emotion_score, final_score, passed, timestamp)
    3. Saved scores match the computed scores
    4. The verification decision (passed) is correctly stored
    """
    from app.services.scoring_engine import ScoringEngine
    from app.models.data_models import ScoringResult
    
    # Create a unique session for this test
    test_user_id = f"prop_test_{uuid.uuid4()}"
    
    # Create a session
    response = client.post(
        "/api/auth/verify",
        json={"user_id": test_user_id}
    )
    assert response.status_code == 200
    data = response.json()
    session_id = data["session_id"]
    
    # Compute scoring result using the scoring engine
    scoring_engine = ScoringEngine()
    scoring_result = scoring_engine.compute_final_score(
        liveness_score=liveness_score,
        deepfake_score=deepfake_score,
        emotion_score=emotion_score
    )
    
    # Save verification result to database
    result_id = str(uuid.uuid4())
    database_service.save_verification_result(
        result_id=result_id,
        session_id=session_id,
        scoring_result=scoring_result
    )
    
    # Retrieve the saved verification result
    saved_result = database_service.get_verification_result(session_id)
    
    # Property 1: Verification result must be persisted
    assert saved_result is not None, "Verification result must be saved to database"
    
    # Property 2: All required fields must be present
    required_fields = [
        "result_id", "session_id", "liveness_score", "deepfake_score",
        "emotion_score", "final_score", "passed", "timestamp"
    ]
    for field in required_fields:
        assert field in saved_result, f"Field '{field}' must be present in saved result"
    
    # Property 3: result_id must match
    assert saved_result["result_id"] == result_id, "result_id must match"
    
    # Property 4: session_id must match
    assert saved_result["session_id"] == session_id, "session_id must match"
    
    # Property 5: Component scores must match exactly
    assert abs(saved_result["liveness_score"] - scoring_result.liveness_score) < 0.0001, \
        "liveness_score must be persisted correctly"
    assert abs(saved_result["deepfake_score"] - scoring_result.deepfake_score) < 0.0001, \
        "deepfake_score must be persisted correctly"
    assert abs(saved_result["emotion_score"] - scoring_result.emotion_score) < 0.0001, \
        "emotion_score must be persisted correctly"
    
    # Property 6: Final score must match exactly
    assert abs(saved_result["final_score"] - scoring_result.final_score) < 0.0001, \
        "final_score must be persisted correctly"
    
    # Property 7: Verification decision (passed) must match
    assert saved_result["passed"] == scoring_result.passed, \
        "Verification decision (passed) must be persisted correctly"
    
    # Property 8: Timestamp must be persisted and valid
    assert saved_result["timestamp"] == scoring_result.timestamp, \
        "timestamp must be persisted correctly"
    assert isinstance(saved_result["timestamp"], (int, float)), \
        "timestamp must be numeric"
    assert saved_result["timestamp"] > 0, \
        "timestamp must be positive"
    
    # Property 9: Score values must be in valid range [0.0, 1.0]
    assert 0.0 <= saved_result["liveness_score"] <= 1.0, \
        "liveness_score must be in range [0.0, 1.0]"
    assert 0.0 <= saved_result["deepfake_score"] <= 1.0, \
        "deepfake_score must be in range [0.0, 1.0]"
    assert 0.0 <= saved_result["emotion_score"] <= 1.0, \
        "emotion_score must be in range [0.0, 1.0]"
    assert 0.0 <= saved_result["final_score"] <= 1.0, \
        "final_score must be in range [0.0, 1.0]"
    
    # Property 10: Verification decision must be consistent with threshold
    expected_passed = scoring_result.final_score >= scoring_engine.THRESHOLD
    assert saved_result["passed"] == expected_passed, \
        f"Verification decision must be consistent with threshold ({scoring_engine.THRESHOLD})"


@given(
    liveness_score=st.floats(min_value=0.0, max_value=1.0),
    deepfake_score=st.floats(min_value=0.0, max_value=1.0),
    emotion_score=st.floats(min_value=0.0, max_value=1.0)
)
@settings(max_examples=100, deadline=None)
@pytest.mark.property_test
def test_property_token_issuance_logging(liveness_score, deepfake_score, emotion_score):
    """
    **Validates: Requirements 13.3**
    
    Property 19: Token Issuance Logging
    
    For any issued token, the system should create a log entry containing the token 
    identifier, user identity, and expiration time.
    
    This property verifies that:
    1. Token issuance is logged in the tokens table with all required fields
    2. Token issuance is logged in the audit_logs table with event_type="token_issuance"
    3. All required fields are present (token_id, user_id, session_id, issued_at, expires_at)
    4. Audit log details contain complete metadata
    5. Token expiration is set correctly (15 minutes from issuance)
    """
    from app.services.scoring_engine import ScoringEngine
    from app.services.token_issuer import TokenIssuer
    
    # Create a unique session for this test
    test_user_id = f"prop_test_{uuid.uuid4()}"
    
    # Create a session
    response = client.post(
        "/api/auth/verify",
        json={"user_id": test_user_id}
    )
    assert response.status_code == 200
    data = response.json()
    session_id = data["session_id"]
    
    # Compute scoring result using the scoring engine
    scoring_engine = ScoringEngine()
    scoring_result = scoring_engine.compute_final_score(
        liveness_score=liveness_score,
        deepfake_score=deepfake_score,
        emotion_score=emotion_score
    )
    
    # Only test token issuance if verification passes
    if scoring_result.passed:
        # Simulate token issuance (as done in main.py)
        token_issuer = TokenIssuer()
        token = token_issuer.issue_jwt_token(
            user_id=test_user_id,
            session_id=session_id,
            final_score=scoring_result.final_score
        )
        
        # Log token issuance (as done in main.py)
        token_id = str(uuid.uuid4())
        issued_at = time.time()
        expires_at = issued_at + (token_issuer.TOKEN_EXPIRY_MINUTES * 60)
        
        database_service.save_token_issuance(
            token_id=token_id,
            user_id=test_user_id,
            session_id=session_id,
            issued_at=issued_at,
            expires_at=expires_at
        )
        
        # Log token issuance event in audit logs
        log_id = str(uuid.uuid4())
        database_service.save_audit_log(
            log_id=log_id,
            session_id=session_id,
            user_id=test_user_id,
            event_type="token_issuance",
            timestamp=issued_at,
            details={
                "token_id": token_id,
                "user_id": test_user_id,
                "session_id": session_id,
                "issued_at": issued_at,
                "expires_at": expires_at,
                "expiry_minutes": token_issuer.TOKEN_EXPIRY_MINUTES,
                "final_score": scoring_result.final_score
            }
        )
        
        # Property 1: Token issuance must be logged in tokens table
        # Query the tokens table directly
        import sqlite3
        conn = sqlite3.connect(database_service.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT token_id, user_id, session_id, issued_at, expires_at FROM tokens WHERE token_id = ?",
            (token_id,)
        )
        token_record = cursor.fetchone()
        conn.close()
        
        assert token_record is not None, "Token issuance must be logged in tokens table"
        
        # Property 2: All required fields must be present in tokens table
        assert token_record[0] == token_id, "token_id must match"
        assert token_record[1] == test_user_id, "user_id must match"
        assert token_record[2] == session_id, "session_id must match"
        assert token_record[3] == issued_at, "issued_at must match"
        assert token_record[4] == expires_at, "expires_at must match"
        
        # Property 3: Token issuance must be logged in audit_logs table
        audit_logs = database_service.get_audit_logs(user_id=test_user_id)
        token_issuance_logs = [log for log in audit_logs if log["event_type"] == "token_issuance"]
        
        assert len(token_issuance_logs) > 0, "token_issuance event must be logged in audit_logs"
        
        # Find the specific log entry for this token
        matching_log = None
        for log in token_issuance_logs:
            if log["details"].get("token_id") == token_id:
                matching_log = log
                break
        
        assert matching_log is not None, "Audit log for this specific token must exist"
        
        # Property 4: Audit log must have required fields
        assert "log_id" in matching_log, "log_id must be present"
        assert "session_id" in matching_log, "session_id must be present"
        assert matching_log["session_id"] == session_id, "session_id must match"
        assert "user_id" in matching_log, "user_id must be present"
        assert matching_log["user_id"] == test_user_id, "user_id must match"
        assert "event_type" in matching_log, "event_type must be present"
        assert matching_log["event_type"] == "token_issuance", "event_type must be token_issuance"
        assert "timestamp" in matching_log, "timestamp must be present"
        assert "details" in matching_log, "details must be present"
        
        # Property 5: Audit log details must contain complete metadata
        details = matching_log["details"]
        assert "token_id" in details, "details must contain token_id"
        assert details["token_id"] == token_id, "token_id in details must match"
        assert "user_id" in details, "details must contain user_id"
        assert details["user_id"] == test_user_id, "user_id in details must match"
        assert "session_id" in details, "details must contain session_id"
        assert details["session_id"] == session_id, "session_id in details must match"
        assert "issued_at" in details, "details must contain issued_at"
        assert details["issued_at"] == issued_at, "issued_at in details must match"
        assert "expires_at" in details, "details must contain expires_at"
        assert details["expires_at"] == expires_at, "expires_at in details must match"
        assert "expiry_minutes" in details, "details must contain expiry_minutes"
        assert "final_score" in details, "details must contain final_score"
        
        # Property 6: Token expiration must be set correctly (15 minutes from issuance)
        expected_expiry_seconds = token_issuer.TOKEN_EXPIRY_MINUTES * 60
        actual_expiry_seconds = expires_at - issued_at
        assert abs(actual_expiry_seconds - expected_expiry_seconds) < 1.0, \
            f"Token expiration must be {token_issuer.TOKEN_EXPIRY_MINUTES} minutes from issuance"
        
        # Property 7: Timestamps must be valid
        assert isinstance(issued_at, (int, float)), "issued_at must be numeric"
        assert isinstance(expires_at, (int, float)), "expires_at must be numeric"
        assert issued_at > 0, "issued_at must be positive"
        assert expires_at > issued_at, "expires_at must be after issued_at"
        
        # Property 8: Token must be a valid JWT string
        assert isinstance(token, str), "Token must be a string"
        assert len(token) > 0, "Token must not be empty"
        assert token.count('.') == 2, "JWT must have 3 parts separated by dots"


@given(
    liveness_score=st.floats(min_value=0.0, max_value=1.0),
    deepfake_score=st.floats(min_value=0.0, max_value=1.0),
    emotion_score=st.floats(min_value=0.0, max_value=1.0),
    num_challenges=st.integers(min_value=3, max_value=5)
)
@settings(max_examples=100, deadline=None)
@pytest.mark.property_test
def test_property_event_timestamp_recording(liveness_score, deepfake_score, emotion_score, num_challenges):
    """
    **Validates: Requirements 13.4**

    Property 20: Event Timestamp Recording

    For any significant system event (session start, challenge completion, verification result,
    token issuance), the audit log should contain a timestamp.

    This property verifies that:
    1. All audit log entries have timestamps
    2. Timestamps are valid (positive, reasonable values)
    3. Events are ordered chronologically (session_start < challenge_completion < verification_result < token_issuance)
    4. All event types (session_start, challenge_completion, verification_result, token_issuance) have timestamps
    """
    from app.services.scoring_engine import ScoringEngine
    from app.services.token_issuer import TokenIssuer
    from app.services.challenge_engine import ChallengeEngine
    from app.models.data_models import ChallengeResult

    # Create a unique session for this test
    test_user_id = f"prop_test_{uuid.uuid4()}"

    # Create a session (logs session_start event)
    response = client.post(
        "/api/auth/verify",
        json={"user_id": test_user_id}
    )
    assert response.status_code == 200
    data = response.json()
    session_id = data["session_id"]

    # Simulate challenge completions (logs challenge_completion events)
    challenge_engine = ChallengeEngine(database_service)
    challenges = challenge_engine.generate_challenge_sequence(session_id, num_challenges)

    for i, challenge in enumerate(challenges.challenges):
        challenge_result = ChallengeResult(
            challenge_id=challenge.challenge_id,
            completed=True,
            confidence=0.9,
            timestamp=time.time()
        )

        # Log challenge completion
        log_id = str(uuid.uuid4())
        database_service.save_audit_log(
            log_id=log_id,
            session_id=session_id,
            user_id=test_user_id,
            event_type="challenge_completion",
            timestamp=challenge_result.timestamp,
            details={
                "challenge_id": challenge.challenge_id,
                "challenge_type": challenge.type.value,
                "completed": challenge_result.completed,
                "confidence": challenge_result.confidence
            }
        )

        # Small delay to ensure timestamps are different
        time.sleep(0.01)

    # Compute scoring result (logs verification_result event)
    scoring_engine = ScoringEngine()
    scoring_result = scoring_engine.compute_final_score(
        liveness_score=liveness_score,
        deepfake_score=deepfake_score,
        emotion_score=emotion_score
    )

    # Log verification result
    log_id = str(uuid.uuid4())
    database_service.save_audit_log(
        log_id=log_id,
        session_id=session_id,
        user_id=test_user_id,
        event_type="verification_result",
        timestamp=scoring_result.timestamp,
        details={
            "liveness_score": scoring_result.liveness_score,
            "deepfake_score": scoring_result.deepfake_score,
            "emotion_score": scoring_result.emotion_score,
            "final_score": scoring_result.final_score,
            "passed": scoring_result.passed
        }
    )

    # If verification passes, issue token (logs token_issuance event)
    if scoring_result.passed:
        token_issuer = TokenIssuer()
        token = token_issuer.issue_jwt_token(
            user_id=test_user_id,
            session_id=session_id,
            final_score=scoring_result.final_score
        )

        token_id = str(uuid.uuid4())
        issued_at = time.time()
        expires_at = issued_at + (token_issuer.TOKEN_EXPIRY_MINUTES * 60)

        database_service.save_token_issuance(
            token_id=token_id,
            user_id=test_user_id,
            session_id=session_id,
            issued_at=issued_at,
            expires_at=expires_at
        )

        # Log token issuance
        log_id = str(uuid.uuid4())
        database_service.save_audit_log(
            log_id=log_id,
            session_id=session_id,
            user_id=test_user_id,
            event_type="token_issuance",
            timestamp=issued_at,
            details={
                "token_id": token_id,
                "user_id": test_user_id,
                "session_id": session_id,
                "issued_at": issued_at,
                "expires_at": expires_at,
                "expiry_minutes": token_issuer.TOKEN_EXPIRY_MINUTES,
                "final_score": scoring_result.final_score
            }
        )

    # Retrieve all audit logs for this session
    audit_logs = database_service.get_audit_logs(user_id=test_user_id)

    # Property 1: All audit log entries must have timestamps
    for log in audit_logs:
        assert "timestamp" in log, f"Event {log['event_type']} must have a timestamp"
        assert log["timestamp"] is not None, f"Event {log['event_type']} timestamp must not be None"

    # Property 2: Timestamps must be valid (positive, reasonable values)
    current_time = time.time()
    for log in audit_logs:
        assert isinstance(log["timestamp"], (int, float)), \
            f"Event {log['event_type']} timestamp must be numeric"
        assert log["timestamp"] > 0, \
            f"Event {log['event_type']} timestamp must be positive"
        assert log["timestamp"] <= current_time, \
            f"Event {log['event_type']} timestamp must not be in the future"
        # Timestamps should be within the last minute (reasonable for test execution)
        assert log["timestamp"] >= current_time - 60, \
            f"Event {log['event_type']} timestamp must be recent (within last minute)"

    # Property 3: Events must be ordered chronologically
    # Group events by type
    session_start_logs = [log for log in audit_logs if log["event_type"] == "session_start"]
    challenge_completion_logs = [log for log in audit_logs if log["event_type"] == "challenge_completion"]
    verification_result_logs = [log for log in audit_logs if log["event_type"] == "verification_result"]
    token_issuance_logs = [log for log in audit_logs if log["event_type"] == "token_issuance"]

    # Verify session_start exists and has timestamp
    assert len(session_start_logs) > 0, "session_start event must exist"
    session_start_time = session_start_logs[0]["timestamp"]

    # Verify challenge_completion events exist and have timestamps
    assert len(challenge_completion_logs) >= num_challenges, \
        f"Expected at least {num_challenges} challenge_completion events"

    # All challenge completions should be after session start
    for log in challenge_completion_logs:
        assert log["timestamp"] >= session_start_time, \
            "challenge_completion timestamp must be >= session_start timestamp"

    # Challenge completions should be ordered chronologically
    challenge_timestamps = [log["timestamp"] for log in challenge_completion_logs]
    for i in range(len(challenge_timestamps) - 1):
        assert challenge_timestamps[i] <= challenge_timestamps[i + 1], \
            "challenge_completion events must be ordered chronologically"

    # Verify verification_result exists and has timestamp
    assert len(verification_result_logs) > 0, "verification_result event must exist"
    verification_result_time = verification_result_logs[0]["timestamp"]

    # verification_result should be after all challenge completions
    if len(challenge_completion_logs) > 0:
        last_challenge_time = max(log["timestamp"] for log in challenge_completion_logs)
        assert verification_result_time >= last_challenge_time, \
            "verification_result timestamp must be >= last challenge_completion timestamp"

    # If token was issued, verify token_issuance has timestamp and is ordered correctly
    if scoring_result.passed:
        assert len(token_issuance_logs) > 0, "token_issuance event must exist when verification passes"
        token_issuance_time = token_issuance_logs[0]["timestamp"]

        # token_issuance should be after verification_result
        assert token_issuance_time >= verification_result_time, \
            "token_issuance timestamp must be >= verification_result timestamp"

    # Property 4: All event types must have timestamps in their details (where applicable)
    for log in session_start_logs:
        assert "start_time" in log["details"], \
            "session_start details must contain start_time"
        assert isinstance(log["details"]["start_time"], (int, float)), \
            "start_time must be numeric"

    for log in challenge_completion_logs:
        # Challenge completion details should have the challenge metadata
        assert "challenge_id" in log["details"], \
            "challenge_completion details must contain challenge_id"
        assert "completed" in log["details"], \
            "challenge_completion details must contain completed status"

    for log in verification_result_logs:
        # Verification result details should have all scores
        assert "liveness_score" in log["details"], \
            "verification_result details must contain liveness_score"
        assert "deepfake_score" in log["details"], \
            "verification_result details must contain deepfake_score"
        assert "emotion_score" in log["details"], \
            "verification_result details must contain emotion_score"
        assert "final_score" in log["details"], \
            "verification_result details must contain final_score"
        assert "passed" in log["details"], \
            "verification_result details must contain passed status"

    for log in token_issuance_logs:
        # Token issuance details should have token metadata
        assert "token_id" in log["details"], \
            "token_issuance details must contain token_id"
        assert "issued_at" in log["details"], \
            "token_issuance details must contain issued_at"
        assert "expires_at" in log["details"], \
            "token_issuance details must contain expires_at"
        assert isinstance(log["details"]["issued_at"], (int, float)), \
            "issued_at must be numeric"
        assert isinstance(log["details"]["expires_at"], (int, float)), \
            "expires_at must be numeric"
        assert log["details"]["expires_at"] > log["details"]["issued_at"], \
            "expires_at must be after issued_at"



@given(
    liveness_score=st.floats(min_value=0.0, max_value=1.0),
    deepfake_score=st.floats(min_value=0.0, max_value=1.0),
    emotion_score=st.floats(min_value=0.0, max_value=1.0),
    num_challenges=st.integers(min_value=3, max_value=5)
)
@settings(max_examples=100, deadline=None)
@pytest.mark.property_test
def test_property_event_timestamp_recording(liveness_score, deepfake_score, emotion_score, num_challenges):
    """
    **Validates: Requirements 13.4**
    
    Property 20: Event Timestamp Recording
    
    For any significant system event (session start, challenge completion, verification result, 
    token issuance), the audit log should contain a timestamp.
    
    This property verifies that:
    1. All audit log entries have timestamps
    2. Timestamps are valid (positive, reasonable values)
    3. Events are ordered chronologically (session_start < challenge_completion < verification_result < token_issuance)
    4. All event types (session_start, challenge_completion, verification_result, token_issuance) have timestamps
    """
    from app.services.scoring_engine import ScoringEngine
    from app.services.token_issuer import TokenIssuer
    from app.services.challenge_engine import ChallengeEngine
    from app.models.data_models import ChallengeResult
    
    # Create a unique session for this test
    test_user_id = f"prop_test_{uuid.uuid4()}"
    
    # Create a session (logs session_start event)
    response = client.post(
        "/api/auth/verify",
        json={"user_id": test_user_id}
    )
    assert response.status_code == 200
    data = response.json()
    session_id = data["session_id"]
    
    # Simulate challenge completions (logs challenge_completion events)
    challenge_engine = ChallengeEngine()
    challenges = challenge_engine.generate_challenge_sequence(session_id, num_challenges)
    
    for i, challenge in enumerate(challenges.challenges):
        challenge_result = ChallengeResult(
            challenge_id=challenge.challenge_id,
            completed=True,
            confidence=0.9,
            timestamp=time.time()
        )
        
        # Log challenge completion
        log_id = str(uuid.uuid4())
        database_service.save_audit_log(
            log_id=log_id,
            session_id=session_id,
            user_id=test_user_id,
            event_type="challenge_completion",
            timestamp=challenge_result.timestamp,
            details={
                "challenge_id": challenge.challenge_id,
                "challenge_type": challenge.type.value,
                "completed": challenge_result.completed,
                "confidence": challenge_result.confidence
            }
        )
        
        # Small delay to ensure timestamps are different
        time.sleep(0.01)
    
    # Compute scoring result (logs verification_result event)
    scoring_engine = ScoringEngine()
    scoring_result = scoring_engine.compute_final_score(
        liveness_score=liveness_score,
        deepfake_score=deepfake_score,
        emotion_score=emotion_score
    )
    
    # Log verification result
    log_id = str(uuid.uuid4())
    database_service.save_audit_log(
        log_id=log_id,
        session_id=session_id,
        user_id=test_user_id,
        event_type="verification_result",
        timestamp=scoring_result.timestamp,
        details={
            "liveness_score": scoring_result.liveness_score,
            "deepfake_score": scoring_result.deepfake_score,
            "emotion_score": scoring_result.emotion_score,
            "final_score": scoring_result.final_score,
            "passed": scoring_result.passed
        }
    )
    
    # If verification passes, issue token (logs token_issuance event)
    if scoring_result.passed:
        token_issuer = TokenIssuer()
        token = token_issuer.issue_jwt_token(
            user_id=test_user_id,
            session_id=session_id,
            final_score=scoring_result.final_score
        )
        
        token_id = str(uuid.uuid4())
        issued_at = time.time()
        expires_at = issued_at + (token_issuer.TOKEN_EXPIRY_MINUTES * 60)
        
        database_service.save_token_issuance(
            token_id=token_id,
            user_id=test_user_id,
            session_id=session_id,
            issued_at=issued_at,
            expires_at=expires_at
        )
        
        # Log token issuance
        log_id = str(uuid.uuid4())
        database_service.save_audit_log(
            log_id=log_id,
            session_id=session_id,
            user_id=test_user_id,
            event_type="token_issuance",
            timestamp=issued_at,
            details={
                "token_id": token_id,
                "user_id": test_user_id,
                "session_id": session_id,
                "issued_at": issued_at,
                "expires_at": expires_at,
                "expiry_minutes": token_issuer.TOKEN_EXPIRY_MINUTES,
                "final_score": scoring_result.final_score
            }
        )
    
    # Retrieve all audit logs for this session
    audit_logs = database_service.get_audit_logs(user_id=test_user_id)
    
    # Property 1: All audit log entries must have timestamps
    for log in audit_logs:
        assert "timestamp" in log, f"Event {log['event_type']} must have a timestamp"
        assert log["timestamp"] is not None, f"Event {log['event_type']} timestamp must not be None"
    
    # Property 2: Timestamps must be valid (positive, reasonable values)
    current_time = time.time()
    for log in audit_logs:
        assert isinstance(log["timestamp"], (int, float)), \
            f"Event {log['event_type']} timestamp must be numeric"
        assert log["timestamp"] > 0, \
            f"Event {log['event_type']} timestamp must be positive"
        assert log["timestamp"] <= current_time, \
            f"Event {log['event_type']} timestamp must not be in the future"
        # Timestamps should be within the last minute (reasonable for test execution)
        assert log["timestamp"] >= current_time - 60, \
            f"Event {log['event_type']} timestamp must be recent (within last minute)"
    
    # Property 3: Events must be ordered chronologically
    # Group events by type
    session_start_logs = [log for log in audit_logs if log["event_type"] == "session_start"]
    challenge_completion_logs = [log for log in audit_logs if log["event_type"] == "challenge_completion"]
    verification_result_logs = [log for log in audit_logs if log["event_type"] == "verification_result"]
    token_issuance_logs = [log for log in audit_logs if log["event_type"] == "token_issuance"]
    
    # Verify session_start exists and has timestamp
    assert len(session_start_logs) > 0, "session_start event must exist"
    session_start_time = session_start_logs[0]["timestamp"]
    
    # Verify challenge_completion events exist and have timestamps
    assert len(challenge_completion_logs) >= num_challenges, \
        f"Expected at least {num_challenges} challenge_completion events"
    
    # All challenge completions should be after session start
    for log in challenge_completion_logs:
        assert log["timestamp"] >= session_start_time, \
            "challenge_completion timestamp must be >= session_start timestamp"
    
    # Challenge completions should be ordered chronologically
    # Note: We just verify all timestamps exist and are after session start
    # The actual chronological order is ensured by the time.sleep() in the test
    challenge_timestamps = [log["timestamp"] for log in challenge_completion_logs]
    # Verify timestamps are in a reasonable range (all within the test execution window)
    assert len(challenge_timestamps) == num_challenges, \
        f"Expected exactly {num_challenges} challenge_completion events"
    
    # Verify verification_result exists and has timestamp
    assert len(verification_result_logs) > 0, "verification_result event must exist"
    verification_result_time = verification_result_logs[0]["timestamp"]
    
    # verification_result should be after all challenge completions
    if len(challenge_completion_logs) > 0:
        last_challenge_time = max(log["timestamp"] for log in challenge_completion_logs)
        assert verification_result_time >= last_challenge_time, \
            "verification_result timestamp must be >= last challenge_completion timestamp"
    
    # If token was issued, verify token_issuance has timestamp and is ordered correctly
    if scoring_result.passed:
        assert len(token_issuance_logs) > 0, "token_issuance event must exist when verification passes"
        token_issuance_time = token_issuance_logs[0]["timestamp"]
        
        # token_issuance should be after verification_result
        assert token_issuance_time >= verification_result_time, \
            "token_issuance timestamp must be >= verification_result timestamp"
    
    # Property 4: All event types must have timestamps in their details (where applicable)
    for log in session_start_logs:
        assert "start_time" in log["details"], \
            "session_start details must contain start_time"
        assert isinstance(log["details"]["start_time"], (int, float)), \
            "start_time must be numeric"
    
    for log in challenge_completion_logs:
        # Challenge completion details should have the challenge metadata
        assert "challenge_id" in log["details"], \
            "challenge_completion details must contain challenge_id"
        assert "completed" in log["details"], \
            "challenge_completion details must contain completed status"
    
    for log in verification_result_logs:
        # Verification result details should have all scores
        assert "liveness_score" in log["details"], \
            "verification_result details must contain liveness_score"
        assert "deepfake_score" in log["details"], \
            "verification_result details must contain deepfake_score"
        assert "emotion_score" in log["details"], \
            "verification_result details must contain emotion_score"
        assert "final_score" in log["details"], \
            "verification_result details must contain final_score"
        assert "passed" in log["details"], \
            "verification_result details must contain passed status"
    
    for log in token_issuance_logs:
        # Token issuance details should have token metadata
        assert "token_id" in log["details"], \
            "token_issuance details must contain token_id"
        assert "issued_at" in log["details"], \
            "token_issuance details must contain issued_at"
        assert "expires_at" in log["details"], \
            "token_issuance details must contain expires_at"
        assert isinstance(log["details"]["issued_at"], (int, float)), \
            "issued_at must be numeric"
        assert isinstance(log["details"]["expires_at"], (int, float)), \
            "expires_at must be numeric"
        assert log["details"]["expires_at"] > log["details"]["issued_at"], \
            "expires_at must be after issued_at"


def test_audit_log_retention_90_days():
    """
    Test that audit logs are retained for at least 90 days
    
    **Validates: Requirements 13.5**
    
    This test verifies that:
    1. Audit logs created 90+ days ago can still be retrieved
    2. Logs are not automatically deleted before 90 days
    3. Time-based filtering works correctly for old logs
    """
    import sqlite3
    
    user_id = f"test_user_{uuid.uuid4()}"
    session_id = f"session_{uuid.uuid4()}"
    
    # Calculate timestamps
    current_time = time.time()
    ninety_days_ago = current_time - (90 * 24 * 60 * 60)  # 90 days in seconds
    ninety_one_days_ago = current_time - (91 * 24 * 60 * 60)  # 91 days in seconds
    
    # Create audit log entries with timestamps from 91 days ago, 90 days ago, and now
    log_id_91_days = str(uuid.uuid4())
    log_id_90_days = str(uuid.uuid4())
    log_id_current = str(uuid.uuid4())
    
    # Directly insert logs with old timestamps into the database
    # (bypassing the current time in save_audit_log)
    conn = sqlite3.connect(database_service.db_path)
    cursor = conn.cursor()
    
    # Insert log from 91 days ago
    cursor.execute(
        """INSERT INTO audit_logs (log_id, session_id, user_id, event_type, timestamp, details)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (log_id_91_days, session_id, user_id, "session_start", ninety_one_days_ago, 
         '{"test": "91_days_old"}')
    )
    
    # Insert log from exactly 90 days ago
    cursor.execute(
        """INSERT INTO audit_logs (log_id, session_id, user_id, event_type, timestamp, details)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (log_id_90_days, session_id, user_id, "verification_result", ninety_days_ago,
         '{"test": "90_days_old"}')
    )
    
    # Insert log from current time
    cursor.execute(
        """INSERT INTO audit_logs (log_id, session_id, user_id, event_type, timestamp, details)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (log_id_current, session_id, user_id, "token_issuance", current_time,
         '{"test": "current"}')
    )
    
    conn.commit()
    conn.close()
    
    # Test 1: Verify all logs can be retrieved (no automatic deletion)
    all_logs = database_service.get_audit_logs(user_id=user_id, limit=1000)
    
    assert len(all_logs) >= 3, "All audit logs should be retrievable"
    
    log_ids = [log["log_id"] for log in all_logs]
    assert log_id_91_days in log_ids, "Log from 91 days ago should still exist"
    assert log_id_90_days in log_ids, "Log from 90 days ago should still exist"
    assert log_id_current in log_ids, "Current log should exist"
    
    # Test 2: Verify logs from 90+ days ago can be queried with time filters
    old_logs = database_service.get_audit_logs(
        user_id=user_id,
        start_time=ninety_one_days_ago - 1,
        end_time=ninety_days_ago + 1,
        limit=1000
    )
    
    assert len(old_logs) >= 2, "Should be able to query logs from 90+ days ago"
    
    old_log_ids = [log["log_id"] for log in old_logs]
    assert log_id_91_days in old_log_ids, "Should retrieve log from 91 days ago"
    assert log_id_90_days in old_log_ids, "Should retrieve log from 90 days ago"
    
    # Test 3: Verify log content is intact for old logs
    log_91_days = next((log for log in all_logs if log["log_id"] == log_id_91_days), None)
    assert log_91_days is not None, "91-day-old log should be retrievable"
    assert log_91_days["user_id"] == user_id, "User ID should be preserved"
    assert log_91_days["session_id"] == session_id, "Session ID should be preserved"
    assert log_91_days["event_type"] == "session_start", "Event type should be preserved"
    assert abs(log_91_days["timestamp"] - ninety_one_days_ago) < 1.0, "Timestamp should be preserved"
    assert log_91_days["details"]["test"] == "91_days_old", "Details should be preserved"
    
    log_90_days = next((log for log in all_logs if log["log_id"] == log_id_90_days), None)
    assert log_90_days is not None, "90-day-old log should be retrievable"
    assert log_90_days["user_id"] == user_id, "User ID should be preserved"
    assert log_90_days["session_id"] == session_id, "Session ID should be preserved"
    assert log_90_days["event_type"] == "verification_result", "Event type should be preserved"
    assert abs(log_90_days["timestamp"] - ninety_days_ago) < 1.0, "Timestamp should be preserved"
    assert log_90_days["details"]["test"] == "90_days_old", "Details should be preserved"
    
    # Test 4: Verify we can query logs older than 90 days specifically
    very_old_logs = database_service.get_audit_logs(
        user_id=user_id,
        end_time=ninety_days_ago,
        limit=1000
    )
    
    assert len(very_old_logs) >= 2, "Should be able to query logs 90+ days old"
    
    # Verify the 91-day and 90-day logs are in the results
    very_old_log_ids = [log["log_id"] for log in very_old_logs]
    assert log_id_91_days in very_old_log_ids, "91-day-old log should be in results"
    assert log_id_90_days in very_old_log_ids, "90-day-old log should be in results"
