# Requirements Document

## Introduction

This document specifies the requirements for integrating the FastAPI backend with the Next.js frontend in the Proof-of-Life Authentication System. The integration enables real-time biometric verification through WebSocket communication, HTTP API endpoints, and proper data flow between the client-side camera capture and server-side ML models (MediaPipe, DeepFace, MesoNet-4).

## Glossary

- **Frontend**: Next.js 14 application with TypeScript running on localhost:3000
- **Backend**: FastAPI Python application running on localhost:8000
- **WebSocket_Connection**: Bidirectional real-time communication channel between Frontend and Backend
- **Session**: A unique verification attempt identified by session_id
- **Challenge**: A specific action the user must perform (e.g., "nod your head", "smile")
- **Video_Frame**: A single image captured from the user's camera, encoded as base64
- **ML_Pipeline**: The sequence of machine learning models that process video frames (MediaPipe for liveness, DeepFace for emotion, MesoNet-4 for deepfake detection)
- **JWT_Token**: JSON Web Token issued upon successful verification
- **Convex**: The database service used for storing sessions, verification results, and audit logs
- **FaceIDScanner**: Frontend React component that displays the verification UI
- **API_Client**: Frontend service module for making HTTP requests to Backend

## Requirements

### Requirement 1: Session Initialization

**User Story:** As a user, I want to start a verification session, so that I can begin the proof-of-life authentication process.

#### Acceptance Criteria

1. WHEN the Frontend requests session creation, THE Backend SHALL create a new Session with a unique session_id
2. WHEN a Session is created, THE Backend SHALL return the session_id and WebSocket_Connection URL to the Frontend
3. WHEN a Session is created, THE Backend SHALL store the Session in Convex with user_id and timestamp
4. WHEN a Session is created, THE Backend SHALL log the session start event in the audit log
5. THE Frontend SHALL send the user_id in the session creation request

### Requirement 2: WebSocket Connection Establishment

**User Story:** As a user, I want my browser to connect to the backend in real-time, so that I can receive immediate feedback during verification.

#### Acceptance Criteria

1. WHEN the Frontend receives a session_id, THE Frontend SHALL establish a WebSocket_Connection to ws://localhost:8000/ws/verify/{session_id}
2. WHEN the WebSocket_Connection is established, THE Backend SHALL validate the session_id exists in Convex
3. IF the session_id is invalid, THEN THE Backend SHALL close the WebSocket_Connection with error code 1008
4. WHEN the WebSocket_Connection is established, THE Backend SHALL check if the Session has timed out
5. IF the Session has timed out, THEN THE Backend SHALL close the WebSocket_Connection with error code 1008

### Requirement 3: Camera Capture and Frame Transmission

**User Story:** As a user, I want my camera to capture video frames, so that the backend can analyze my biometric data.

#### Acceptance Criteria

1. WHEN verification starts, THE Frontend SHALL request camera permissions from the browser
2. WHEN camera access is granted, THE Frontend SHALL capture video frames at 10 frames per second
3. WHEN a frame is captured, THE Frontend SHALL encode it as base64 format
4. WHEN a frame is encoded, THE Frontend SHALL send it to the Backend via WebSocket_Connection with message type "video_frame"
5. WHEN the Backend receives a frame, THE Backend SHALL decode the base64 data into a numpy array for ML processing

### Requirement 4: Challenge Delivery and Display

**User Story:** As a user, I want to see what actions I need to perform, so that I can complete the verification challenges.

#### Acceptance Criteria

1. WHEN the WebSocket_Connection is established, THE Backend SHALL generate a sequence of 3 challenges
2. WHEN a Challenge is generated, THE Backend SHALL send it to the Frontend with message type "CHALLENGE_ISSUED"
3. WHEN the Frontend receives a Challenge, THE Frontend SHALL display the challenge instruction to the user
4. WHEN displaying a Challenge, THE Frontend SHALL show the challenge text prominently in the UI
5. THE Frontend SHALL display a visual indicator that the challenge is active

### Requirement 5: Real-Time Feedback Messages

**User Story:** As a user, I want to receive immediate feedback during verification, so that I know if my actions are being recognized correctly.

#### Acceptance Criteria

1. WHEN the Backend processes a Challenge, THE Backend SHALL send feedback messages via WebSocket_Connection
2. WHEN a Challenge is completed successfully, THE Backend SHALL send a "CHALLENGE_COMPLETED" message with confidence score
3. WHEN a Challenge fails, THE Backend SHALL send a "CHALLENGE_FAILED" message
4. WHEN the Frontend receives feedback, THE Frontend SHALL update the UI to reflect the current status
5. WHEN ML scores are computed, THE Backend SHALL send a "SCORE_UPDATE" message with liveness_score, emotion_score, and deepfake_score

### Requirement 6: ML Score Display

**User Story:** As a user, I want to see my verification scores in real-time, so that I understand how well the system is detecting my biometric data.

#### Acceptance Criteria

1. WHEN the Backend computes liveness_score, THE Backend SHALL send it to the Frontend via "SCORE_UPDATE" message
2. WHEN the Backend computes emotion_score, THE Backend SHALL send it to the Frontend via "SCORE_UPDATE" message
3. WHEN the Backend computes deepfake_score, THE Backend SHALL send it to the Frontend via "SCORE_UPDATE" message
4. WHEN the Frontend receives score updates, THE Frontend SHALL display them as percentage values in the UI
5. WHEN displaying scores, THE Frontend SHALL use visual progress bars or indicators

### Requirement 7: Verification Completion

**User Story:** As a user, I want to know when verification is complete, so that I can proceed with authentication or retry if needed.

#### Acceptance Criteria

1. WHEN all challenges are processed, THE Backend SHALL compute a final_score
2. IF final_score meets the threshold, THEN THE Backend SHALL send a "VERIFICATION_SUCCESS" message with JWT_Token
3. IF final_score does not meet the threshold, THEN THE Backend SHALL send a "VERIFICATION_FAILED" message
4. WHEN the Frontend receives "VERIFICATION_SUCCESS", THE Frontend SHALL store the JWT_Token
5. WHEN the Frontend receives "VERIFICATION_SUCCESS", THE Frontend SHALL display a success UI state
6. WHEN the Frontend receives "VERIFICATION_FAILED", THE Frontend SHALL display a failure UI state with retry option

### Requirement 8: Token Storage and Usage

**User Story:** As a user, I want my authentication token to be stored securely, so that I can access protected resources without re-verifying.

#### Acceptance Criteria

1. WHEN the Frontend receives a JWT_Token, THE Frontend SHALL store it in Convex database
2. WHEN storing the JWT_Token, THE Frontend SHALL associate it with the user_id and session_id
3. THE Frontend SHALL include the JWT_Token in subsequent API requests to protected endpoints
4. WHEN the JWT_Token expires, THE Frontend SHALL prompt the user to re-verify
5. THE Frontend SHALL provide a method to retrieve the current valid JWT_Token

### Requirement 9: Error Handling and Recovery

**User Story:** As a user, I want the system to handle errors gracefully, so that I can understand what went wrong and retry if possible.

#### Acceptance Criteria

1. WHEN the WebSocket_Connection fails, THE Frontend SHALL display an error message to the user
2. WHEN the WebSocket_Connection is lost during verification, THE Frontend SHALL attempt to reconnect once
3. IF reconnection fails, THEN THE Frontend SHALL display an error and offer to restart verification
4. WHEN the Backend encounters an error, THE Backend SHALL send an "ERROR" feedback message with error details
5. WHEN the Frontend receives an error message, THE Frontend SHALL display it in a user-friendly format

### Requirement 10: CORS Configuration

**User Story:** As a developer, I want the backend to accept requests from the frontend, so that cross-origin communication works correctly.

#### Acceptance Criteria

1. THE Backend SHALL configure CORS middleware to allow requests from http://localhost:3000
2. THE Backend SHALL allow credentials in CORS configuration
3. THE Backend SHALL allow all HTTP methods in CORS configuration
4. THE Backend SHALL allow all headers in CORS configuration
5. THE Backend SHALL read allowed origins from the CORS_ORIGINS environment variable

### Requirement 11: Environment Configuration

**User Story:** As a developer, I want to configure API endpoints via environment variables, so that I can easily switch between development and production environments.

#### Acceptance Criteria

1. THE Frontend SHALL read the Backend HTTP URL from NEXT_PUBLIC_API_URL environment variable
2. THE Frontend SHALL read the Backend WebSocket URL from NEXT_PUBLIC_WS_URL environment variable
3. THE Backend SHALL read the frontend origin from CORS_ORIGINS environment variable
4. THE Backend SHALL read the Convex URL from CONVEX_URL environment variable
5. IF environment variables are missing, THEN THE system SHALL use sensible defaults for local development

### Requirement 12: API Client Implementation

**User Story:** As a developer, I want a centralized API client, so that all HTTP requests to the backend are consistent and maintainable.

#### Acceptance Criteria

1. THE Frontend SHALL implement an API_Client module in src/lib/api.ts
2. THE API_Client SHALL provide a method to create verification sessions
3. THE API_Client SHALL provide a method to validate JWT tokens
4. THE API_Client SHALL handle HTTP errors and return structured error responses
5. THE API_Client SHALL use the NEXT_PUBLIC_API_URL for all requests

### Requirement 13: WebSocket Message Protocol

**User Story:** As a developer, I want a well-defined message protocol, so that frontend and backend can communicate reliably.

#### Acceptance Criteria

1. THE Frontend SHALL send messages with a "type" field indicating the message type
2. WHEN sending video frames, THE Frontend SHALL use message type "video_frame" with a "frame" field containing base64 data
3. WHEN signaling challenge completion, THE Frontend SHALL use message type "challenge_complete"
4. THE Backend SHALL send messages with "type", "message", and "data" fields
5. THE Backend SHALL use standardized message types: "CHALLENGE_ISSUED", "CHALLENGE_COMPLETED", "CHALLENGE_FAILED", "SCORE_UPDATE", "VERIFICATION_SUCCESS", "VERIFICATION_FAILED", "ERROR"

### Requirement 14: Progress Tracking

**User Story:** As a user, I want to see my progress through the verification process, so that I know how many challenges remain.

#### Acceptance Criteria

1. WHEN a Challenge is completed, THE Frontend SHALL increment a completed_challenges counter
2. THE Frontend SHALL display the ratio of completed challenges to total challenges
3. THE Frontend SHALL display a progress percentage based on completed challenges
4. WHEN all challenges are completed, THE Frontend SHALL show 100% progress
5. THE Frontend SHALL update progress indicators in real-time as challenges complete

### Requirement 15: Connection Lifecycle Management

**User Story:** As a developer, I want proper connection lifecycle management, so that resources are cleaned up correctly.

#### Acceptance Criteria

1. WHEN the user navigates away from the verification page, THE Frontend SHALL close the WebSocket_Connection
2. WHEN the WebSocket_Connection closes, THE Frontend SHALL clean up camera resources
3. WHEN verification completes, THE Backend SHALL close the WebSocket_Connection gracefully with code 1000
4. WHEN an error occurs, THE Backend SHALL close the WebSocket_Connection with an appropriate error code
5. THE Frontend SHALL remove event listeners when the component unmounts
