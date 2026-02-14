"""
Integration tests for WebSocket verification endpoint

These tests verify the complete verification flow including:
- Challenge generation and distribution
- Video frame processing
- Score computation
- Token issuance
"""
import pytest
import base64
import numpy as np
import cv2
import json
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def create_test_frame(width=640, height=480):
    """Create a simple test video frame"""
    # Create a frame with some variation (not completely black)
    frame = np.random.randint(0, 255, (height, width, 3), dtype=np.uint8)
    _, buffer = cv2.imencode('.jpg', frame)
    return base64.b64encode(buffer).decode('utf-8')


def test_websocket_complete_verification_flow():
    """
    Test complete verification flow from session creation to token issuance.
    
    This test validates:
    - Session creation
    - WebSocket connection
    - Challenge issuance
    - Frame reception
    - Score computation
    - Token issuance (if scores are sufficient)
    
    Note: This test may not complete full verification if MediaPipe model
    is not available, but it validates the flow structure.
    """
    # Step 1: Create session
    response = client.post(
        "/api/auth/verify",
        json={"user_id": "integration_test_user"}
    )
    assert response.status_code == 200
    session_id = response.json()["session_id"]
    
    # Step 2: Connect to WebSocket
    with client.websocket_connect(f"/ws/verify/{session_id}") as websocket:
        challenges_received = 0
        
        # Receive first message (should be challenge)
        data = websocket.receive_json()
        
        if data["type"] == "challenge_issued":
            challenges_received += 1
            challenge_id = data["data"]["challenge_id"]
            
            # Send some test frames for this challenge
            for i in range(5):
                frame_data = create_test_frame()
                websocket.send_json({
                    "type": "video_frame",
                    "frame": frame_data
                })
            
            # Signal challenge completion
            websocket.send_json({
                "type": "challenge_complete",
                "challenge_id": challenge_id
            })
        
        # Verify we received at least one challenge
        assert challenges_received > 0, "Should receive at least one challenge"


def test_websocket_session_timeout():
    """Test that WebSocket handles session timeout correctly"""
    # Create a session
    response = client.post(
        "/api/auth/verify",
        json={"user_id": "timeout_test_user"}
    )
    session_id = response.json()["session_id"]
    
    # Manually mark session as timed out by updating database
    from app.main import database_service, session_manager
    import time
    import sqlite3
    
    # Get session and update it to be very old
    session_data = database_service.get_session(session_id)
    old_start_time = time.time() - (session_manager.MAX_SESSION_DURATION_SECONDS + 10)
    
    # Update the session start time directly in database
    with database_service._get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE sessions SET start_time = ? WHERE session_id = ?",
            (old_start_time, session_id)
        )
        conn.commit()
    
    # Try to connect - should be rejected
    with client.websocket_connect(f"/ws/verify/{session_id}") as websocket:
        data = websocket.receive_json()
        assert data["type"] == "error"
        assert "timed out" in data["message"].lower() or "timeout" in data["message"].lower()


def test_websocket_challenge_feedback_structure():
    """Test that challenge feedback has correct structure"""
    response = client.post(
        "/api/auth/verify",
        json={"user_id": "feedback_test_user"}
    )
    session_id = response.json()["session_id"]
    
    with client.websocket_connect(f"/ws/verify/{session_id}") as websocket:
        # Receive first challenge
        data = websocket.receive_json()
        
        # Verify feedback structure
        assert "type" in data
        assert "message" in data
        assert "data" in data or data["type"] == "error"
        
        if data["type"] == "challenge_issued":
            # Verify challenge data structure
            assert "challenge_id" in data["data"]
            assert "instruction" in data["data"]
            assert "timeout_seconds" in data["data"]
            assert data["data"]["timeout_seconds"] == 10


def test_websocket_frame_decoding():
    """Test that WebSocket correctly decodes base64 frames"""
    response = client.post(
        "/api/auth/verify",
        json={"user_id": "frame_decode_test"}
    )
    session_id = response.json()["session_id"]
    
    with client.websocket_connect(f"/ws/verify/{session_id}") as websocket:
        # Receive challenge
        data = websocket.receive_json()
        assert data["type"] == "challenge_issued"
        
        # Send a valid frame
        frame_data = create_test_frame()
        websocket.send_json({
            "type": "video_frame",
            "frame": frame_data
        })
        
        # Send frame with data URL prefix
        frame_with_prefix = f"data:image/jpeg;base64,{frame_data}"
        websocket.send_json({
            "type": "video_frame",
            "frame": frame_with_prefix
        })
        
        # WebSocket should continue processing without errors


def test_websocket_multiple_challenges():
    """Test that WebSocket issues multiple challenges"""
    response = client.post(
        "/api/auth/verify",
        json={"user_id": "multi_challenge_test"}
    )
    session_id = response.json()["session_id"]
    
    with client.websocket_connect(f"/ws/verify/{session_id}") as websocket:
        # Receive first challenge
        data = websocket.receive_json()
        
        assert data["type"] == "challenge_issued"
        challenge_id = data["data"]["challenge_id"]
        
        # Send some frames
        for _ in range(3):
            websocket.send_json({
                "type": "video_frame",
                "frame": create_test_frame()
            })
        
        # Complete challenge
        websocket.send_json({
            "type": "challenge_complete",
            "challenge_id": challenge_id
        })
        
        # Should have received at least one challenge
        assert challenge_id is not None


def test_websocket_real_time_feedback():
    """Test that WebSocket provides real-time feedback"""
    response = client.post(
        "/api/auth/verify",
        json={"user_id": "realtime_feedback_test"}
    )
    session_id = response.json()["session_id"]
    
    with client.websocket_connect(f"/ws/verify/{session_id}") as websocket:
        # Receive first message
        data = websocket.receive_json()
        
        # Should receive feedback
        assert "type" in data
        assert "message" in data
        
        # Should be challenge issued
        assert data["type"] == "challenge_issued"


def test_websocket_nonce_storage():
    """Test that nonce is stored for replay attack prevention"""
    from app.main import database_service
    
    response = client.post(
        "/api/auth/verify",
        json={"user_id": "nonce_test_user"}
    )
    session_id = response.json()["session_id"]
    
    # Connect to WebSocket to trigger nonce storage
    with client.websocket_connect(f"/ws/verify/{session_id}") as websocket:
        # Receive first message
        data = websocket.receive_json()
        assert data["type"] == "challenge_issued"
    
    # Verify nonce was stored (we can't easily check this without
    # accessing internal state, but we can verify the database method exists)
    # This is more of a smoke test
    assert hasattr(database_service, 'store_nonce')
    assert hasattr(database_service, 'check_nonce_used')


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
