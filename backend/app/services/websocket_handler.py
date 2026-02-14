"""
WebSocket handler for real-time proof-of-life verification communication.

This module provides the WebSocketHandler class that manages WebSocket connections,
video frame transmission, challenge delivery, and real-time feedback during verification.
"""
from fastapi import WebSocket, WebSocketDisconnect
from typing import Optional, List
import logging
import json
import base64
import numpy as np
import cv2

from app.models.data_models import (
    VerificationFeedback,
    FeedbackType,
    Challenge,
    ChallengeResult
)

logger = logging.getLogger(__name__)


class WebSocketHandler:
    """
    Manages WebSocket communication for real-time verification.
    
    This class encapsulates all WebSocket-related functionality including:
    - Connection lifecycle management
    - Video frame reception and decoding
    - Challenge transmission
    - Real-time feedback delivery
    
    Validates Requirements: 10.1, 10.2, 10.5
    """
    
    def __init__(self):
        """Initialize WebSocket handler."""
        pass
    
    async def handle_connection(
        self,
        websocket: WebSocket,
        session_id: str
    ) -> None:
        """
        Accept and manage WebSocket connection lifecycle.
        
        This method accepts the WebSocket connection and prepares it for
        bidirectional communication during the verification process.
        
        Args:
            websocket: FastAPI WebSocket connection object
            session_id: Unique session identifier
            
        Validates Requirements: 10.1
        """
        await websocket.accept()
        logger.info(f"WebSocket connection established for session {session_id}")
    
    async def receive_video_frame(self, websocket: WebSocket) -> Optional[np.ndarray]:
        """
        Receive and decode a video frame from the client.
        
        This method receives a message from the WebSocket, expects it to contain
        a base64-encoded video frame, and decodes it into a numpy array suitable
        for computer vision processing.
        
        Args:
            websocket: FastAPI WebSocket connection object
            
        Returns:
            Decoded video frame as numpy array, or None if:
            - Message is not a video frame
            - Decoding fails
            - Connection error occurs
            
        Validates Requirements: 10.2
        """
        try:
            # Receive text message from client
            data = await websocket.receive_text()
            
            # Parse JSON message
            message = json.loads(data)
            
            # Check if this is a video frame message
            if message.get("type") == "video_frame":
                frame_data = message.get("frame")
                if frame_data:
                    # Decode base64 frame
                    frame = self._decode_frame(frame_data)
                    return frame
            
            return None
        
        except WebSocketDisconnect:
            logger.info("WebSocket disconnected while receiving frame")
            raise
        
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON received: {e}")
            return None
        
        except Exception as e:
            logger.error(f"Error receiving video frame: {e}")
            return None
    
    async def send_challenge(
        self,
        websocket: WebSocket,
        challenge: Challenge
    ) -> None:
        """
        Send a challenge to the client.
        
        This method transmits a challenge instruction to the frontend,
        including the challenge ID, instruction text, and timeout duration.
        
        Args:
            websocket: FastAPI WebSocket connection object
            challenge: Challenge object containing instruction details
            
        Validates Requirements: 10.5
        """
        await self.send_feedback(
            websocket,
            VerificationFeedback(
                type=FeedbackType.CHALLENGE_ISSUED,
                message=f"Challenge: {challenge.instruction}",
                data={
                    "challenge_id": challenge.challenge_id,
                    "instruction": challenge.instruction,
                    "timeout_seconds": challenge.timeout_seconds,
                    "type": challenge.type.value
                }
            )
        )
        logger.debug(f"Sent challenge {challenge.challenge_id}: {challenge.instruction}")
    
    async def send_feedback(
        self,
        websocket: WebSocket,
        feedback: VerificationFeedback
    ) -> None:
        """
        Send real-time feedback to the client.
        
        This method transmits status updates, score information, challenge results,
        and other feedback messages to the frontend for display to the user.
        
        Args:
            websocket: FastAPI WebSocket connection object
            feedback: VerificationFeedback object containing message details
            
        Validates Requirements: 10.5
        """
        try:
            # Convert feedback to JSON-serializable format
            feedback_dict = {
                "type": feedback.type.value,
                "message": feedback.message,
                "data": feedback.data
            }
            
            # Send JSON message
            await websocket.send_json(feedback_dict)
            logger.debug(f"Sent feedback: {feedback.type.value}")
        
        except Exception as e:
            logger.error(f"Error sending feedback: {e}")
            raise
    
    async def close_connection(
        self,
        websocket: WebSocket,
        code: int = 1000,
        reason: str = "Normal closure"
    ) -> None:
        """
        Close the WebSocket connection gracefully.
        
        Args:
            websocket: FastAPI WebSocket connection object
            code: WebSocket close code (default: 1000 for normal closure)
            reason: Human-readable reason for closure
        """
        try:
            await websocket.close(code=code, reason=reason)
            logger.info(f"WebSocket closed: {reason} (code: {code})")
        except Exception as e:
            logger.error(f"Error closing WebSocket: {e}")
    
    def _decode_frame(self, frame_data: str) -> Optional[np.ndarray]:
        """
        Decode base64-encoded video frame.
        
        This internal method handles the conversion of base64-encoded image data
        (typically from a browser canvas) into a numpy array suitable for OpenCV
        and MediaPipe processing.
        
        Args:
            frame_data: Base64-encoded image data (may include data URL prefix)
            
        Returns:
            Decoded frame as numpy array (BGR format), or None if decoding fails
        """
        try:
            # Remove data URL prefix if present (e.g., "data:image/jpeg;base64,")
            if "," in frame_data:
                frame_data = frame_data.split(",")[1]
            
            # Decode base64 to bytes
            img_bytes = base64.b64decode(frame_data)
            
            # Convert bytes to numpy array
            nparr = np.frombuffer(img_bytes, np.uint8)
            
            # Decode image using OpenCV (returns BGR format)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if frame is None:
                logger.error("Failed to decode frame: cv2.imdecode returned None")
                return None
            
            return frame
        
        except Exception as e:
            logger.error(f"Error decoding frame: {e}")
            return None
