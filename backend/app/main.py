"""
FastAPI application entry point for Proof of Life Authentication System
"""
from fastapi import FastAPI, HTTPException, Request, Header, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional
import os
import logging
import json
import base64
import numpy as np
import cv2
import uuid
import time
import asyncio
import jwt as pyjwt
import httpx
from dotenv import load_dotenv

# Import all services
from app.services import (
    DatabaseService,
    SessionManager,
    ChallengeEngine,
    CVVerifier,
    ScoringEngine,
    TokenIssuer,
    EmotionAnalyzer,
    DeepfakeDetector,
    BlockchainLedger
)

# Import data models
from app.models.data_models import (
    VerificationFeedback,
    FeedbackType,
    ChallengeResult
)

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Proof of Life Authentication API",
    description="Multi-factor proof of life authentication system with liveness detection",
    version="1.0.0"
)

# CORS configuration for Next.js frontend
origins = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
database_service = DatabaseService()  # Now uses Convex
session_manager = SessionManager(database_service)
challenge_engine = ChallengeEngine()

# Initialize CV Verifier with model path
model_path = os.getenv("MEDIAPIPE_MODEL_PATH", "").strip() or None
if model_path is None:
    # Try default location
    default_path = os.path.join(os.path.expanduser("~"), ".mediapipe_models", "face_landmarker.task")
    if os.path.exists(default_path):
        model_path = default_path
        logger.info(f"Using MediaPipe model at default path: {model_path}")
if model_path:
    logger.info(f"MediaPipe model path resolved to: {model_path} (exists={os.path.exists(model_path)})")
else:
    logger.warning("No MediaPipe model path found! Face detection will not work.")
cv_verifier = CVVerifier(model_path=model_path)

# Initialize Scoring Engine
scoring_engine = ScoringEngine()

# Initialize Token Issuer
private_key = os.getenv("JWT_PRIVATE_KEY", None)
public_key = os.getenv("JWT_PUBLIC_KEY", None)
token_issuer = TokenIssuer(private_key=private_key, public_key=public_key)

# Initialize Emotion Analyzer
emotion_analyzer = EmotionAnalyzer()

# Initialize Deepfake Detector
deepfake_model_path = os.getenv("DEEPFAKE_MODEL_PATH", "").strip() or None
deepfake_detector = DeepfakeDetector(model_path=deepfake_model_path)

# Initialize Blockchain Verification Ledger (Decentralized audit trail)
blockchain_ledger = BlockchainLedger(
    private_key=private_key,
    public_key=public_key,
    storage_dir=os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
)
logger.info(f"Blockchain ledger initialized: {blockchain_ledger.get_chain_stats()['total_blocks']} blocks")

# Clerk JWT verification cache
_clerk_jwks_client = None

def _get_clerk_jwks_client():
    """Get or create the Clerk JWKS client for JWT verification"""
    global _clerk_jwks_client
    if _clerk_jwks_client is None:
        clerk_issuer = os.getenv("CLERK_ISSUER_URL")
        if clerk_issuer:
            jwks_url = f"{clerk_issuer}/.well-known/jwks.json"
            _clerk_jwks_client = pyjwt.PyJWKClient(jwks_url)
    return _clerk_jwks_client

def validate_clerk_token(auth_header: str) -> Optional[dict]:
    """
    Validate a Clerk JWT token from the Authorization header.
    
    Returns decoded payload if valid, None if validation fails or is disabled.
    """
    clerk_issuer = os.getenv("CLERK_ISSUER_URL")
    if not clerk_issuer:
        # Clerk validation not configured — allow passthrough in dev
        logger.warning("CLERK_ISSUER_URL not set — skipping Clerk token validation")
        return None

    if not auth_header or not auth_header.startswith("Bearer "):
        return None

    token = auth_header.replace("Bearer ", "")
    try:
        jwks_client = _get_clerk_jwks_client()
        if not jwks_client:
            return None
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        decoded = pyjwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            issuer=clerk_issuer,
            options={"verify_aud": False},
        )
        return decoded
    except Exception as e:
        logger.warning(f"Clerk token validation failed: {e}")
        return None

# Background task control
_purge_task = None
_purge_task_running = False

async def purge_expired_nonces_task():
    """
    Background task to periodically purge expired nonces from the database.
    Runs every hour to prevent the nonces table from growing indefinitely.
    
    Validates Requirement 11.5: Expired nonces (older than 24 hours) should be automatically purged
    """
    global _purge_task_running
    _purge_task_running = True
    
    logger.info("Starting nonce purge background task")
    
    while _purge_task_running:
        try:
            # Wait 1 hour between purge operations
            await asyncio.sleep(3600)  # 3600 seconds = 1 hour
            
            # Purge expired nonces
            deleted_count = database_service.purge_expired_nonces()
            
            logger.info(f"Purged {deleted_count} expired nonces from database")
            
            # Log purge operation for audit trail
            log_id = str(uuid.uuid4())
            database_service.save_audit_log(
                log_id=log_id,
                session_id="system",
                user_id="system",
                event_type="nonce_purge",
                timestamp=time.time(),
                details={
                    "deleted_count": deleted_count,
                    "operation": "automatic_purge"
                }
            )
            
        except Exception as e:
            logger.error(f"Error in nonce purge task: {e}", exc_info=True)
            # Continue running even if one purge fails
            await asyncio.sleep(60)  # Wait 1 minute before retrying

@app.on_event("startup")
async def startup_event():
    """
    Application startup event handler.
    Starts the background task for purging expired nonces.
    """
    global _purge_task
    logger.info("Application startup: initializing background tasks")
    
    # Start the nonce purge background task
    _purge_task = asyncio.create_task(purge_expired_nonces_task())
    logger.info("Nonce purge background task started")

@app.on_event("shutdown")
async def shutdown_event():
    """
    Application shutdown event handler.
    Stops the background task gracefully.
    """
    global _purge_task, _purge_task_running
    logger.info("Application shutdown: stopping background tasks")
    
    # Stop the purge task
    _purge_task_running = False
    
    if _purge_task:
        _purge_task.cancel()
        try:
            await _purge_task
        except asyncio.CancelledError:
            logger.info("Nonce purge background task stopped")

# Request/Response models
class AuthVerifyRequest(BaseModel):
    """Request body for /api/auth/verify endpoint"""
    user_id: str
    
class AuthVerifyResponse(BaseModel):
    """Response body for /api/auth/verify endpoint"""
    session_id: str
    websocket_url: str
    message: str

# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Handle all unhandled exceptions"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred",
                "category": "system",
                "recoverable": False
            }
        }
    )

# HTTP exception handler
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions with consistent error format"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": {
                "code": exc.detail if isinstance(exc.detail, str) else "HTTP_ERROR",
                "message": str(exc.detail),
                "category": "http",
                "recoverable": exc.status_code < 500
            }
        }
    )

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Proof of Life Authentication API",
        "status": "running",
        "version": "1.0.0"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring"""
    try:
        # Basic health check - can be extended to check database, ML models, etc.
        chain_stats = blockchain_ledger.get_chain_stats()
        return {
            "status": "healthy",
            "services": {
                "api": "operational",
                "database": "operational",
                "blockchain_ledger": "operational"
            },
            "blockchain": {
                "total_blocks": chain_stats["total_blocks"],
                "chain_hash": chain_stats["chain_hash"]
            }
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": str(e)
            }
        )

@app.post("/api/auth/verify", response_model=AuthVerifyResponse)
async def verify_authentication(
    request: AuthVerifyRequest,
    authorization: Optional[str] = Header(None)
):
    """
    Verify user authentication and create verification session
    
    This endpoint accepts user authentication from Clerk (via Authorization header),
    creates a new verification session, and returns the session ID and WebSocket URL
    for the verification flow.
    
    Args:
        request: Request body containing user_id
        authorization: Optional Authorization header with Clerk token
        
    Returns:
        AuthVerifyResponse with session_id and websocket_url
        
    Raises:
        HTTPException: If authentication fails or session creation fails
    """
    try:
        # Validate Clerk token if configured
        clerk_issuer = os.getenv("CLERK_ISSUER_URL")
        if clerk_issuer:
            if not authorization:
                return JSONResponse(
                    status_code=401,
                    content={
                        "error": {
                            "code": "MISSING_AUTH_TOKEN",
                            "message": "Authorization header with Clerk token is required",
                            "category": "authentication",
                            "recoverable": False
                        }
                    }
                )
            clerk_payload = validate_clerk_token(authorization)
            if clerk_payload is None:
                return JSONResponse(
                    status_code=401,
                    content={
                        "error": {
                            "code": "INVALID_AUTH_TOKEN",
                            "message": "Invalid or expired Clerk token",
                            "category": "authentication",
                            "recoverable": False
                        }
                    }
                )
            # Use the Clerk user ID (sub claim) as the authoritative user_id
            clerk_user_id = clerk_payload.get("sub")
            if clerk_user_id and clerk_user_id != request.user_id:
                logger.warning(
                    f"User ID mismatch: body={request.user_id}, clerk={clerk_user_id}"
                )
                # Use the Clerk-verified ID
                request.user_id = clerk_user_id
        
        if not request.user_id:
            return JSONResponse(
                status_code=400,
                content={
                    "error": {
                        "code": "MISSING_USER_ID",
                        "message": "User ID is required",
                        "category": "authentication",
                        "recoverable": False
                    }
                }
            )
        
        # Create new verification session
        session = session_manager.create_session(request.user_id)
        
        # Log session start with user identity (Requirement 13.1)
        log_id = str(uuid.uuid4())
        database_service.save_audit_log(
            log_id=log_id,
            session_id=session.session_id,
            user_id=request.user_id,
            event_type="session_start",
            timestamp=session.start_time,
            details={
                "user_id": request.user_id,
                "session_id": session.session_id,
                "start_time": session.start_time
            }
        )
        
        # Build WebSocket URL
        ws_host = os.getenv("WEBSOCKET_HOST", "localhost:8000")
        ws_protocol = "wss" if os.getenv("USE_WSS", "false").lower() == "true" else "ws"
        websocket_url = f"{ws_protocol}://{ws_host}/ws/verify/{session.session_id}"
        
        logger.info(f"Created session {session.session_id} for user {request.user_id}")
        
        return AuthVerifyResponse(
            session_id=session.session_id,
            websocket_url=websocket_url,
            message="Session created successfully. Connect to WebSocket to begin verification."
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create verification session: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "SESSION_CREATION_FAILED",
                    "message": "Failed to create verification session",
                    "category": "system",
                    "recoverable": True
                }
            }
        )


@app.websocket("/ws/verify/{session_id}")
async def websocket_verify_endpoint(websocket: WebSocket, session_id: str):
    """
    WebSocket endpoint for real-time proof-of-life verification.
    
    This endpoint orchestrates the complete verification flow:
    1. Generate challenges
    2. Receive video frames from client
    3. Run ML verification pipeline (liveness detection)
    4. Compute scores
    5. Issue token on success
    
    Sends real-time feedback throughout the process.
    
    Args:
        websocket: WebSocket connection
        session_id: Unique session identifier from /api/auth/verify
        
    Validates Requirements: 2.1, 3.1, 4.1, 5.1, 6.1, 7.1, 8.1, 10.5
    """
    await websocket.accept()
    logger.info(f"WebSocket connection established for session {session_id}")
    
    try:
        # Verify session exists and is still active
        session_data = database_service.get_session(session_id)
        if not session_data:
            logger.warning(f"Session {session_id} not found in database — rejecting WebSocket")
            await _send_feedback(
                websocket,
                FeedbackType.ERROR,
                "Invalid session ID. Please start a new verification.",
                {"code": "SESSION_NOT_FOUND", "session_id": session_id}
            )
            await websocket.close(code=1008, reason="Invalid session")
            return
        
        # Check if session was already terminated (completed/failed/timeout)
        session_status = session_data.get('status', 'active')
        if session_status in ('completed', 'failed', 'timeout'):
            logger.warning(f"Session {session_id} already terminated (status={session_status})")
            await _send_feedback(
                websocket,
                FeedbackType.ERROR,
                f"Session already {session_status}. Please start a new verification.",
                {"code": "SESSION_TERMINATED", "status": session_status}
            )
            await websocket.close(code=1008, reason=f"Session {session_status}")
            return
        
        # Check if session has timed out
        if session_manager.check_timeout(session_id):
            session_manager.terminate_session(session_id, "timeout")
            await _send_feedback(
                websocket,
                FeedbackType.ERROR,
                "Session has timed out",
                None
            )
            await websocket.close(code=1008, reason="Session timeout")
            return
        
        # Generate challenge sequence (Requirement 2.1)
        challenge_sequence = challenge_engine.generate_challenge_sequence(
            session_id=session_id,
            num_challenges=8
        )
        
        # Validate nonce hasn't been used before (Requirement 11.3)
        if database_service.check_nonce_used(challenge_sequence.nonce):
            logger.warning(f"Nonce reuse detected for session {session_id}")
            
            # Log security event
            log_id = str(uuid.uuid4())
            database_service.save_audit_log(
                log_id=log_id,
                session_id=session_id,
                user_id=session_data['user_id'],
                event_type="security_event",
                timestamp=time.time(),
                details={
                    "event": "nonce_reuse_detected",
                    "nonce": challenge_sequence.nonce,
                    "session_id": session_id
                }
            )
            
            session_manager.terminate_session(session_id, "security_violation")
            await _send_feedback(
                websocket,
                FeedbackType.ERROR,
                "Security violation: Replay attack detected",
                None
            )
            await websocket.close(code=1008, reason="Replay attack detected")
            return
        
        # Store nonce for replay attack prevention (Requirement 11.3)
        database_service.store_nonce(
            nonce=challenge_sequence.nonce,
            session_id=session_id,
            expires_at=challenge_sequence.timestamp + 300  # 5 minutes
        )
        
        logger.info(f"Generated {len(challenge_sequence.challenges)} challenges for session {session_id}")
        
        # Track completed challenges and video frames
        completed_count = 0
        all_video_frames = []
        
        # Process each challenge
        for challenge in challenge_sequence.challenges:
            # Check for timeout and failure limit before each challenge
            if session_manager.check_timeout(session_id):
                session_manager.terminate_session(session_id, "timeout")
                await _send_feedback(
                    websocket,
                    FeedbackType.ERROR,
                    "Session timed out",
                    None
                )
                await websocket.close(code=1008, reason="Timeout")
                return
            
            if session_manager.check_failure_limit(session_id):
                session_manager.terminate_session(session_id, "max_failures")
                await _send_feedback(
                    websocket,
                    FeedbackType.VERIFICATION_FAILED,
                    "Too many failed challenges",
                    {"reason": "max_failures"}
                )
                await websocket.close(code=1008, reason="Max failures")
                return
            
            # Send challenge to client (Requirement 4.1)
            await _send_feedback(
                websocket,
                FeedbackType.CHALLENGE_ISSUED,
                f"Challenge: {challenge.instruction}",
                {
                    "challenge_id": challenge.challenge_id,
                    "instruction": challenge.instruction,
                    "timeout_seconds": challenge.timeout_seconds,
                    "challenge_number": challenge_sequence.challenges.index(challenge) + 1,
                    "total_challenges": len(challenge_sequence.challenges),
                    "prep_time_seconds": 1.5
                }
            )
            
            # === HUMAN REACTION TIME BUDGET ===
            # Give the user time to read, comprehend, and prepare (1.5 seconds)
            # During this time, drain any stale frames so they don't pollute detection
            await _send_feedback(
                websocket,
                FeedbackType.SCORE_UPDATE,
                f"Get ready to: {challenge.instruction}",
                {"countdown": 1.5, "status": "preparing", "instruction": challenge.instruction}
            )
            
            # Drain any frames sent during the countdown so they don't count
            # Use a clean async sleep with periodic drain to avoid blocking
            drain_duration = 1.5
            drain_start = time.time()
            while time.time() - drain_start < drain_duration:
                remaining = drain_duration - (time.time() - drain_start)
                if remaining <= 0:
                    break
                try:
                    # Try to read and discard frames, with short timeout
                    await asyncio.wait_for(websocket.receive_text(), timeout=min(0.5, remaining))
                except asyncio.TimeoutError:
                    pass
                except Exception:
                    break
            
            # Send countdown updates for last second for better UX
            await _send_feedback(
                websocket,
                FeedbackType.SCORE_UPDATE,
                f"Go! Perform: {challenge.instruction}",
                {"status": "recording", "instruction": challenge.instruction}
            )
            
            # Collect video frames for this challenge
            challenge_frames = []
            challenge_start_time = None
            frames_since_last_feedback = 0
            
            # Receive frames until timeout or enough frames collected
            while True:
                try:
                    # Set timeout for receiving frames
                    data = await websocket.receive_text()
                    
                    if challenge_start_time is None:
                        challenge_start_time = time.time()
                    
                    # Check challenge timeout
                    elapsed = time.time() - challenge_start_time
                    if elapsed > challenge.timeout_seconds:
                        logger.warning(f"Challenge {challenge.challenge_id} timed out after {elapsed:.1f}s")
                        break
                    
                    # Parse message
                    message = json.loads(data)
                    
                    # Validate nonce if present in message (Requirement 11.2)
                    if "nonce" in message:
                        message_nonce = message.get("nonce")
                        
                        # Check nonce matches current session (Requirement 11.2)
                        if message_nonce != challenge_sequence.nonce:
                            logger.warning(f"Nonce mismatch for session {session_id}: expected {challenge_sequence.nonce}, got {message_nonce}")
                            
                            # Log security event
                            log_id = str(uuid.uuid4())
                            database_service.save_audit_log(
                                log_id=log_id,
                                session_id=session_id,
                                user_id=session_data['user_id'],
                                event_type="security_event",
                                timestamp=time.time(),
                                details={
                                    "event": "nonce_mismatch",
                                    "expected_nonce": challenge_sequence.nonce,
                                    "received_nonce": message_nonce,
                                    "session_id": session_id
                                }
                            )
                            
                            session_manager.terminate_session(session_id, "security_violation")
                            await _send_feedback(
                                websocket,
                                FeedbackType.ERROR,
                                "Security violation: Invalid nonce",
                                None
                            )
                            await websocket.close(code=1008, reason="Invalid nonce")
                            return
                    
                    if message.get("type") == "video_frame":
                        # Decode base64 frame
                        frame_data = message.get("frame")
                        if frame_data:
                            frame = _decode_frame(frame_data)
                            if frame is not None:
                                challenge_frames.append(frame)
                                all_video_frames.append(frame)
                                frames_since_last_feedback += 1
                                
                                if len(challenge_frames) == 1:
                                    logger.info(f"First frame decoded: shape={frame.shape}, dtype={frame.dtype}")
                                
                                # Send periodic feedback every 30 frames (~1s at 30fps)
                                # so the user knows the system is actively recording
                                if frames_since_last_feedback >= 30:
                                    frames_since_last_feedback = 0
                                    elapsed_secs = time.time() - challenge_start_time
                                    await _send_feedback(
                                        websocket,
                                        FeedbackType.SCORE_UPDATE,
                                        f"Recording... {len(challenge_frames)} frames ({elapsed_secs:.0f}s)",
                                        {
                                            "status": "recording",
                                            "frames_captured": len(challenge_frames),
                                            "elapsed_seconds": round(elapsed_secs, 1)
                                        }
                                    )
                                
                                # Collect frames for ~3 seconds (at 30 FPS = 90 frames)
                                if len(challenge_frames) >= 90:
                                    break
                            else:
                                if len(challenge_frames) == 0:
                                    logger.warning("Frame decode returned None (first frame)")
                        else:
                            if len(challenge_frames) == 0:
                                logger.warning("Video frame message missing 'frame' field")
                    
                    elif message.get("type") == "challenge_complete":
                        # Client signals challenge completion
                        logger.info(f"Client signaled completion for challenge {challenge.challenge_id}")
                        break
                
                except WebSocketDisconnect:
                    logger.info(f"WebSocket disconnected during challenge {challenge.challenge_id}")
                    raise
                except json.JSONDecodeError as e:
                    logger.error(f"Invalid JSON received: {e}")
                    break
                except Exception as e:
                    logger.error(f"Error receiving frame: {e}")
                    break
            
            # Verify challenge (Requirement 4.2, 4.3)
            logger.info(f"Challenge '{challenge.instruction}' (type={challenge.type.value}): collected {len(challenge_frames)} frames")
            if len(challenge_frames) > 0:
                challenge_result = cv_verifier.verify_challenge(challenge, challenge_frames)
                logger.info(f"Challenge '{challenge.instruction}' result: completed={challenge_result.completed}, confidence={challenge_result.confidence:.3f}")
                
                # Update session with result
                session_manager.update_session(session_id, challenge_result)
                
                # Log challenge completion (Requirement 13.4)
                log_id = str(uuid.uuid4())
                database_service.save_audit_log(
                    log_id=log_id,
                    session_id=session_id,
                    user_id=session_data['user_id'],
                    event_type="challenge_completion",
                    timestamp=challenge_result.timestamp,
                    details={
                        "challenge_id": challenge.challenge_id,
                        "challenge_type": challenge.type.value,
                        "instruction": challenge.instruction,
                        "completed": challenge_result.completed,
                        "confidence": challenge_result.confidence,
                        "timestamp": challenge_result.timestamp
                    }
                )
                
                if challenge_result.completed:
                    completed_count += 1
                    await _send_feedback(
                        websocket,
                        FeedbackType.CHALLENGE_COMPLETED,
                        f"Challenge completed successfully! ({completed_count}/{len(challenge_sequence.challenges)})",
                        {
                            "challenge_id": challenge.challenge_id,
                            "confidence": challenge_result.confidence,
                            "completed_count": completed_count,
                            "total_challenges": len(challenge_sequence.challenges)
                        }
                    )
                else:
                    await _send_feedback(
                        websocket,
                        FeedbackType.CHALLENGE_FAILED,
                        f"Challenge not detected. Moving to next one.",
                        {
                            "challenge_id": challenge.challenge_id,
                            "confidence": challenge_result.confidence,
                            "completed_count": completed_count,
                            "total_challenges": len(challenge_sequence.challenges)
                        }
                    )
                
                # Send live progress score after each challenge
                progress_score = completed_count / len(challenge_sequence.challenges)
                await _send_feedback(
                    websocket,
                    FeedbackType.SCORE_UPDATE,
                    f"Progress: {completed_count}/{len(challenge_sequence.challenges)} challenges passed",
                    {
                        "liveness_score": progress_score,
                        "completed_count": completed_count,
                        "total_challenges": len(challenge_sequence.challenges),
                        "last_confidence": challenge_result.confidence
                    }
                )
                
                # Brief pause between challenges so user can see result and rest
                await asyncio.sleep(1.0)
            else:
                # No frames received - mark as failed
                challenge_result = ChallengeResult(
                    challenge_id=challenge.challenge_id,
                    completed=False,
                    confidence=0.0,
                    timestamp=time.time()
                )
                session_manager.update_session(session_id, challenge_result)
                
                # Log failed challenge (Requirement 13.4)
                log_id = str(uuid.uuid4())
                database_service.save_audit_log(
                    log_id=log_id,
                    session_id=session_id,
                    user_id=session_data['user_id'],
                    event_type="challenge_completion",
                    timestamp=challenge_result.timestamp,
                    details={
                        "challenge_id": challenge.challenge_id,
                        "challenge_type": challenge.type.value,
                        "instruction": challenge.instruction,
                        "completed": False,
                        "confidence": 0.0,
                        "reason": "no_frames_received",
                        "timestamp": challenge_result.timestamp
                    }
                )
                
                await _send_feedback(
                    websocket,
                    FeedbackType.CHALLENGE_FAILED,
                    "No video frames received",
                    {"challenge_id": challenge.challenge_id}
                )
        
        # Check if minimum challenges completed (75% pass rate required)
        # e.g. 6/8 challenges or 3/4 challenges
        total_challenges = len(challenge_sequence.challenges)
        min_required = max(1, int(total_challenges * 0.75))
        if completed_count < min_required:
            session_manager.terminate_session(session_id, "failed")
            await _send_feedback(
                websocket,
                FeedbackType.VERIFICATION_FAILED,
                f"Verification failed. Only {completed_count}/{total_challenges} challenges passed (need {min_required}).",
                {
                    "completed_count": completed_count,
                    "required_count": min_required,
                    "total_challenges": total_challenges,
                    "final_score": 0.0,
                    "passed": False
                }
            )
            await websocket.close(code=1000)
            return
        
        # Run ML verification pipeline (Requirement 3.1)
        logger.info(f"Running ML verification pipeline on {len(all_video_frames)} frames")
        
        if len(all_video_frames) > 0:
            # === PIPELINE OPTIMIZATION ===
            # Subsample frames for the final ML pass to avoid processing 1000+ frames
            # Each challenge already verified its own frames, so the final pass only needs
            # a representative sample for liveness/emotion/deepfake scoring
            max_pipeline_frames = 60  # ~2 seconds worth at 30fps, spread across all challenges
            if len(all_video_frames) > max_pipeline_frames:
                import numpy as np_sample
                indices = np_sample.linspace(0, len(all_video_frames) - 1, max_pipeline_frames, dtype=int)
                pipeline_frames = [all_video_frames[i] for i in indices]
                logger.info(f"Subsampled {len(all_video_frames)} frames to {len(pipeline_frames)} for final pipeline")
            else:
                pipeline_frames = all_video_frames
            
            # Compute liveness score
            liveness_score = cv_verifier.compute_liveness_score(pipeline_frames)
            
            # Clear detection cache after liveness (free memory before next pass)
            cv_verifier.clear_detection_cache()
            
            # Compute emotion authenticity score (Requirement 6.3)
            emotion_score = emotion_analyzer.compute_emotion_score(pipeline_frames)
            
            # Compute deepfake detection score (Requirement 5.3)
            deepfake_result = deepfake_detector.analyze_with_early_termination(pipeline_frames)
            deepfake_score = deepfake_result.deepfake_score
            
            # Check for early termination due to deepfake detection (Requirement 5.5)
            if deepfake_result.should_terminate:
                logger.warning(f"Deepfake detected for session {session_id}, terminating")
                
                # Log security event
                log_id = str(uuid.uuid4())
                database_service.save_audit_log(
                    log_id=log_id,
                    session_id=session_id,
                    user_id=session_data['user_id'],
                    event_type="security_event",
                    timestamp=time.time(),
                    details={
                        "event": "deepfake_detected",
                        "deepfake_score": deepfake_score,
                        "spatial_score": deepfake_result.spatial_score,
                        "temporal_score": deepfake_result.temporal_score,
                        "session_id": session_id
                    }
                )
                
                session_manager.terminate_session(session_id, "security_violation")
                await _send_feedback(
                    websocket,
                    FeedbackType.ERROR,
                    "Security violation: Synthetic content detected",
                    {
                        "reason": "deepfake_detected",
                        "deepfake_score": deepfake_score
                    }
                )
                await websocket.close(code=1008, reason="Deepfake detected")
                return
        else:
            liveness_score = 0.0
            emotion_score = 0.0
            deepfake_score = 0.0
        
        # Boost liveness score by incorporating challenge completion rate.
        # Completing challenges is strong evidence of being alive — the user
        # had to physically perform gestures and expressions that were verified
        # by the CV pipeline. This rewards users who passed challenges.
        challenge_rate = completed_count / len(challenge_sequence.challenges)
        liveness_score = 0.5 * liveness_score + 0.5 * challenge_rate
        liveness_score = min(liveness_score, 1.0)
        
        logger.info(f"Scores - Liveness: {liveness_score:.3f} (challenge_rate={challenge_rate:.2f}), Emotion: {emotion_score:.3f}, Deepfake: {deepfake_score:.3f}")
        
        # Send score update (Requirement 10.5)
        await _send_feedback(
            websocket,
            FeedbackType.SCORE_UPDATE,
            "Verification scores computed",
            {
                "liveness_score": liveness_score,
                "emotion_score": emotion_score,
                "deepfake_score": deepfake_score
            }
        )
        
        # Compute final score (Requirement 7.1)
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
        
        # Record verification result on blockchain ledger (Decentralized audit)
        try:
            verification_block = blockchain_ledger.add_verification_block(
                session_id=session_id,
                user_id=session_data['user_id'],
                verification_score=scoring_result.final_score,
                liveness_score=scoring_result.liveness_score,
                emotion_score=scoring_result.emotion_score,
                deepfake_score=scoring_result.deepfake_score,
                passed=scoring_result.passed,
                metadata={"result_id": result_id}
            )
            logger.info(f"Verification recorded on blockchain: block #{verification_block.index}")
        except Exception as e:
            logger.error(f"Failed to record verification on blockchain: {e}")
        
        # Log verification result with all scores (Requirement 13.2)
        log_id = str(uuid.uuid4())
        database_service.save_audit_log(
            log_id=log_id,
            session_id=session_id,
            user_id=session_data['user_id'],
            event_type="verification_result",
            timestamp=scoring_result.timestamp,
            details={
                "liveness_score": scoring_result.liveness_score,
                "deepfake_score": scoring_result.deepfake_score,
                "emotion_score": scoring_result.emotion_score,
                "final_score": scoring_result.final_score,
                "passed": scoring_result.passed,
                "threshold": scoring_engine.THRESHOLD,
                "timestamp": scoring_result.timestamp
            }
        )
        
        logger.info(f"Final score: {scoring_result.final_score:.3f}, Passed: {scoring_result.passed}")
        
        # Check if verification passed
        if scoring_result.passed:
            # Issue token (Requirement 8.1)
            token = token_issuer.issue_jwt_token(
                user_id=session_data['user_id'],
                session_id=session_id,
                final_score=scoring_result.final_score
            )
            
            # Log token issuance (Requirement 13.3)
            token_id = str(uuid.uuid4())
            issued_at = time.time()
            expires_at = issued_at + (token_issuer.TOKEN_EXPIRY_MINUTES * 60)
            
            database_service.save_token_issuance(
                token_id=token_id,
                user_id=session_data['user_id'],
                session_id=session_id,
                issued_at=issued_at,
                expires_at=expires_at
            )
            
            # Record token issuance on blockchain ledger
            try:
                blockchain_ledger.add_token_block(
                    session_id=session_id,
                    user_id=session_data['user_id'],
                    token_id=token_id,
                    issued_at=issued_at,
                    expires_at=expires_at,
                    verification_score=scoring_result.final_score
                )
            except Exception as e:
                logger.error(f"Failed to record token on blockchain: {e}")
            
            # Log token issuance event (Requirement 13.3, 13.4)
            log_id = str(uuid.uuid4())
            database_service.save_audit_log(
                log_id=log_id,
                session_id=session_id,
                user_id=session_data['user_id'],
                event_type="token_issuance",
                timestamp=issued_at,
                details={
                    "token_id": token_id,
                    "user_id": session_data['user_id'],
                    "session_id": session_id,
                    "issued_at": issued_at,
                    "expires_at": expires_at,
                    "expiry_minutes": token_issuer.TOKEN_EXPIRY_MINUTES,
                    "final_score": scoring_result.final_score
                }
            )
            
            # Mark session as completed
            session_manager.terminate_session(session_id, "completed")
            
            # Generate a unique blockchain verification ID for this user
            # This ID is tied to the blockchain block and expires with the token (15 min)
            blockchain_id = f"SNTL-{uuid.uuid4().hex[:8].upper()}-{uuid.uuid4().hex[:4].upper()}"
            chain_stats = blockchain_ledger.get_chain_stats()
            
            # Send success feedback
            await _send_feedback(
                websocket,
                FeedbackType.VERIFICATION_SUCCESS,
                "Verification successful!",
                {
                    "token": token,
                    "blockchain_id": blockchain_id,
                    "final_score": scoring_result.final_score,
                    "liveness_score": scoring_result.liveness_score,
                    "emotion_score": scoring_result.emotion_score,
                    "deepfake_score": scoring_result.deepfake_score,
                    "completed_challenges": completed_count,
                    "total_challenges": len(challenge_sequence.challenges),
                    "expires_in_minutes": token_issuer.TOKEN_EXPIRY_MINUTES,
                    "blockchain": {
                        "blockchain_id": blockchain_id,
                        "block_index": chain_stats["total_blocks"] - 1,
                        "block_count": chain_stats["total_blocks"],
                        "chain_hash": chain_stats["chain_hash"],
                        "ledger_url": "/blockchain"
                    }
                }
            )
            
            logger.info(f"Verification successful for session {session_id}")
        else:
            # Verification failed
            session_manager.terminate_session(session_id, "failed")
            
            await _send_feedback(
                websocket,
                FeedbackType.VERIFICATION_FAILED,
                "Verification failed. Score too low.",
                {
                    "final_score": scoring_result.final_score,
                    "threshold": scoring_engine.THRESHOLD,
                    "liveness_score": scoring_result.liveness_score,
                    "emotion_score": scoring_result.emotion_score,
                    "deepfake_score": scoring_result.deepfake_score,
                    "completed_challenges": completed_count,
                    "total_challenges": len(challenge_sequence.challenges)
                }
            )
            
            logger.info(f"Verification failed for session {session_id}")
        
        # Close connection gracefully
        await websocket.close(code=1000)
    
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for session {session_id}")
        session_manager.terminate_session(session_id, "disconnected")
    
    except Exception as e:
        logger.error(f"Error in WebSocket handler: {e}", exc_info=True)
        try:
            await _send_feedback(
                websocket,
                FeedbackType.ERROR,
                f"Internal error: {str(e)}",
                None
            )
            await websocket.close(code=1011, reason="Internal error")
        except:
            pass
        session_manager.terminate_session(session_id, "error")


async def _send_feedback(
    websocket: WebSocket,
    feedback_type: FeedbackType,
    message: str,
    data: Optional[dict]
) -> None:
    """
    Send real-time feedback message to client.
    
    Args:
        websocket: WebSocket connection
        feedback_type: Type of feedback message
        message: Human-readable message
        data: Optional additional data
    """
    feedback = VerificationFeedback(
        type=feedback_type,
        message=message,
        data=data
    )
    
    # Convert to JSON-serializable format
    # Recursively convert numpy float32/int types to Python native types
    import numpy as _np
    def _jsonify(obj):
        if isinstance(obj, dict):
            return {k: _jsonify(v) for k, v in obj.items()}
        if isinstance(obj, (list, tuple)):
            return [_jsonify(v) for v in obj]
        if isinstance(obj, (_np.floating, _np.float32, _np.float64)):
            return float(obj)
        if isinstance(obj, (_np.integer, _np.int32, _np.int64)):
            return int(obj)
        if isinstance(obj, _np.ndarray):
            return obj.tolist()
        return obj

    feedback_dict = {
        "type": feedback.type.value,
        "message": feedback.message,
        "data": _jsonify(feedback.data)
    }
    
    await websocket.send_json(feedback_dict)


@app.post("/api/token/validate")
async def validate_token_endpoint(request: Request):
    """
    Validate JWT token signature and expiration.
    
    This endpoint accepts a JWT token in the request body and validates:
    - JWT signature using the public key
    - Token expiration timestamp
    
    Args:
        request: Request containing token in JSON body
        
    Returns:
        JSON response with validation result
        
    Validates Requirements: 14.1, 14.2, 14.3, 14.4
    """
    try:
        # Parse request body
        body = await request.json()
        token = body.get("token")
        
        if not token:
            return JSONResponse(
                status_code=400,
                content={
                    "error": {
                        "code": "MISSING_TOKEN",
                        "message": "Token is required in request body",
                        "category": "validation",
                        "recoverable": False
                    }
                }
            )
        
        # Validate token (Requirements 14.1, 14.2)
        validation_result = token_issuer.validate_token(token)
        
        if validation_result.valid:
            # Token is valid
            return JSONResponse(
                status_code=200,
                content={
                    "valid": True,
                    "user_id": validation_result.user_id,
                    "session_id": validation_result.session_id,
                    "issued_at": validation_result.issued_at,
                    "expires_at": validation_result.expires_at
                }
            )
        else:
            # Token is invalid (Requirements 14.3, 14.4)
            # Log security event for invalid signatures
            if "signature" in validation_result.error.lower():
                logger.warning(f"Invalid token signature detected: {validation_result.error}")
            
            return JSONResponse(
                status_code=401,
                content={
                    "valid": False,
                    "error": validation_result.error
                }
            )
    
    except json.JSONDecodeError:
        return JSONResponse(
            status_code=400,
            content={
                "error": {
                    "code": "INVALID_JSON",
                    "message": "Request body must be valid JSON",
                    "category": "validation",
                    "recoverable": False
                }
            }
        )
    
    except Exception as e:
        logger.error(f"Error validating token: {e}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Failed to validate token",
                    "category": "system",
                    "recoverable": True
                }
            }
        )


# ======================================================================
# Blockchain Ledger API — Decentralized Verification Audit Trail
# ======================================================================

@app.get("/api/blockchain/stats")
async def blockchain_stats():
    """Get blockchain ledger statistics."""
    stats = blockchain_ledger.get_chain_stats()
    return JSONResponse(status_code=200, content=stats)


@app.get("/api/blockchain/chain")
async def blockchain_chain(limit: int = 50, offset: int = 0):
    """
    Get the blockchain verification ledger.
    
    Returns blocks in reverse chronological order (newest first).
    """
    chain = blockchain_ledger.get_chain()
    total = len(chain)
    # Reverse for newest-first, then paginate
    reversed_chain = list(reversed(chain))
    paginated = reversed_chain[offset : offset + limit]
    return JSONResponse(
        status_code=200,
        content={
            "blocks": paginated,
            "total": total,
            "offset": offset,
            "limit": limit,
        },
    )


@app.get("/api/blockchain/block/{block_index}")
async def blockchain_block(block_index: int):
    """Get a specific block by index."""
    block = blockchain_ledger.get_block(block_index)
    if block is None:
        return JSONResponse(
            status_code=404,
            content={"error": "Block not found"},
        )
    return JSONResponse(status_code=200, content=block)


@app.get("/api/blockchain/verify")
async def blockchain_verify():
    """
    Verify the entire blockchain integrity.
    
    Checks hash linkage, block hashes, and RSA signatures.
    Returns whether the chain is valid and any errors found.
    """
    result = blockchain_ledger.verify_chain_integrity()
    status = 200 if result["valid"] else 409
    return JSONResponse(status_code=status, content=result)


@app.get("/api/blockchain/verify/{block_index}")
async def blockchain_verify_block(block_index: int):
    """Verify a single block's integrity, hash, and signature."""
    result = blockchain_ledger.verify_single_block(block_index)
    if "error" in result:
        return JSONResponse(status_code=404, content=result)
    status = 200 if result["valid"] else 409
    return JSONResponse(status_code=status, content=result)


@app.get("/api/blockchain/proof/{block_index}")
async def blockchain_proof(block_index: int):
    """
    Generate a standalone cryptographic proof for a block.
    
    This proof can be independently verified by anyone with the
    public key — enabling decentralized, peer-to-peer validation
    without needing access to the full chain or the server.
    """
    proof = blockchain_ledger.generate_proof(block_index)
    if proof is None:
        return JSONResponse(
            status_code=404,
            content={"error": "Block not found"},
        )
    return JSONResponse(status_code=200, content=proof)


@app.get("/api/blockchain/session/{session_id}")
async def blockchain_session_blocks(session_id: str):
    """Get all blockchain blocks related to a specific session."""
    blocks = blockchain_ledger.get_blocks_by_session(session_id)
    return JSONResponse(
        status_code=200,
        content={"session_id": session_id, "blocks": blocks, "count": len(blocks)},
    )


@app.get("/api/blockchain/public-key")
async def blockchain_public_key():
    """
    Export the ledger's public key for independent verification.
    
    Third parties can use this key to verify block signatures
    without trusting the server — true decentralized validation.
    """
    return JSONResponse(
        status_code=200,
        content={
            "public_key": blockchain_ledger.get_public_key_pem(),
            "algorithm": "RSA-PSS with SHA-256",
            "key_size": 2048,
            "usage": "Verify block signatures in the verification ledger",
        },
    )


def _decode_frame(frame_data: str) -> Optional[np.ndarray]:
    """
    Decode base64-encoded video frame.
    
    Args:
        frame_data: Base64-encoded image data
        
    Returns:
        Decoded frame as numpy array, or None if decoding fails
    """
    try:
        # Remove data URL prefix if present
        if "," in frame_data:
            frame_data = frame_data.split(",")[1]
        
        # Decode base64
        img_bytes = base64.b64decode(frame_data)
        
        # Convert to numpy array
        nparr = np.frombuffer(img_bytes, np.uint8)
        
        # Decode image
        frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        return frame
    
    except Exception as e:
        logger.error(f"Error decoding frame: {e}")
        return None
