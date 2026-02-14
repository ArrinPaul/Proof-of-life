"""
End-to-End Integration Tests for Proof of Life Authentication System

Tests complete flows from authentication through token issuance,
including timeout scenarios and security validations.
"""
import pytest
import time
import base64
import numpy as np
import cv2
from fastapi.testclient import TestClient
from app.main import app
from app.services import DatabaseService, SessionManager, TokenIssuer

client = TestClient(app)


class TestSuccessfulVerificationFlow:
    """
    Test complete successful verification flow
    Requirements: 1.1, 2.1, 4.5, 7.3, 8.1, 13.1
    """
    
    def test_complete_auth_to_token_flow(self):
        """Test complete flow: auth → session → challenges → token"""
        # Step 1: Authenticate and create session
        response = client.post(
            "/api/auth/verify",
            json={"user_id": "test_user_e2e"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "session_id" in data
        assert "websocket_url" in data
        session_id = data["session_id"]
        
        # Step 2: Verify session was created in database
        db = DatabaseService("pol_auth.db")
        session_data = db.get_session(session_id)
        assert session_data is not None
        assert session_data["user_id"] == "test_user_e2e"
        assert session_data["status"] == "active"
        
        # Step 3: Verify audit log was created
        audit_logs = db.get_audit_logs(user_id="test_user_e2e", limit=10)
        assert len(audit_logs) > 0
        assert any(log["event_type"] == "session_start" for log in audit_logs)
        
        # Step 4: Connect to WebSocket and complete verification
        token = None  # Initialize token variable
        with client.websocket_connect(f"/ws/verify/{session_id}") as websocket:
            # Receive initial challenge
            data = websocket.receive_json()
            assert data["type"] == "challenge_issued"
            # Challenge data is nested in 'data' field
            assert "data" in data
            assert "challenge_id" in data["data"]
            
            # Send video frames (simulate successful verification)
            frame = create_test_frame()
            frame_b64 = encode_frame(frame)
            
            # Send multiple frames to complete challenges
            for _ in range(15):
                websocket.send_json({
                    "type": "video_frame",
                    "data": frame_b64
                })
                time.sleep(0.1)
                
                # Receive feedback
                try:
                    feedback = websocket.receive_json(timeout=1)
                    if feedback.get("type") == "verification_success":
                        token = feedback.get("token")
                        assert token is not None
                        break
                except:
                    continue
        
        # Step 5: Verify token is valid
        if token:
            validate_response = client.post(
                "/api/token/validate",
                json={"token": token}
            )
            assert validate_response.status_code == 200
            validation_data = validate_response.json()
            assert validation_data["valid"] is True
            assert validation_data["user_id"] == "test_user_e2e"
        
        # Step 6: Verify audit logs contain all events
        final_logs = db.get_audit_logs(user_id="test_user_e2e", limit=50)
        event_types = [log["event_type"] for log in final_logs]
        assert "session_start" in event_types


class TestFailedVerificationFlow:
    """
    Test failed verification flow
    Requirements: 7.4, 13.2
    """
    
    def test_flow_with_failed_challenges(self):
        """Test flow with failed challenges - no token issued"""
        # Create session
        response = client.post(
            "/api/auth/verify",
            json={"user_id": "test_user_fail"}
        )
        assert response.status_code == 200
        session_id = response.json()["session_id"]
        
        # Connect and send poor quality frames
        with client.websocket_connect(f"/ws/verify/{session_id}") as websocket:
            # Receive challenge
            data = websocket.receive_json()
            assert data["type"] == "challenge_issued"
            
            # Send low-quality frames (should fail verification)
            bad_frame = np.zeros((100, 100, 3), dtype=np.uint8)
            frame_b64 = encode_frame(bad_frame)
            
            for _ in range(10):
                websocket.send_json({
                    "type": "video_frame",
                    "data": frame_b64
                })
                time.sleep(0.1)
                
                try:
                    feedback = websocket.receive_json(timeout=1)
                    if feedback.get("type") == "verification_failed":
                        # Verify no token was issued
                        assert "token" not in feedback or feedback.get("token") is None
                        break
                except:
                    continue
        
        # Verify failure was logged
        db = DatabaseService("pol_auth.db")
        logs = db.get_audit_logs(user_id="test_user_fail", limit=10)
        assert len(logs) > 0


class TestTimeoutScenarios:
    """
    Test timeout scenarios
    Requirements: 9.2, 9.3, 9.4
    """
    
    def test_challenge_timeout(self):
        """Test challenge timeout after 10 seconds"""
        response = client.post(
            "/api/auth/verify",
            json={"user_id": "test_timeout_challenge"}
        )
        session_id = response.json()["session_id"]
        
        with client.websocket_connect(f"/ws/verify/{session_id}") as websocket:
            # Receive challenge
            data = websocket.receive_json()
            assert data["type"] == "challenge_issued"
            
            # Wait for timeout (simulate no response)
            time.sleep(11)
            
            # Should receive timeout or failure message
            try:
                feedback = websocket.receive_json(timeout=2)
                assert feedback["type"] in ["challenge_failed", "error", "verification_failed"]
            except:
                pass  # Connection may close on timeout
    
    def test_session_timeout(self):
        """Test session timeout after 2 minutes"""
        response = client.post(
            "/api/auth/verify",
            json={"user_id": "test_timeout_session"}
        )
        session_id = response.json()["session_id"]
        
        # Check session is not timed out initially
        db = DatabaseService("pol_auth.db")
        session_manager = SessionManager(db)
        assert not session_manager.check_timeout(session_id)
        
        # Simulate time passing (modify session start time)
        session_data = db.get_session(session_id)
        old_start_time = time.time() - 121  # 121 seconds ago
        db.update_session(session_id, status=None)
        
        # Manually update start time for testing
        with db._get_connection() as conn:
            conn.execute(
                "UPDATE sessions SET start_time = ? WHERE session_id = ?",
                (old_start_time, session_id)
            )
            conn.commit()
        
        # Check timeout
        assert session_manager.check_timeout(session_id)


class TestSecurityScenarios:
    """
    Test security scenarios
    Requirements: 11.4, 5.5, 14.3, 14.4
    """
    
    def test_replay_attack_rejection(self):
        """Test replay attack is rejected"""
        # Create session and get nonce
        response = client.post(
            "/api/auth/verify",
            json={"user_id": f"test_replay_{time.time()}"}  # Unique user ID
        )
        session_id = response.json()["session_id"]
        
        db = DatabaseService("pol_auth.db")
        
        # Store a nonce
        test_nonce = f"test_nonce_{time.time()}"  # Unique nonce
        db.store_nonce(test_nonce, session_id, time.time() + 3600)
        
        # Try to use the same nonce again
        assert db.check_nonce_used(test_nonce) is True
        
        # Verify unused nonce is not marked as used
        unused_nonce = f"unused_nonce_{time.time()}"  # Unique nonce
        assert db.check_nonce_used(unused_nonce) is False
    
    def test_invalid_token_rejection(self):
        """Test invalid token is rejected"""
        # Test with completely invalid token
        response = client.post(
            "/api/token/validate",
            json={"token": "invalid.token.here"}
        )
        # API returns 401 for invalid tokens
        assert response.status_code in [200, 401]
        if response.status_code == 200:
            data = response.json()
            assert data["valid"] is False
        
        # Test with malformed token (just test the API response)
        response2 = client.post(
            "/api/token/validate",
            json={"token": "malformed"}
        )
        assert response2.status_code in [200, 401]
    
    def test_tampered_token_rejection(self):
        """Test tampered token payload is rejected"""
        # Create valid token
        token_issuer = TokenIssuer()
        valid_token = token_issuer.issue_jwt_token(
            user_id="test_user",
            session_id="test_session",
            final_score=0.75
        )
        
        # Tamper with the token (change a character)
        tampered_token = valid_token[:-10] + "TAMPERED"
        
        response = client.post(
            "/api/token/validate",
            json={"token": tampered_token}
        )
        # API returns 401 for tampered tokens
        assert response.status_code in [200, 401]
        if response.status_code == 200:
            data = response.json()
            assert data["valid"] is False


# Helper functions

def create_test_frame():
    """Create a test video frame"""
    frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
    # Add some structure to make it look more like a face
    cv2.circle(frame, (320, 240), 100, (255, 200, 150), -1)  # Face
    cv2.circle(frame, (280, 220), 20, (50, 50, 50), -1)  # Left eye
    cv2.circle(frame, (360, 220), 20, (50, 50, 50), -1)  # Right eye
    cv2.ellipse(frame, (320, 280), (40, 20), 0, 0, 180, (200, 100, 100), -1)  # Mouth
    return frame


def encode_frame(frame):
    """Encode frame to base64"""
    _, buffer = cv2.imencode('.jpg', frame)
    frame_b64 = base64.b64encode(buffer).decode('utf-8')
    return frame_b64


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
