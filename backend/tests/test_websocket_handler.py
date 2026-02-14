"""
Unit tests for WebSocketHandler class.

Tests cover:
- Connection handling
- Video frame reception and decoding
- Challenge transmission
- Feedback delivery
- Connection closure
- Property-based tests for frame transmission
"""
import pytest
import json
import base64
import numpy as np
import cv2
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi import WebSocket, WebSocketDisconnect
from hypothesis import given, strategies as st, settings

from app.services.websocket_handler import WebSocketHandler
from app.models.data_models import (
    Challenge,
    ChallengeType,
    VerificationFeedback,
    FeedbackType
)


@pytest.fixture
def websocket_handler():
    """Create WebSocketHandler instance for testing."""
    return WebSocketHandler()


@pytest.fixture
def mock_websocket():
    """Create mock WebSocket for testing."""
    websocket = AsyncMock(spec=WebSocket)
    return websocket


@pytest.fixture
def sample_challenge():
    """Create sample challenge for testing."""
    return Challenge(
        challenge_id="test_challenge_1",
        type=ChallengeType.GESTURE,
        instruction="Nod your head",
        timeout_seconds=10
    )


@pytest.fixture
def sample_frame():
    """Create sample video frame for testing."""
    # Create a simple 100x100 RGB image
    frame = np.zeros((100, 100, 3), dtype=np.uint8)
    frame[:, :] = [255, 0, 0]  # Blue frame
    return frame


@pytest.fixture
def encoded_frame(sample_frame):
    """Create base64-encoded frame for testing."""
    # Encode frame as JPEG
    _, buffer = cv2.imencode('.jpg', sample_frame)
    # Convert to base64
    encoded = base64.b64encode(buffer).decode('utf-8')
    # Add data URL prefix
    return f"data:image/jpeg;base64,{encoded}"


class TestHandleConnection:
    """Tests for handle_connection method."""
    
    @pytest.mark.asyncio
    async def test_accepts_websocket_connection(self, websocket_handler, mock_websocket):
        """Test that handle_connection accepts the WebSocket connection."""
        session_id = "test_session_123"
        
        await websocket_handler.handle_connection(mock_websocket, session_id)
        
        # Verify accept was called
        mock_websocket.accept.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_logs_connection_establishment(self, websocket_handler, mock_websocket):
        """Test that connection establishment is logged."""
        session_id = "test_session_456"
        
        with patch('app.services.websocket_handler.logger') as mock_logger:
            await websocket_handler.handle_connection(mock_websocket, session_id)
            
            # Verify info log was called with session ID
            mock_logger.info.assert_called_once()
            log_message = mock_logger.info.call_args[0][0]
            assert session_id in log_message
            assert "established" in log_message.lower()


class TestReceiveVideoFrame:
    """Tests for receive_video_frame method."""
    
    @pytest.mark.asyncio
    async def test_receives_and_decodes_valid_frame(
        self,
        websocket_handler,
        mock_websocket,
        encoded_frame
    ):
        """Test receiving and decoding a valid video frame."""
        # Mock WebSocket to return video frame message
        message = {
            "type": "video_frame",
            "frame": encoded_frame
        }
        mock_websocket.receive_text.return_value = json.dumps(message)
        
        frame = await websocket_handler.receive_video_frame(mock_websocket)
        
        # Verify frame was decoded
        assert frame is not None
        assert isinstance(frame, np.ndarray)
        assert frame.shape[2] == 3  # BGR format
        assert frame.dtype == np.uint8
    
    @pytest.mark.asyncio
    async def test_returns_none_for_non_frame_message(
        self,
        websocket_handler,
        mock_websocket
    ):
        """Test that non-frame messages return None."""
        # Mock WebSocket to return non-frame message
        message = {
            "type": "challenge_complete",
            "challenge_id": "test_123"
        }
        mock_websocket.receive_text.return_value = json.dumps(message)
        
        frame = await websocket_handler.receive_video_frame(mock_websocket)
        
        assert frame is None
    
    @pytest.mark.asyncio
    async def test_returns_none_for_invalid_json(
        self,
        websocket_handler,
        mock_websocket
    ):
        """Test that invalid JSON returns None."""
        # Mock WebSocket to return invalid JSON
        mock_websocket.receive_text.return_value = "not valid json {"
        
        frame = await websocket_handler.receive_video_frame(mock_websocket)
        
        assert frame is None
    
    @pytest.mark.asyncio
    async def test_returns_none_for_invalid_base64(
        self,
        websocket_handler,
        mock_websocket
    ):
        """Test that invalid base64 data returns None."""
        # Mock WebSocket to return message with invalid base64
        message = {
            "type": "video_frame",
            "frame": "not_valid_base64!!!"
        }
        mock_websocket.receive_text.return_value = json.dumps(message)
        
        frame = await websocket_handler.receive_video_frame(mock_websocket)
        
        assert frame is None
    
    @pytest.mark.asyncio
    async def test_handles_frame_without_data_url_prefix(
        self,
        websocket_handler,
        mock_websocket,
        sample_frame
    ):
        """Test decoding frame without data URL prefix."""
        # Encode frame without prefix
        _, buffer = cv2.imencode('.jpg', sample_frame)
        encoded = base64.b64encode(buffer).decode('utf-8')
        
        message = {
            "type": "video_frame",
            "frame": encoded
        }
        mock_websocket.receive_text.return_value = json.dumps(message)
        
        frame = await websocket_handler.receive_video_frame(mock_websocket)
        
        assert frame is not None
        assert isinstance(frame, np.ndarray)


class TestSendChallenge:
    """Tests for send_challenge method."""
    
    @pytest.mark.asyncio
    async def test_sends_challenge_with_correct_format(
        self,
        websocket_handler,
        mock_websocket,
        sample_challenge
    ):
        """Test that challenge is sent with correct format."""
        await websocket_handler.send_challenge(mock_websocket, sample_challenge)
        
        # Verify send_json was called
        mock_websocket.send_json.assert_called_once()
        
        # Verify message format
        sent_data = mock_websocket.send_json.call_args[0][0]
        assert sent_data["type"] == FeedbackType.CHALLENGE_ISSUED.value
        assert sample_challenge.instruction in sent_data["message"]
        assert sent_data["data"]["challenge_id"] == sample_challenge.challenge_id
        assert sent_data["data"]["instruction"] == sample_challenge.instruction
        assert sent_data["data"]["timeout_seconds"] == sample_challenge.timeout_seconds
        assert sent_data["data"]["type"] == sample_challenge.type.value
    
    @pytest.mark.asyncio
    async def test_sends_gesture_challenge(
        self,
        websocket_handler,
        mock_websocket
    ):
        """Test sending a gesture challenge."""
        challenge = Challenge(
            challenge_id="gesture_1",
            type=ChallengeType.GESTURE,
            instruction="Turn your head left",
            timeout_seconds=10
        )
        
        await websocket_handler.send_challenge(mock_websocket, challenge)
        
        sent_data = mock_websocket.send_json.call_args[0][0]
        assert sent_data["data"]["type"] == "gesture"
    
    @pytest.mark.asyncio
    async def test_sends_expression_challenge(
        self,
        websocket_handler,
        mock_websocket
    ):
        """Test sending an expression challenge."""
        challenge = Challenge(
            challenge_id="expression_1",
            type=ChallengeType.EXPRESSION,
            instruction="Smile",
            timeout_seconds=10
        )
        
        await websocket_handler.send_challenge(mock_websocket, challenge)
        
        sent_data = mock_websocket.send_json.call_args[0][0]
        assert sent_data["data"]["type"] == "expression"


class TestSendFeedback:
    """Tests for send_feedback method."""
    
    @pytest.mark.asyncio
    async def test_sends_feedback_with_correct_format(
        self,
        websocket_handler,
        mock_websocket
    ):
        """Test that feedback is sent with correct format."""
        feedback = VerificationFeedback(
            type=FeedbackType.CHALLENGE_COMPLETED,
            message="Challenge completed successfully",
            data={"challenge_id": "test_123", "confidence": 0.95}
        )
        
        await websocket_handler.send_feedback(mock_websocket, feedback)
        
        # Verify send_json was called
        mock_websocket.send_json.assert_called_once()
        
        # Verify message format
        sent_data = mock_websocket.send_json.call_args[0][0]
        assert sent_data["type"] == feedback.type.value
        assert sent_data["message"] == feedback.message
        assert sent_data["data"] == feedback.data
    
    @pytest.mark.asyncio
    async def test_sends_score_update_feedback(
        self,
        websocket_handler,
        mock_websocket
    ):
        """Test sending score update feedback."""
        feedback = VerificationFeedback(
            type=FeedbackType.SCORE_UPDATE,
            message="Scores computed",
            data={
                "liveness_score": 0.85,
                "emotion_score": 0.90,
                "deepfake_score": 0.95
            }
        )
        
        await websocket_handler.send_feedback(mock_websocket, feedback)
        
        sent_data = mock_websocket.send_json.call_args[0][0]
        assert sent_data["type"] == "score_update"
        assert sent_data["data"]["liveness_score"] == 0.85
    
    @pytest.mark.asyncio
    async def test_sends_error_feedback(
        self,
        websocket_handler,
        mock_websocket
    ):
        """Test sending error feedback."""
        feedback = VerificationFeedback(
            type=FeedbackType.ERROR,
            message="Session timeout",
            data=None
        )
        
        await websocket_handler.send_feedback(mock_websocket, feedback)
        
        sent_data = mock_websocket.send_json.call_args[0][0]
        assert sent_data["type"] == "error"
        assert sent_data["message"] == "Session timeout"
        assert sent_data["data"] is None
    
    @pytest.mark.asyncio
    async def test_sends_verification_success_feedback(
        self,
        websocket_handler,
        mock_websocket
    ):
        """Test sending verification success feedback."""
        feedback = VerificationFeedback(
            type=FeedbackType.VERIFICATION_SUCCESS,
            message="Verification successful!",
            data={
                "token": "jwt_token_here",
                "final_score": 0.85
            }
        )
        
        await websocket_handler.send_feedback(mock_websocket, feedback)
        
        sent_data = mock_websocket.send_json.call_args[0][0]
        assert sent_data["type"] == "verification_success"
        assert "token" in sent_data["data"]


class TestCloseConnection:
    """Tests for close_connection method."""
    
    @pytest.mark.asyncio
    async def test_closes_connection_with_default_code(
        self,
        websocket_handler,
        mock_websocket
    ):
        """Test closing connection with default code."""
        await websocket_handler.close_connection(mock_websocket)
        
        mock_websocket.close.assert_called_once_with(
            code=1000,
            reason="Normal closure"
        )
    
    @pytest.mark.asyncio
    async def test_closes_connection_with_custom_code(
        self,
        websocket_handler,
        mock_websocket
    ):
        """Test closing connection with custom code and reason."""
        await websocket_handler.close_connection(
            mock_websocket,
            code=1008,
            reason="Session timeout"
        )
        
        mock_websocket.close.assert_called_once_with(
            code=1008,
            reason="Session timeout"
        )
    
    @pytest.mark.asyncio
    async def test_handles_close_error_gracefully(
        self,
        websocket_handler,
        mock_websocket
    ):
        """Test that close errors are handled gracefully."""
        mock_websocket.close.side_effect = Exception("Connection already closed")
        
        # Should not raise exception
        await websocket_handler.close_connection(mock_websocket)


class TestDecodeFrame:
    """Tests for _decode_frame internal method."""
    
    def test_decodes_frame_with_data_url_prefix(
        self,
        websocket_handler,
        encoded_frame
    ):
        """Test decoding frame with data URL prefix."""
        frame = websocket_handler._decode_frame(encoded_frame)
        
        assert frame is not None
        assert isinstance(frame, np.ndarray)
        assert len(frame.shape) == 3
        assert frame.shape[2] == 3  # BGR
    
    def test_decodes_frame_without_prefix(
        self,
        websocket_handler,
        sample_frame
    ):
        """Test decoding frame without data URL prefix."""
        # Encode without prefix
        _, buffer = cv2.imencode('.jpg', sample_frame)
        encoded = base64.b64encode(buffer).decode('utf-8')
        
        frame = websocket_handler._decode_frame(encoded)
        
        assert frame is not None
        assert isinstance(frame, np.ndarray)
    
    def test_returns_none_for_invalid_base64(
        self,
        websocket_handler
    ):
        """Test that invalid base64 returns None."""
        frame = websocket_handler._decode_frame("not_valid_base64!!!")
        
        assert frame is None
    
    def test_returns_none_for_corrupted_image_data(
        self,
        websocket_handler
    ):
        """Test that corrupted image data returns None."""
        # Valid base64 but not a valid image
        corrupted = base64.b64encode(b"not an image").decode('utf-8')
        
        frame = websocket_handler._decode_frame(corrupted)
        
        assert frame is None
    
    def test_handles_different_image_formats(
        self,
        websocket_handler,
        sample_frame
    ):
        """Test decoding different image formats (JPEG, PNG)."""
        # Test JPEG
        _, buffer_jpg = cv2.imencode('.jpg', sample_frame)
        encoded_jpg = base64.b64encode(buffer_jpg).decode('utf-8')
        frame_jpg = websocket_handler._decode_frame(encoded_jpg)
        assert frame_jpg is not None
        
        # Test PNG
        _, buffer_png = cv2.imencode('.png', sample_frame)
        encoded_png = base64.b64encode(buffer_png).decode('utf-8')
        frame_png = websocket_handler._decode_frame(encoded_png)
        assert frame_png is not None



class TestPropertyFrameTransmission:
    """
    Property-based tests for frame transmission via WebSocket.
    
    **Validates: Requirements 10.2**
    **Property 15: Frame Transmission via WebSocket**
    
    For any captured video frame during an active session, the frame should be
    transmitted to the backend via the WebSocket connection and successfully
    decoded back to its original format.
    """
    
    @given(
        height=st.integers(min_value=50, max_value=1920),
        width=st.integers(min_value=50, max_value=1920),
        red=st.integers(min_value=0, max_value=255),
        green=st.integers(min_value=0, max_value=255),
        blue=st.integers(min_value=0, max_value=255)
    )
    @settings(max_examples=100, deadline=None)
    @pytest.mark.asyncio
    async def test_property_frame_encoding_decoding_roundtrip(
        self,
        height,
        width,
        red,
        green,
        blue
    ):
        """
        Property Test: Frame Transmission via WebSocket
        
        **Validates: Requirements 10.2**
        
        For any video frame with arbitrary dimensions and color values,
        the frame should be successfully:
        1. Encoded to base64 format (simulating frontend transmission)
        2. Transmitted via WebSocket message
        3. Decoded back to numpy array (backend reception)
        4. Maintain correct shape and data type
        
        This property ensures that the encoding/decoding pipeline is robust
        across all possible frame configurations.
        """
        websocket_handler = WebSocketHandler()
        mock_websocket = AsyncMock(spec=WebSocket)
        
        # Create a frame with the given dimensions and color
        original_frame = np.zeros((height, width, 3), dtype=np.uint8)
        original_frame[:, :] = [blue, green, red]  # BGR format
        
        # Encode frame as JPEG (simulating frontend)
        _, buffer = cv2.imencode('.jpg', original_frame)
        encoded = base64.b64encode(buffer).decode('utf-8')
        
        # Create WebSocket message with data URL prefix
        frame_data = f"data:image/jpeg;base64,{encoded}"
        message = {
            "type": "video_frame",
            "frame": frame_data
        }
        
        # Mock WebSocket to return the encoded frame
        mock_websocket.receive_text.return_value = json.dumps(message)
        
        # Receive and decode frame (simulating backend)
        decoded_frame = await websocket_handler.receive_video_frame(mock_websocket)
        
        # Property assertions
        assert decoded_frame is not None, "Frame should be successfully decoded"
        assert isinstance(decoded_frame, np.ndarray), "Decoded frame should be numpy array"
        assert decoded_frame.dtype == np.uint8, "Frame should have uint8 data type"
        assert len(decoded_frame.shape) == 3, "Frame should be 3-dimensional"
        assert decoded_frame.shape[2] == 3, "Frame should have 3 color channels (BGR)"
        
        # Verify dimensions are preserved (allowing for JPEG compression artifacts)
        assert decoded_frame.shape[0] == height, f"Height should be preserved: expected {height}, got {decoded_frame.shape[0]}"
        assert decoded_frame.shape[1] == width, f"Width should be preserved: expected {width}, got {decoded_frame.shape[1]}"
    
    @given(
        height=st.integers(min_value=100, max_value=640),
        width=st.integers(min_value=100, max_value=640)
    )
    @settings(max_examples=100, deadline=None)
    @pytest.mark.asyncio
    async def test_property_frame_transmission_without_data_url_prefix(
        self,
        height,
        width
    ):
        """
        Property Test: Frame transmission works with or without data URL prefix.
        
        **Validates: Requirements 10.2**
        
        For any video frame, the decoding should work correctly whether the
        base64 data includes the data URL prefix or not. This ensures
        compatibility with different frontend implementations.
        """
        websocket_handler = WebSocketHandler()
        mock_websocket = AsyncMock(spec=WebSocket)
        
        # Create a random frame
        original_frame = np.random.randint(0, 256, (height, width, 3), dtype=np.uint8)
        
        # Encode frame without data URL prefix
        _, buffer = cv2.imencode('.jpg', original_frame)
        encoded = base64.b64encode(buffer).decode('utf-8')
        
        message = {
            "type": "video_frame",
            "frame": encoded  # No prefix
        }
        
        mock_websocket.receive_text.return_value = json.dumps(message)
        
        # Decode frame
        decoded_frame = await websocket_handler.receive_video_frame(mock_websocket)
        
        # Property assertions
        assert decoded_frame is not None, "Frame without prefix should be decoded"
        assert isinstance(decoded_frame, np.ndarray), "Should return numpy array"
        assert decoded_frame.shape == (height, width, 3), "Dimensions should be preserved"
        assert decoded_frame.dtype == np.uint8, "Data type should be uint8"
    
    @given(
        height=st.integers(min_value=100, max_value=640),
        width=st.integers(min_value=100, max_value=640),
        format_choice=st.sampled_from(['.jpg', '.png'])
    )
    @settings(max_examples=100, deadline=None)
    @pytest.mark.asyncio
    async def test_property_frame_transmission_multiple_formats(
        self,
        height,
        width,
        format_choice
    ):
        """
        Property Test: Frame transmission works with different image formats.
        
        **Validates: Requirements 10.2**
        
        For any video frame encoded in different formats (JPEG, PNG),
        the transmission and decoding should work correctly.
        """
        websocket_handler = WebSocketHandler()
        mock_websocket = AsyncMock(spec=WebSocket)
        
        # Create a frame with some pattern
        original_frame = np.random.randint(0, 256, (height, width, 3), dtype=np.uint8)
        
        # Encode frame in the specified format
        _, buffer = cv2.imencode(format_choice, original_frame)
        encoded = base64.b64encode(buffer).decode('utf-8')
        
        # Determine MIME type
        mime_type = "image/jpeg" if format_choice == '.jpg' else "image/png"
        frame_data = f"data:{mime_type};base64,{encoded}"
        
        message = {
            "type": "video_frame",
            "frame": frame_data
        }
        
        mock_websocket.receive_text.return_value = json.dumps(message)
        
        # Decode frame
        decoded_frame = await websocket_handler.receive_video_frame(mock_websocket)
        
        # Property assertions
        assert decoded_frame is not None, f"Frame in {format_choice} format should be decoded"
        assert isinstance(decoded_frame, np.ndarray), "Should return numpy array"
        assert decoded_frame.shape == (height, width, 3), "Dimensions should be preserved"
        assert decoded_frame.dtype == np.uint8, "Data type should be uint8"
    
    @given(
        num_frames=st.integers(min_value=1, max_value=10)
    )
    @settings(max_examples=100, deadline=None)
    @pytest.mark.asyncio
    async def test_property_multiple_frame_transmission(
        self,
        num_frames
    ):
        """
        Property Test: Multiple frames can be transmitted sequentially.
        
        **Validates: Requirements 10.2**
        
        For any sequence of video frames, each frame should be successfully
        transmitted and decoded independently. This simulates a real verification
        session where multiple frames are sent over time.
        """
        websocket_handler = WebSocketHandler()
        mock_websocket = AsyncMock(spec=WebSocket)
        
        # Create multiple frames with different colors
        frames = []
        for i in range(num_frames):
            frame = np.zeros((100, 100, 3), dtype=np.uint8)
            # Each frame has a unique color based on index
            color_value = min(255, (i + 1) * 25)
            frame[:, :] = [color_value, color_value, color_value]
            frames.append(frame)
        
        # Transmit and decode each frame
        decoded_frames = []
        for original_frame in frames:
            # Encode frame
            _, buffer = cv2.imencode('.jpg', original_frame)
            encoded = base64.b64encode(buffer).decode('utf-8')
            frame_data = f"data:image/jpeg;base64,{encoded}"
            
            message = {
                "type": "video_frame",
                "frame": frame_data
            }
            
            mock_websocket.receive_text.return_value = json.dumps(message)
            
            # Decode frame
            decoded_frame = await websocket_handler.receive_video_frame(mock_websocket)
            decoded_frames.append(decoded_frame)
        
        # Property assertions
        assert len(decoded_frames) == num_frames, "All frames should be decoded"
        
        for i, decoded_frame in enumerate(decoded_frames):
            assert decoded_frame is not None, f"Frame {i} should be decoded"
            assert isinstance(decoded_frame, np.ndarray), f"Frame {i} should be numpy array"
            assert decoded_frame.shape == (100, 100, 3), f"Frame {i} dimensions should be preserved"
            assert decoded_frame.dtype == np.uint8, f"Frame {i} should have uint8 data type"


class TestConnectionDrop:
    """Tests for WebSocket connection drop handling."""
    
    @pytest.mark.asyncio
    async def test_connection_drop_raises_websocket_disconnect(
        self,
        websocket_handler,
        mock_websocket
    ):
        """
        Test that connection drop raises WebSocketDisconnect exception.
        
        **Validates: Requirements 10.4**
        
        When the WebSocket connection drops during frame reception,
        the receive_video_frame method should raise WebSocketDisconnect
        exception, which will be caught by the endpoint handler to
        terminate the session.
        """
        # Mock WebSocket to raise WebSocketDisconnect
        mock_websocket.receive_text.side_effect = WebSocketDisconnect()
        
        # Verify that WebSocketDisconnect is raised
        with pytest.raises(WebSocketDisconnect):
            await websocket_handler.receive_video_frame(mock_websocket)
    
    @pytest.mark.asyncio
    async def test_connection_drop_during_frame_reception(
        self,
        websocket_handler,
        mock_websocket
    ):
        """
        Test that connection drop during frame reception is properly detected.
        
        **Validates: Requirements 10.4**
        
        When the WebSocket connection drops while waiting for a video frame,
        the exception should propagate to allow the endpoint handler to
        terminate the session.
        """
        # Simulate connection drop
        mock_websocket.receive_text.side_effect = WebSocketDisconnect(
            code=1001,
            reason="Client disconnected"
        )
        
        # Attempt to receive frame
        with pytest.raises(WebSocketDisconnect) as exc_info:
            await websocket_handler.receive_video_frame(mock_websocket)
        
        # Verify exception details
        assert exc_info.value.code == 1001
        assert exc_info.value.reason == "Client disconnected"


class TestPropertyStatusUpdatePropagation:
    """
    Property-based tests for status update propagation.
    
    **Validates: Requirements 10.5, 12.3**
    **Property 16: Status Update Propagation**
    
    For any significant verification event (challenge completion, score update,
    verification result), the system should send a status update message to the frontend.
    """
    
    @given(
        challenge_id=st.text(min_size=1, max_size=50),
        instruction=st.sampled_from([
            "Nod your head",
            "Turn left",
            "Turn right",
            "Smile",
            "Look surprised",
            "Raise eyebrows"
        ]),
        timeout=st.integers(min_value=5, max_value=30)
    )
    @settings(max_examples=100, deadline=None)
    @pytest.mark.asyncio
    async def test_property_challenge_completion_sends_status_update(
        self,
        challenge_id,
        instruction,
        timeout
    ):
        """
        Property Test: Challenge completion events trigger status updates.
        
        **Validates: Requirements 10.5, 12.3**
        
        For any challenge completion event, the system should send a status
        update message to the frontend via WebSocket. This ensures users
        receive real-time feedback on their verification progress.
        """
        websocket_handler = WebSocketHandler()
        mock_websocket = AsyncMock(spec=WebSocket)
        
        # Create challenge completion feedback
        feedback = VerificationFeedback(
            type=FeedbackType.CHALLENGE_COMPLETED,
            message=f"Challenge '{instruction}' completed successfully",
            data={
                "challenge_id": challenge_id,
                "instruction": instruction,
                "confidence": 0.95
            }
        )
        
        # Send feedback (simulating challenge completion event)
        await websocket_handler.send_feedback(mock_websocket, feedback)
        
        # Property assertions: Status update should be sent
        mock_websocket.send_json.assert_called_once()
        
        sent_data = mock_websocket.send_json.call_args[0][0]
        assert sent_data is not None, "Status update should be sent"
        assert "type" in sent_data, "Status update should have type field"
        assert sent_data["type"] == FeedbackType.CHALLENGE_COMPLETED.value
        assert "message" in sent_data, "Status update should have message field"
        assert "data" in sent_data, "Status update should have data field"
        assert sent_data["data"]["challenge_id"] == challenge_id
    
    @given(
        liveness_score=st.floats(min_value=0.0, max_value=1.0),
        deepfake_score=st.floats(min_value=0.0, max_value=1.0),
        emotion_score=st.floats(min_value=0.0, max_value=1.0)
    )
    @settings(max_examples=100, deadline=None)
    @pytest.mark.asyncio
    async def test_property_score_update_sends_status_update(
        self,
        liveness_score,
        deepfake_score,
        emotion_score
    ):
        """
        Property Test: Score update events trigger status updates.
        
        **Validates: Requirements 10.5, 12.3**
        
        For any score update event (liveness, deepfake, emotion scores computed),
        the system should send a status update message to the frontend. This
        provides real-time feedback on verification progress.
        """
        websocket_handler = WebSocketHandler()
        mock_websocket = AsyncMock(spec=WebSocket)
        
        # Create score update feedback
        feedback = VerificationFeedback(
            type=FeedbackType.SCORE_UPDATE,
            message="Verification scores computed",
            data={
                "liveness_score": liveness_score,
                "deepfake_score": deepfake_score,
                "emotion_score": emotion_score
            }
        )
        
        # Send feedback (simulating score update event)
        await websocket_handler.send_feedback(mock_websocket, feedback)
        
        # Property assertions: Status update should be sent
        mock_websocket.send_json.assert_called_once()
        
        sent_data = mock_websocket.send_json.call_args[0][0]
        assert sent_data is not None, "Status update should be sent"
        assert sent_data["type"] == FeedbackType.SCORE_UPDATE.value
        assert "data" in sent_data
        assert "liveness_score" in sent_data["data"]
        assert "deepfake_score" in sent_data["data"]
        assert "emotion_score" in sent_data["data"]
        assert sent_data["data"]["liveness_score"] == liveness_score
        assert sent_data["data"]["deepfake_score"] == deepfake_score
        assert sent_data["data"]["emotion_score"] == emotion_score
    
    @given(
        final_score=st.floats(min_value=0.0, max_value=1.0),
        passed=st.booleans()
    )
    @settings(max_examples=100, deadline=None)
    @pytest.mark.asyncio
    async def test_property_verification_result_sends_status_update(
        self,
        final_score,
        passed
    ):
        """
        Property Test: Verification result events trigger status updates.
        
        **Validates: Requirements 10.5, 12.3**
        
        For any verification result (success or failure), the system should
        send a status update message to the frontend. This ensures users
        are immediately informed of the verification outcome.
        """
        websocket_handler = WebSocketHandler()
        mock_websocket = AsyncMock(spec=WebSocket)
        
        # Determine feedback type based on result
        feedback_type = (
            FeedbackType.VERIFICATION_SUCCESS if passed
            else FeedbackType.VERIFICATION_FAILED
        )
        
        # Create verification result feedback
        feedback = VerificationFeedback(
            type=feedback_type,
            message="Verification successful!" if passed else "Verification failed",
            data={
                "final_score": final_score,
                "passed": passed
            }
        )
        
        # Send feedback (simulating verification result event)
        await websocket_handler.send_feedback(mock_websocket, feedback)
        
        # Property assertions: Status update should be sent
        mock_websocket.send_json.assert_called_once()
        
        sent_data = mock_websocket.send_json.call_args[0][0]
        assert sent_data is not None, "Status update should be sent"
        assert sent_data["type"] == feedback_type.value
        assert "data" in sent_data
        assert "final_score" in sent_data["data"]
        assert "passed" in sent_data["data"]
        assert sent_data["data"]["final_score"] == final_score
        assert sent_data["data"]["passed"] == passed
    
    @given(
        challenge_id=st.text(min_size=1, max_size=50),
        reason=st.sampled_from([
            "Timeout",
            "Incorrect gesture",
            "No face detected",
            "Poor lighting"
        ])
    )
    @settings(max_examples=100, deadline=None)
    @pytest.mark.asyncio
    async def test_property_challenge_failure_sends_status_update(
        self,
        challenge_id,
        reason
    ):
        """
        Property Test: Challenge failure events trigger status updates.
        
        **Validates: Requirements 10.5, 12.3**
        
        For any challenge failure event, the system should send a status
        update message to the frontend explaining the failure reason.
        """
        websocket_handler = WebSocketHandler()
        mock_websocket = AsyncMock(spec=WebSocket)
        
        # Create challenge failure feedback
        feedback = VerificationFeedback(
            type=FeedbackType.CHALLENGE_FAILED,
            message=f"Challenge failed: {reason}",
            data={
                "challenge_id": challenge_id,
                "reason": reason
            }
        )
        
        # Send feedback (simulating challenge failure event)
        await websocket_handler.send_feedback(mock_websocket, feedback)
        
        # Property assertions: Status update should be sent
        mock_websocket.send_json.assert_called_once()
        
        sent_data = mock_websocket.send_json.call_args[0][0]
        assert sent_data is not None, "Status update should be sent"
        assert sent_data["type"] == FeedbackType.CHALLENGE_FAILED.value
        assert "data" in sent_data
        assert sent_data["data"]["challenge_id"] == challenge_id
        assert sent_data["data"]["reason"] == reason
    
    @given(
        event_type=st.sampled_from([
            FeedbackType.CHALLENGE_ISSUED,
            FeedbackType.CHALLENGE_COMPLETED,
            FeedbackType.CHALLENGE_FAILED,
            FeedbackType.SCORE_UPDATE,
            FeedbackType.VERIFICATION_SUCCESS,
            FeedbackType.VERIFICATION_FAILED,
            FeedbackType.ERROR
        ]),
        message=st.text(min_size=1, max_size=200)
    )
    @settings(max_examples=100, deadline=None)
    @pytest.mark.asyncio
    async def test_property_all_significant_events_send_status_updates(
        self,
        event_type,
        message
    ):
        """
        Property Test: All significant verification events trigger status updates.
        
        **Validates: Requirements 10.5, 12.3**
        
        For any significant verification event type (challenge issued, completed,
        failed, score update, verification result, error), the system should
        send a status update message to the frontend.
        
        This is the core property test that validates the universal requirement
        that all significant events result in status updates.
        """
        websocket_handler = WebSocketHandler()
        mock_websocket = AsyncMock(spec=WebSocket)
        
        # Create feedback for the given event type
        feedback = VerificationFeedback(
            type=event_type,
            message=message,
            data={"event_type": event_type.value}
        )
        
        # Send feedback (simulating any significant event)
        await websocket_handler.send_feedback(mock_websocket, feedback)
        
        # Property assertions: Status update should ALWAYS be sent
        mock_websocket.send_json.assert_called_once()
        
        sent_data = mock_websocket.send_json.call_args[0][0]
        assert sent_data is not None, "Status update should be sent for all significant events"
        assert "type" in sent_data, "Status update must have type field"
        assert "message" in sent_data, "Status update must have message field"
        assert sent_data["type"] == event_type.value, "Event type should be preserved"
        assert sent_data["message"] == message, "Message should be preserved"
    
    @given(
        num_events=st.integers(min_value=1, max_value=20)
    )
    @settings(max_examples=100, deadline=None)
    @pytest.mark.asyncio
    async def test_property_multiple_events_send_multiple_status_updates(
        self,
        num_events
    ):
        """
        Property Test: Multiple events result in multiple status updates.
        
        **Validates: Requirements 10.5, 12.3**
        
        For any sequence of verification events, each event should trigger
        its own status update. This simulates a real verification session
        where multiple events occur (challenges issued, completed, scores
        computed, etc.).
        """
        websocket_handler = WebSocketHandler()
        mock_websocket = AsyncMock(spec=WebSocket)
        
        # Create a sequence of different events
        event_types = [
            FeedbackType.CHALLENGE_ISSUED,
            FeedbackType.CHALLENGE_COMPLETED,
            FeedbackType.SCORE_UPDATE,
            FeedbackType.VERIFICATION_SUCCESS
        ]
        
        # Send multiple events
        for i in range(num_events):
            event_type = event_types[i % len(event_types)]
            feedback = VerificationFeedback(
                type=event_type,
                message=f"Event {i}: {event_type.value}",
                data={"event_index": i}
            )
            
            await websocket_handler.send_feedback(mock_websocket, feedback)
        
        # Property assertions: Each event should trigger a status update
        assert mock_websocket.send_json.call_count == num_events, \
            f"Should send {num_events} status updates for {num_events} events"
        
        # Verify each call was made with proper data
        for i, call in enumerate(mock_websocket.send_json.call_args_list):
            sent_data = call[0][0]
            assert sent_data is not None, f"Status update {i} should not be None"
            assert "type" in sent_data, f"Status update {i} should have type"
            assert "message" in sent_data, f"Status update {i} should have message"
            assert "data" in sent_data, f"Status update {i} should have data"
