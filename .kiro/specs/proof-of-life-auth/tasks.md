# Implementation Plan: Multi-Factor Proof of Life Authentication System

## Overview

This implementation plan breaks down the Proof of Life authentication system into incremental coding tasks. The approach prioritizes critical functionality (liveness detection, challenge verification) while treating optional features (blockchain, advanced anti-spoof) as stretch goals. Each task builds on previous work, with property-based tests integrated early to catch errors during development.

**Tech Stack:**
- Backend: Python + FastAPI + WebSockets + SQLite
- Frontend: TypeScript + Next.js + WebRTC + Clerk Auth
- ML Layer: MediaPipe FaceMesh + OpenCV + DeepFace
- Testing: pytest + hypothesis (backend), vitest + fast-check (frontend)

## Tasks

- [x] 1. Set up project structure and development environment
  - Create backend directory with FastAPI project structure
  - Create frontend directory with Next.js project structure
  - Set up Python virtual environment and install dependencies (fastapi, uvicorn, opencv-python, mediapipe, deepface, pyjwt, websockets, sqlite3, hypothesis, pytest)
  - Set up Node.js project and install dependencies (next, react, clerk, tailwindcss, fast-check, vitest)
  - Create database schema SQL file
  - Set up environment variables for JWT keys and configuration
  - _Requirements: All (foundational)_

- [x] 2. Implement database service and session management
  - [x] 2.1 Create DatabaseService class with SQLite connection
    - Implement database initialization with schema creation
    - Implement session CRUD operations (create, read, update)
    - Implement nonce storage and lookup methods
    - Implement audit log storage methods
    - _Requirements: 13.1, 13.2, 13.3, 13.4, 11.3_
  
  - [x] 2.2 Write property test for session persistence
    - **Property 14: Session Start Timestamp**
    - **Validates: Requirements 9.1, 13.1**
  
  - [x] 2.3 Write property test for nonce storage
    - **Property 17: Nonce Storage and Validation**
    - **Validates: Requirements 11.2, 11.3**
  
  - [x] 2.4 Create SessionManager class
    - Implement create_session method with unique ID generation
    - Implement session timeout checking (2 minutes max)
    - Implement challenge failure tracking (3 max consecutive)
    - Implement session termination with reason logging
    - _Requirements: 1.2, 9.1, 9.4, 9.5_
  
  - [x] 2.5 Write property test for unique session generation
    - **Property 1: Unique Session Generation**
    - **Validates: Requirements 1.2**
  
  - [x] 2.6 Write unit tests for session timeout scenarios
    - Test 2-minute session timeout enforcement
    - Test 3 consecutive failure termination
    - _Requirements: 9.4, 9.5_

- [x] 3. Implement challenge generation engine
  - [x] 3.1 Create ChallengeEngine class with gesture and expression pools
    - Define gesture pool with at least 10 types (nod_up, nod_down, turn_left, turn_right, tilt_left, tilt_right, open_mouth, close_eyes, raise_eyebrows, blink)
    - Define expression pool with at least 5 types (smile, frown, surprised, neutral, angry)
    - Implement cryptographic nonce generation using secrets module
    - _Requirements: 2.2, 2.3, 11.1_
  
  - [x] 3.2 Write unit tests for challenge pools
    - Test gesture pool contains at least 10 distinct types
    - Test expression pool contains at least 5 distinct types
    - _Requirements: 2.2, 2.3_
  
  - [x] 3.3 Implement generate_challenge_sequence method
    - Generate random sequence of 3+ challenges
    - Include timestamp and nonce in sequence
    - Ensure randomization prevents identical consecutive sequences
    - _Requirements: 2.1, 2.4, 2.5_
  
  - [x] 3.4 Write property test for challenge uniqueness
    - **Property 3: Challenge Sequence Uniqueness**
    - **Validates: Requirements 2.4**
  
  - [x] 3.5 Write property test for challenge timestamp presence
    - **Property 4: Challenge Timestamp Presence**
    - **Validates: Requirements 2.5, 11.1**

- [x] 4. Checkpoint - Ensure database and challenge generation tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. Implement computer vision liveness detection
  - [x] 5.1 Create CVVerifier class with MediaPipe FaceMesh initialization
    - Initialize MediaPipe FaceMesh with appropriate confidence thresholds
    - Implement frame preprocessing (resize, color conversion)
    - _Requirements: 3.1_
  
  - [x] 5.2 Implement detect_3d_depth method
    - Extract 468 facial landmarks from frames
    - Calculate depth cues from landmark geometry (nose-to-face ratio, perspective)
    - Return depth score (0.0-1.0)
    - _Requirements: 3.2_
  
  - [x] 5.3 Write unit test for 3D depth detection
    - Test with flat image (should score low)
    - Test with 3D video (should score high)
    - _Requirements: 3.2_
  
  - [x] 5.4 Implement detect_micro_movements method
    - Track landmark positions across frame sequence
    - Detect natural micro-movements (eye blinks, subtle head motion)
    - Return movement score (0.0-1.0)
    - _Requirements: 3.3_
  
  - [x] 5.5 Write unit test for micro-movement detection
    - Test with static frames (should score low)
    - Test with dynamic frames (should score high)
    - _Requirements: 3.3_
  
  - [x] 5.6 Implement compute_liveness_score method
    - Combine depth and movement scores
    - Return final liveness score (0.0-1.0)
    - _Requirements: 3.4_
  
  - [x] 5.7 Write property test for liveness score range
    - **Property 5: Score Range Validity (Liveness)**
    - **Validates: Requirements 3.4**

- [x] 6. Implement gesture and expression verification
  - [x] 6.1 Implement verify_challenge method in CVVerifier
    - For gesture challenges: detect head pose and movement patterns
    - For expression challenges: integrate with emotion analyzer
    - Return ChallengeResult with completion status and confidence
    - Record timestamp on successful completion
    - _Requirements: 4.2, 4.3_
  
  - [x] 6.2 Write property test for challenge completion recording
    - **Property 6: Challenge Completion Recording**
    - **Validates: Requirements 4.3**
  
  - [x] 6.3 Write unit tests for gesture recognition
    - Test each gesture type (nod, turn, tilt, etc.)
    - Test challenge timeout (10 seconds)
    - _Requirements: 4.2, 4.4_

- [x] 7. Implement emotion analysis
  - [x] 7.1 Create EmotionAnalyzer class with DeepFace integration
    - Initialize DeepFace emotion detection
    - Implement detect_emotion method for single frames
    - Return EmotionResult with dominant emotion and confidence
    - _Requirements: 6.1_
  
  - [x] 7.2 Write unit test for emotion detection
    - Test detection of 5 core emotions (happy, sad, surprised, neutral, angry)
    - _Requirements: 6.4_
  
  - [x] 7.3 Implement verify_natural_transitions method
    - Track emotion sequence across frames
    - Detect unnatural instantaneous transitions
    - Penalize rigid or synthetic emotional patterns
    - _Requirements: 6.2, 6.5_
  
  - [x] 7.4 Write unit test for transition analysis
    - Test natural transitions (should score high)
    - Test unnatural transitions (should score low)
    - _Requirements: 6.2, 6.5_
  
  - [x] 7.5 Implement compute_emotion_score method
    - Combine emotion detection and transition analysis
    - Return emotion authenticity score (0.0-1.0)
    - _Requirements: 6.3_
  
  - [x] 7.6 Write property test for emotion score range
    - **Property 5: Score Range Validity (Emotion)**
    - **Validates: Requirements 6.3**
  
  - [x] 7.7 Write property test for expression challenge detection
    - **Property 9: Expression Challenge Detection**
    - **Validates: Requirements 6.1**

- [x] 8. Implement deepfake detection (optional but recommended)
  - [x] 8.1 Create DeepfakeDetector class with model loading
    - Load pre-trained deepfake detection model (or use placeholder)
    - Implement frame preprocessing for model input
    - _Requirements: 5.1_
  
  - [x] 8.2 Implement detect_spatial_artifacts method
    - Analyze frames for GAN fingerprints and compression anomalies
    - Return spatial authenticity score
    - _Requirements: 5.1_
  
  - [x] 8.3 Implement detect_temporal_inconsistencies method
    - Analyze frame-to-frame transitions
    - Detect flickering and discontinuities
    - Return temporal consistency score
    - _Requirements: 5.2_
  
  - [x] 8.4 Write unit test for temporal inconsistency detection
    - Test with consistent frames (should score high)
    - Test with inconsistent frames (should score low)
    - _Requirements: 5.2_
  
  - [x] 8.5 Implement compute_deepfake_score method
    - Combine spatial and temporal analysis
    - Return authenticity score (0.0-1.0)
    - Implement early termination if score < 0.5
    - _Requirements: 5.3, 5.5_
  
  - [x] 8.6 Write property test for deepfake score range
    - **Property 5: Score Range Validity (Deepfake)**
    - **Validates: Requirements 5.3**
  
  - [x] 8.7 Write property test for frame analysis completeness
    - **Property 8: Frame Analysis Completeness**
    - **Validates: Requirements 5.1**
  
  - [x] 8.8 Write unit test for early termination
    - Test that score < 0.5 triggers session termination
    - _Requirements: 5.5_

- [x] 9. Checkpoint - Ensure all ML verification components pass tests
  - Ensure all tests pass, ask the user if questions arise.

- [x] 10. Implement scoring engine
  - [x] 10.1 Create ScoringEngine class with weighted formula
    - Implement compute_final_score method with formula: 0.4 × liveness + 0.3 × deepfake + 0.3 × emotion
    - Implement threshold comparison (0.70)
    - Return ScoringResult with all scores and pass/fail decision
    - _Requirements: 7.1, 7.2, 7.3, 7.4_
  
  - [x] 10.2 Write property test for scoring formula correctness
    - **Property 10: Scoring Formula Correctness**
    - **Validates: Requirements 7.1**
  
  - [x] 10.3 Write property test for threshold-based decision
    - **Property 11: Threshold-Based Verification Decision**
    - **Validates: Requirements 7.2, 7.3, 7.4**
  
  - [x] 10.4 Write unit test for threshold boundary
    - Test score 0.69 fails, 0.70 passes
    - _Requirements: 7.3, 7.4_

- [x] 11. Implement token issuance and validation
  - [x] 11.1 Create TokenIssuer class with JWT generation
    - Generate RSA key pair for signing (or load from environment)
    - Implement issue_jwt_token method
    - Include user_id, session_id, final_score in payload
    - Set expiration to exactly 15 minutes from issuance
    - Sign token with private key
    - _Requirements: 8.1, 8.2, 8.3, 8.4_
  
  - [x] 11.2 Write property test for JWT structure validity
    - **Property 13: JWT Structure Validity**
    - **Validates: Requirements 8.1, 8.2, 8.3, 8.4**
  
  - [x] 11.3 Implement validate_token method
    - Verify JWT signature using public key
    - Check expiration timestamp
    - Return TokenValidation result
    - _Requirements: 14.1, 14.2_
  
  - [x] 11.4 Write property test for JWT signature verification
    - **Property 21: JWT Signature Verification**
    - **Validates: Requirements 14.1, 14.2**
  
  - [x] 11.5 Write unit tests for token validation edge cases
    - Test expired token rejection
    - Test invalid signature rejection
    - Test tampered payload rejection
    - _Requirements: 14.3, 14.4_

- [x] 12. Implement WebSocket handler and real-time communication
  - [x] 12.1 Create WebSocketHandler class with FastAPI WebSocket support
    - Implement handle_connection method for WebSocket lifecycle
    - Implement receive_video_frame method (decode base64 frames)
    - Implement send_challenge method
    - Implement send_feedback method for real-time updates
    - _Requirements: 10.1, 10.2, 10.5_
  
  - [x] 12.2 Write property test for frame transmission
    - **Property 15: Frame Transmission via WebSocket**
    - **Validates: Requirements 10.2**
  
  - [x] 12.3 Write property test for status update propagation
    - **Property 16: Status Update Propagation**
    - **Validates: Requirements 10.5, 12.3**
  
  - [x] 12.4 Write unit test for WebSocket connection drop
    - Test that connection drop terminates session
    - _Requirements: 10.4_

- [x] 13. Implement backend API endpoints
  - [x] 13.1 Create FastAPI application with CORS configuration
    - Set up FastAPI app with middleware
    - Configure CORS for Next.js frontend
    - _Requirements: All (foundational)_
  
  - [x] 13.2 Implement POST /api/auth/verify endpoint
    - Accept user authentication token from Clerk
    - Create session via SessionManager
    - Return session_id and WebSocket connection URL
    - _Requirements: 1.1, 1.2_
  
  - [x] 13.3 Implement WebSocket /ws/verify/{session_id} endpoint
    - Accept WebSocket connection
    - Orchestrate verification flow:
      1. Generate challenges
      2. Receive video frames
      3. Run ML verification pipeline
      4. Compute scores
      5. Issue token on success
    - Send real-time feedback throughout
    - _Requirements: 2.1, 3.1, 4.1, 5.1, 6.1, 7.1, 8.1, 10.5_
  
  - [x] 13.4 Implement POST /api/token/validate endpoint
    - Accept JWT token
    - Validate signature and expiration
    - Return validation result
    - _Requirements: 14.1, 14.2, 14.3, 14.4_
  
  - [x] 13.5 Write integration tests for API endpoints
    - Test authentication flow
    - Test WebSocket verification flow
    - Test token validation flow
    - _Requirements: 1.1, 1.2, 8.1, 14.1_

- [x] 14. Implement audit logging and persistence
  - [x] 14.1 Add audit logging to all verification events
    - Log session start with user identity
    - Log challenge completions
    - Log verification results with all scores
    - Log token issuance
    - _Requirements: 13.1, 13.2, 13.3, 13.4_
  
  - [x] 14.2 Write property test for audit log completeness
    - **Property 12: Audit Log Completeness**
    - **Validates: Requirements 7.5**
  
  - [x] 14.3 Write property test for verification result persistence
    - **Property 18: Verification Result Persistence**
    - **Validates: Requirements 13.2**
  
  - [x] 14.4 Write property test for token issuance logging
    - **Property 19: Token Issuance Logging**
    - **Validates: Requirements 13.3**
  
  - [x] 14.5 Write property test for event timestamp recording
    - **Property 20: Event Timestamp Recording**
    - **Validates: Requirements 13.4**
  
  - [x] 14.6 Write unit test for audit log retention
    - Test logs are retained for at least 90 days
    - _Requirements: 13.5_

- [x] 15. Implement anti-replay attack protection
  - [x] 15.1 Add nonce validation to WebSocket handler
    - Check nonce matches current session
    - Check nonce hasn't been used before
    - Store used nonces with expiration
    - _Requirements: 11.2, 11.3_
  
  - [x] 15.2 Implement nonce expiration and purging
    - Create background task to purge nonces older than 24 hours
    - _Requirements: 11.5_
  
  - [x] 15.3 Write unit test for replay attack prevention
    - Test reused nonce is rejected
    - _Requirements: 11.4_
  
  - [x] 15.4 Write unit test for nonce purging
    - Test expired nonces are removed
    - _Requirements: 11.5_

- [x] 16. Checkpoint - Ensure backend implementation is complete and tested
  - Ensure all tests pass, ask the user if questions arise.

- [x] 17. Implement frontend authentication with Clerk
  - [x] 17.1 Set up Clerk provider in Next.js app
    - Configure Clerk with API keys
    - Wrap app with ClerkProvider
    - Create protected route wrapper
    - _Requirements: 1.1_
  
  - [x] 17.2 Create authentication pages
    - Create sign-in page
    - Create sign-up page
    - Create user profile page
    - _Requirements: 1.1_
  
  - [x] 17.3 Write unit test for authentication flow
    - Test unauthenticated access is blocked
    - Test successful authentication redirects to verification
    - _Requirements: 1.1, 1.3_

- [x] 18. Implement frontend camera and WebRTC
  - [x] 18.1 Create CameraCapture component
    - Request camera permissions
    - Initialize WebRTC MediaStream
    - Display live camera preview
    - Capture frames at 10 FPS
    - _Requirements: 12.2_
  
  - [x] 18.2 Write unit test for camera permission handling
    - Test camera access denied shows error message
    - _Requirements: 15.1_
  
  - [x] 18.3 Implement frame encoding for WebSocket transmission
    - Convert video frames to base64
    - Implement frame rate throttling
    - _Requirements: 10.2_

- [x] 19. Implement frontend WebSocket client
  - [x] 19.1 Create WebSocketClient class
    - Implement connection establishment
    - Implement message sending (video frames)
    - Implement message receiving (challenges, feedback)
    - Implement connection drop handling
    - _Requirements: 10.1, 10.2, 10.4_
  
  - [x] 19.2 Write unit test for WebSocket connection
    - Test connection establishment on session start
    - Test connection drop triggers error
    - _Requirements: 10.1, 10.4_
  
  - [x] 19.3 Write unit test for network failure handling
    - Test network failure shows error and retry option
    - _Requirements: 15.2_

- [x] 20. Implement frontend verification UI
  - [x] 20.1 Create VerificationPage component
    - Display current challenge with instructions
    - Show camera preview
    - Display real-time feedback (challenge progress, scores)
    - Show verification result on completion
    - _Requirements: 12.1, 12.2, 12.3, 12.4_
  
  - [x] 20.2 Create ChallengeDisplay component
    - Render challenge instructions with visual cues
    - Show countdown timer (10 seconds)
    - Animate challenge completion
    - _Requirements: 4.1_
  
  - [x] 20.3 Create FeedbackDisplay component
    - Show real-time status updates
    - Display score indicators
    - Show error messages with recovery options
    - _Requirements: 12.3, 12.5, 15.3_
  
  - [x] 20.4 Write unit tests for UI components
    - Test challenge display shows instructions
    - Test camera preview is visible
    - Test verification result is displayed
    - Test error messages are shown
    - _Requirements: 12.1, 12.2, 12.4, 12.5_

- [x] 21. Implement frontend state management
  - [x] 21.1 Create verification state management (React Context or Zustand)
    - Track session state (idle, active, completed, failed)
    - Track current challenge
    - Track completed challenges count
    - Track current scores
    - _Requirements: 12.3_
  
  - [x] 21.2 Implement verification flow orchestration
    - Start session on user action
    - Handle WebSocket messages and update state
    - Handle verification completion (success/failure)
    - Store received token in secure storage
    - _Requirements: 8.1, 12.3_
  
  - [x] 21.3 Write unit test for state transitions
    - Test state changes during verification flow
    - _Requirements: 12.3_

- [x] 22. Implement error handling and recovery
  - [x] 22.1 Add error handling to all backend components
    - Handle ML model loading failures
    - Handle database connection failures
    - Handle WebSocket errors
    - Log all errors with appropriate severity
    - _Requirements: 15.4_
  
  - [x] 22.2 Write property test for error logging completeness
    - **Property 22: Error Logging Completeness**
    - **Validates: Requirements 15.4**
  
  - [x] 22.3 Add error recovery to frontend
    - Show clear error messages with instructions
    - Provide retry buttons for recoverable errors
    - Implement restart verification flow
    - _Requirements: 15.1, 15.2, 15.3, 15.5_
  
  - [x] 22.4 Write unit tests for error scenarios
    - Test camera access denied error
    - Test network failure error
    - Test verification failure explanation
    - Test restart after failure
    - _Requirements: 15.1, 15.2, 15.3, 15.5_

- [x] 23. Implement remaining property tests
  - [x] 23.1 Write property test for user association invariant
    - **Property 2: User Association Invariant**
    - **Validates: Requirements 1.4**
  
  - [x] 23.2 Write property test for minimum challenge requirement
    - **Property 7: Minimum Challenge Requirement**
    - **Validates: Requirements 4.5**

- [x] 24. Integration and end-to-end testing
  - [x] 24.1 Write integration test for successful verification flow
    - Test complete flow: auth → session → challenges → token
    - Verify token is valid and contains correct data
    - Verify audit logs are created
    - _Requirements: 1.1, 2.1, 4.5, 7.3, 8.1, 13.1_
  
  - [x] 24.2 Write integration test for failed verification flow
    - Test flow with failed challenges
    - Verify no token is issued
    - Verify failure is logged
    - _Requirements: 7.4, 13.2_
  
  - [x] 24.3 Write integration test for timeout scenarios
    - Test challenge timeout
    - Test session timeout
    - _Requirements: 9.2, 9.3, 9.4_
  
  - [x] 24.4 Write integration test for security scenarios
    - Test replay attack rejection
    - Test deepfake detection termination
    - Test invalid token rejection
    - _Requirements: 11.4, 5.5, 14.3, 14.4_

- [x] 25. Final checkpoint - Ensure all tests pass and system is functional
  - Run full test suite (unit + property + integration)
  - Verify all 22 correctness properties are tested
  - Test complete user flow manually
  - Ensure all tests pass, ask the user if questions arise.

- [x] 26. Deployment preparation
  - [x] 26.1 Create production configuration
    - Set up environment variables for production
    - Configure JWT key rotation
    - Set up database backup strategy
    - Configure logging for production
    - _Requirements: All (operational)_
  
  - [x] 26.2 Create deployment scripts
    - Create Dockerfile for backend (FastAPI)
    - Create deployment config for frontend (Vercel)
    - Create database migration scripts
    - _Requirements: All (operational)_
  
  - [x] 26.3 Set up monitoring and alerting
    - Configure error tracking (Sentry or similar)
    - Set up performance monitoring
    - Create alerts for security events (replay attacks, deepfakes)
    - _Requirements: 13.4, 15.4_

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP development
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation at key milestones
- Property tests validate universal correctness properties (100+ iterations each)
- Unit tests validate specific examples, edge cases, and error conditions
- Integration tests validate end-to-end flows and security scenarios
- The implementation prioritizes critical features (liveness, challenges, scoring) over optional features (blockchain, advanced anti-spoof)
- ML model selection for deepfake detection can be adjusted based on performance requirements
- Frontend styling with Tailwind CSS should be added incrementally during UI component development
