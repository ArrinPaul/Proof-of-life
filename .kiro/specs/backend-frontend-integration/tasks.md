# Implementation Plan: Backend-Frontend Integration

## Overview

This implementation plan connects the FastAPI backend with the Next.js frontend for real-time proof-of-life verification. The integration involves creating an API client, implementing WebSocket communication, adding camera capture, and wiring together the complete verification flow with real ML model feedback.

## Tasks

- [ ] 1. Create API Client Module
  - [x] 1.1 Implement API client in frontend/src/lib/api.ts
    - Create APIClient class with createSession and validateToken methods
    - Use fetch API with proper error handling
    - Read base URL from process.env.NEXT_PUBLIC_API_URL
    - Return typed responses using TypeScript interfaces
    - _Requirements: 1.1, 1.2, 12.2, 12.3, 12.4_
  
  - [x] 1.2 Write property test for API client
    - **Property 2: Session creation response structure**
    - **Validates: Requirements 1.2**
  
  - [x] 1.3 Write unit tests for API client error handling
    - Test network errors, 4xx responses, 5xx responses
    - Test JSON parsing errors
    - _Requirements: 12.4_

- [ ] 2. Implement Camera Capture Module
  - [x] 2.1 Create camera capture module in frontend/src/lib/camera.ts
    - Implement CameraCapture class with start, stop, captureFrame methods
    - Use navigator.mediaDevices.getUserMedia for camera access
    - Render video stream to hidden canvas element
    - Capture frames using canvas.toDataURL('image/jpeg', 0.8)
    - Implement frame rate limiting at 10 FPS using setInterval
    - Release media stream on stop
    - _Requirements: 3.1, 3.2, 3.3_
  
  - [x] 2.2 Write property test for frame capture rate
    - **Property 8: Frame capture rate consistency**
    - **Validates: Requirements 3.2**
  
  - [x] 2.3 Write property test for frame encoding
    - **Property 9: Frame encoding validity**
    - **Validates: Requirements 3.3**
  
  - [x] 2.4 Write unit tests for camera error handling
    - Test NotAllowedError (permission denied)
    - Test NotFoundError (no camera)
    - Test cleanup on stop
    - _Requirements: 9.1_

- [ ] 3. Implement WebSocket Client
  - [x] 3.1 Create WebSocket client module in frontend/src/lib/websocket.ts
    - Implement WebSocketClient class with connect, sendFrame, disconnect methods
    - Construct URL from process.env.NEXT_PUBLIC_WS_URL and session_id
    - Send messages as JSON strings with proper structure
    - Parse incoming messages as JSON
    - Implement event handlers for message, error, close
    - Implement single reconnection attempt on unexpected disconnect
    - _Requirements: 2.1, 13.1, 13.2, 13.3, 9.2_
  
  - [x] 3.2 Write property test for WebSocket URL construction
    - **Property 5: WebSocket URL construction**
    - **Validates: Requirements 2.1**
  
  - [x] 3.3 Write property test for message structure
    - **Property 26: Frontend message type field**
    - **Validates: Requirements 13.1**
  
  - [x] 3.4 Write property test for reconnection logic
    - **Property 22: Reconnection attempt limit**
    - **Validates: Requirements 9.2, 9.3**

- [ ] 4. Update FaceIDScanner Component
  - [x] 4.1 Add scores prop to FaceIDScanner component
    - Add scores prop with liveness, emotion, deepfake fields
    - Display scores as percentage values with progress bars
    - Update component to show real-time score updates
    - _Requirements: 6.4, 6.5_
  
  - [x] 4.2 Add current challenge display
    - Show challenge instruction prominently
    - Add visual indicator for active challenge
    - _Requirements: 4.3, 4.4, 4.5_
  
  - [x] 4.3 Write property test for score display formatting
    - **Property 16: Score display formatting**
    - **Validates: Requirements 6.4**

- [x] 5. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 6. Integrate Components in Verification Page
  - [x] 6.1 Update verify-glass page to use real API client
    - Import and use APIClient to create session
    - Store session_id in component state
    - Handle session creation errors
    - _Requirements: 1.1, 1.2, 1.5_
  
  - [x] 6.2 Integrate WebSocket client in verify-glass page
    - Establish WebSocket connection after session creation
    - Set up message handlers for all feedback types
    - Update UI state based on received messages
    - Handle WebSocket errors and disconnections
    - _Requirements: 2.1, 2.2, 5.4, 9.1_
  
  - [x] 6.3 Integrate camera capture in verify-glass page
    - Start camera when verification begins
    - Capture and send frames at 10 FPS via WebSocket
    - Stop camera when verification completes or errors
    - _Requirements: 3.1, 3.2, 3.4_
  
  - [x] 6.4 Write property test for frame message structure
    - **Property 10: Frame message structure**
    - **Validates: Requirements 3.4, 13.2**

- [ ] 7. Implement Challenge Flow
  - [x] 7.1 Handle CHALLENGE_ISSUED messages
    - Update currentChallenge state with instruction
    - Display challenge in UI via FaceIDScanner
    - _Requirements: 4.2, 4.3_
  
  - [x] 7.2 Handle CHALLENGE_COMPLETED messages
    - Increment completedChallenges counter
    - Update progress percentage
    - Show success feedback in UI
    - _Requirements: 5.2, 14.1, 14.3_
  
  - [x] 7.3 Handle CHALLENGE_FAILED messages
    - Show failure feedback in UI
    - Continue to next challenge
    - _Requirements: 5.3_
  
  - [x] 7.4 Write property test for challenge display
    - **Property 13: Challenge display**
    - **Validates: Requirements 4.3**
  
  - [x] 7.5 Write property test for challenge completion counter
    - **Property 29: Challenge completion counter**
    - **Validates: Requirements 14.1**

- [ ] 8. Implement Score Updates
  - [x] 8.1 Handle SCORE_UPDATE messages
    - Extract liveness_score, emotion_score, deepfake_score from message
    - Update scores state
    - Pass scores to FaceIDScanner component
    - _Requirements: 5.5, 6.1, 6.2, 6.3_
  
  - [x] 8.2 Write property test for score update message structure
    - **Property 15: Score update message structure**
    - **Validates: Requirements 5.5, 6.1, 6.2, 6.3**

- [ ] 9. Implement Verification Completion
  - [x] 9.1 Handle VERIFICATION_SUCCESS messages
    - Extract JWT token from message
    - Store token in Convex database
    - Update UI to success state
    - Display final scores
    - _Requirements: 7.2, 7.4, 7.5, 8.1, 8.2_
  
  - [x] 9.2 Handle VERIFICATION_FAILED messages
    - Update UI to error state
    - Display failure message with scores
    - Show retry button
    - _Requirements: 7.3, 7.6_
  
  - [x] 9.3 Write property test for token persistence
    - **Property 19: Token persistence**
    - **Validates: Requirements 7.4, 8.1, 8.2**
  
  - [x] 9.4 Write property test for UI state transitions
    - **Property 20: UI state transitions**
    - **Validates: Requirements 7.5, 7.6**

- [ ] 10. Implement Resource Cleanup
  - [x] 10.1 Add cleanup logic to verify-glass page
    - Close WebSocket connection on component unmount
    - Stop camera capture when WebSocket closes
    - Remove event listeners on unmount
    - _Requirements: 15.1, 15.2, 15.5_
  
  - [x] 10.2 Write property test for WebSocket cleanup
    - **Property 31: WebSocket cleanup on unmount**
    - **Validates: Requirements 15.1**
  
  - [x] 10.3 Write property test for camera cleanup
    - **Property 32: Camera resource cleanup**
    - **Validates: Requirements 15.2**

- [ ] 11. Update Backend CORS Configuration
  - [x] 11.1 Verify CORS configuration in backend/app/main.py
    - Ensure CORS_ORIGINS includes http://localhost:3000
    - Verify allow_credentials is True
    - Verify allow_methods includes all methods
    - Verify allow_headers includes all headers
    - _Requirements: 10.1, 10.2, 10.3, 10.4_
  
  - [x] 11.2 Update backend/.env with frontend origin
    - Add http://localhost:3000 to CORS_ORIGINS if not present
    - _Requirements: 10.5_
  
  - [x] 11.3 Write property test for CORS headers
    - **Property 24: CORS origin validation**
    - **Validates: Requirements 10.1, 10.5**

- [-] 12. Checkpoint - Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 13. Integration Testing
  - [x] 13.1 Write integration test for complete verification flow
    - Test session creation → WebSocket connection → frame transmission → challenge completion → token issuance
    - Mock camera and WebSocket for controlled testing
    - _Requirements: 1.1, 2.1, 3.4, 4.2, 5.2, 7.2_
  
  - [x] 13.2 Write integration test for error scenarios
    - Test invalid session_id rejection
    - Test timeout handling
    - Test WebSocket disconnection recovery
    - _Requirements: 2.3, 2.5, 9.2_
  
  - [x] 13.3 Write property test for backend message structure
    - **Property 27: Backend message structure**
    - **Validates: Requirements 13.4**
  
  - [x] 13.4 Write property test for backend message types
    - **Property 28: Backend message type enumeration**
    - **Validates: Requirements 13.5**

- [ ] 14. Final Checkpoint - End-to-End Verification
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties
- Unit tests validate specific examples and edge cases
- Integration tests validate end-to-end flows
- The backend already has comprehensive WebSocket handling, so most work is on the frontend
- Camera capture and WebSocket client are new modules that need to be created
- The verify-glass page needs significant updates to replace mock simulation with real backend communication
