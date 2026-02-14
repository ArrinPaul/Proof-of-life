# Design Document: Multi-Factor Proof of Life Authentication System

## Overview

The Multi-Factor Proof of Life (PoL) authentication system is a sophisticated real-time verification platform that combines computer vision, emotion analysis, and deepfake detection to confirm human liveness and intent. The system addresses the growing threat of AI-generated deepfakes and spoofing attacks by implementing multiple independent verification layers that must all succeed for authentication.

The architecture follows a client-server model with real-time WebSocket communication, enabling immediate feedback during verification. The system generates unpredictable visual challenges, analyzes user responses through multiple ML models, computes a weighted verification score, and issues time-bound authentication tokens upon success.

**Key Design Principles:**
- Defense in depth: Multiple independent verification layers
- Real-time feedback: Sub-500ms response times for user actions
- Unpredictability: Cryptographically random challenges prevent preparation
- Time-bound security: Short-lived tokens and session timeouts
- Auditability: Comprehensive logging of all verification attempts

## Architecture

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend (Next.js)                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Clerk Auth   │  │ WebRTC       │  │ WebSocket    │      │
│  │ Component    │  │ Camera       │  │ Client       │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│  ┌────────────────────────────────────────────────────┐     │
│  │         UI Components (Tailwind CSS)               │     │
│  │  - Challenge Display                               │     │
│  │  - Camera Preview                                  │     │
│  │  - Real-time Feedback                              │     │
│  │  - Score Display                                   │     │
│  └────────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────┘
                            │
                            │ WebSocket + HTTPS
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    Backend (FastAPI)                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ WebSocket    │  │ Session      │  │ JWT Token    │      │
│  │ Handler      │  │ Manager      │  │ Service      │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Challenge    │  │ Scoring      │  │ Database     │      │
│  │ Engine       │  │ Engine       │  │ (SQLite)     │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                    ML Verification Layer                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ MediaPipe    │  │ DeepFace     │  │ Deepfake     │      │
│  │ FaceMesh     │  │ Emotion      │  │ Detector     │      │
│  │ (Liveness)   │  │ Analysis     │  │ Model        │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│  ┌──────────────┐                                           │
│  │ OpenCV       │                                           │
│  │ Processing   │                                           │
│  └──────────────┘                                           │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼ (Optional)
┌─────────────────────────────────────────────────────────────┐
│              Blockchain Layer (Stretch Goal)                 │
│  ┌──────────────┐  ┌──────────────┐                         │
│  │ Hardhat      │  │ ERC721       │                         │
│  │ Smart        │  │ Token        │                         │
│  │ Contracts    │  │ Minting      │                         │
│  └──────────────┘  └──────────────┘                         │
└─────────────────────────────────────────────────────────────┘
```

### Communication Flow

1. **Authentication Phase**: User authenticates via Clerk, receives session token
2. **Session Initialization**: Frontend establishes WebSocket connection, backend creates session record
3. **Challenge Generation**: Backend generates random challenge sequence with cryptographic nonce
4. **Video Capture**: Frontend captures video frames via WebRTC, streams to backend via WebSocket
5. **ML Processing**: Backend processes frames through three parallel verification pipelines
6. **Score Computation**: Scoring engine combines results using weighted formula
7. **Token Issuance**: Upon success, backend generates JWT and returns to frontend
8. **Token Usage**: Frontend includes JWT in requests to protected resources

## Components and Interfaces

### 1. Authentication Service (Clerk Integration)

**Responsibility:** Manage user authentication and session initialization

**Interface:**
```typescript
interface AuthService {
  // Authenticate user and create session
  authenticateUser(): Promise<AuthResult>
  
  // Get current user identity
  getCurrentUser(): User | null
  
  // Sign out user
  signOut(): Promise<void>
}

interface AuthResult {
  success: boolean
  userId: string
  sessionToken: string
  error?: string
}

interface User {
  id: string
  email: string
  name: string
}
```

### 2. Challenge Engine

**Responsibility:** Generate unpredictable visual challenges with anti-replay protection

**Interface:**
```python
class ChallengeEngine:
    def generate_challenge_sequence(
        self, 
        session_id: str, 
        num_challenges: int = 3
    ) -> ChallengeSequence:
        """Generate random sequence of gestures and expressions"""
        pass
    
    def validate_nonce(self, nonce: str, session_id: str) -> bool:
        """Verify nonce is valid and not reused"""
        pass

@dataclass
class ChallengeSequence:
    session_id: str
    nonce: str
    timestamp: float
    challenges: List[Challenge]

@dataclass
class Challenge:
    challenge_id: str
    type: ChallengeType  # GESTURE or EXPRESSION
    instruction: str  # e.g., "Nod your head", "Smile"
    timeout_seconds: int = 10

class ChallengeType(Enum):
    GESTURE = "gesture"
    EXPRESSION = "expression"
```

**Challenge Pool:**
- Gestures: nod_up, nod_down, turn_left, turn_right, tilt_left, tilt_right, open_mouth, close_eyes, raise_eyebrows, blink
- Expressions: smile, frown, surprised, neutral, angry

### 3. Computer Vision Verifier

**Responsibility:** Detect liveness and verify challenge completion using MediaPipe and OpenCV

**Interface:**
```python
class CVVerifier:
    def __init__(self):
        self.face_mesh = mp.solutions.face_mesh.FaceMesh(
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )
    
    def compute_liveness_score(self, video_frames: List[np.ndarray]) -> float:
        """Analyze frames for 3D depth cues and natural micro-movements"""
        pass
    
    def verify_challenge(
        self, 
        challenge: Challenge, 
        video_frames: List[np.ndarray]
    ) -> ChallengeResult:
        """Check if user performed the requested action"""
        pass
    
    def detect_3d_depth(self, landmarks: np.ndarray) -> float:
        """Compute depth score from facial landmark geometry"""
        pass
    
    def detect_micro_movements(self, frame_sequence: List[np.ndarray]) -> float:
        """Detect natural involuntary movements"""
        pass

@dataclass
class ChallengeResult:
    challenge_id: str
    completed: bool
    confidence: float
    timestamp: float
```

**Liveness Detection Algorithm:**
1. Extract 468 facial landmarks using MediaPipe FaceMesh
2. Compute 3D depth by analyzing landmark distances and perspective
3. Track micro-movements (eye blinks, subtle head motion) across frames
4. Detect texture patterns inconsistent with flat images
5. Combine signals into liveness score (0.0-1.0)

### 4. Deepfake Detector

**Responsibility:** Identify synthetic or manipulated video content

**Interface:**
```python
class DeepfakeDetector:
    def __init__(self, model_path: str):
        self.model = load_deepfake_model(model_path)
    
    def compute_deepfake_score(self, video_frames: List[np.ndarray]) -> float:
        """Analyze frames for synthetic artifacts and temporal inconsistencies"""
        pass
    
    def detect_spatial_artifacts(self, frame: np.ndarray) -> float:
        """Look for GAN artifacts, compression anomalies"""
        pass
    
    def detect_temporal_inconsistencies(
        self, 
        frame_sequence: List[np.ndarray]
    ) -> float:
        """Check for unnatural frame-to-frame transitions"""
        pass
```

**Detection Strategy:**
- Spatial analysis: Look for GAN fingerprints, compression artifacts, unnatural textures
- Temporal analysis: Detect inconsistent motion, flickering, frame discontinuities
- Frequency domain: Analyze spectral patterns typical of synthetic media
- Output: Authenticity score (0.0 = definitely fake, 1.0 = definitely real)

### 5. Emotion Analyzer

**Responsibility:** Verify genuine emotional responses using DeepFace

**Interface:**
```python
class EmotionAnalyzer:
    def __init__(self):
        self.detector = DeepFace
    
    def compute_emotion_score(
        self, 
        video_frames: List[np.ndarray],
        expected_emotion: Optional[str] = None
    ) -> float:
        """Analyze emotional authenticity and natural transitions"""
        pass
    
    def detect_emotion(self, frame: np.ndarray) -> EmotionResult:
        """Identify dominant emotion in frame"""
        pass
    
    def verify_natural_transitions(
        self, 
        emotion_sequence: List[EmotionResult]
    ) -> float:
        """Check for realistic emotional state changes"""
        pass

@dataclass
class EmotionResult:
    dominant_emotion: str  # happy, sad, angry, surprised, neutral, fear, disgust
    confidence: float
    timestamp: float
```

**Authenticity Verification:**
- Detect current emotion using DeepFace
- Track emotion transitions across frames
- Penalize instantaneous or unnatural changes
- Verify micro-expressions consistent with genuine emotion
- Output: Authenticity score (0.0-1.0)

### 6. Scoring Engine

**Responsibility:** Combine verification signals into final decision

**Interface:**
```python
class ScoringEngine:
    LIVENESS_WEIGHT = 0.4
    DEEPFAKE_WEIGHT = 0.3
    EMOTION_WEIGHT = 0.3
    THRESHOLD = 0.70
    
    def compute_final_score(
        self,
        liveness_score: float,
        deepfake_score: float,
        emotion_score: float
    ) -> ScoringResult:
        """Calculate weighted final score and verification decision"""
        pass

@dataclass
class ScoringResult:
    liveness_score: float
    deepfake_score: float
    emotion_score: float
    final_score: float
    passed: bool
    timestamp: float
```

**Scoring Formula:**
```
final_score = 0.4 × liveness_score + 0.3 × deepfake_score + 0.3 × emotion_score
passed = final_score >= 0.70
```

### 7. Token Issuer

**Responsibility:** Generate and validate time-bound authentication tokens

**Interface:**
```python
class TokenIssuer:
    TOKEN_EXPIRY_MINUTES = 15
    
    def __init__(self, private_key: str, public_key: str):
        self.private_key = private_key
        self.public_key = public_key
    
    def issue_jwt_token(
        self,
        user_id: str,
        session_id: str,
        final_score: float
    ) -> str:
        """Generate signed JWT with verification metadata"""
        pass
    
    def validate_token(self, token: str) -> TokenValidation:
        """Verify signature and expiration"""
        pass
    
    # Optional blockchain methods
    def mint_nft_token(
        self,
        user_address: str,
        verification_metadata: dict
    ) -> str:
        """Mint ERC721 token on-chain (stretch goal)"""
        pass

@dataclass
class TokenValidation:
    valid: bool
    user_id: Optional[str]
    session_id: Optional[str]
    issued_at: Optional[float]
    expires_at: Optional[float]
    error: Optional[str]
```

**JWT Payload Structure:**
```json
{
  "sub": "user_id",
  "session_id": "unique_session_id",
  "final_score": 0.85,
  "iat": 1234567890,
  "exp": 1234568790,
  "iss": "proof-of-life-auth"
}
```

### 8. Session Manager

**Responsibility:** Track verification sessions and enforce timeouts

**Interface:**
```python
class SessionManager:
    MAX_SESSION_DURATION_SECONDS = 120
    MAX_CONSECUTIVE_FAILURES = 3
    CHALLENGE_TIMEOUT_SECONDS = 10
    
    def create_session(self, user_id: str) -> Session:
        """Initialize new verification session"""
        pass
    
    def update_session(
        self,
        session_id: str,
        challenge_result: ChallengeResult
    ) -> Session:
        """Record challenge completion"""
        pass
    
    def check_timeout(self, session_id: str) -> bool:
        """Verify session hasn't exceeded time limits"""
        pass
    
    def terminate_session(self, session_id: str, reason: str) -> None:
        """End session and log reason"""
        pass

@dataclass
class Session:
    session_id: str
    user_id: str
    start_time: float
    challenges: List[Challenge]
    completed_challenges: List[ChallengeResult]
    failed_count: int
    status: SessionStatus

class SessionStatus(Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
```

### 9. WebSocket Handler

**Responsibility:** Manage real-time bidirectional communication

**Interface:**
```python
class WebSocketHandler:
    async def handle_connection(self, websocket: WebSocket, user_id: str):
        """Accept WebSocket connection and manage session"""
        pass
    
    async def receive_video_frame(self, websocket: WebSocket) -> np.ndarray:
        """Receive and decode video frame from client"""
        pass
    
    async def send_challenge(self, websocket: WebSocket, challenge: Challenge):
        """Send new challenge to client"""
        pass
    
    async def send_feedback(
        self,
        websocket: WebSocket,
        feedback: VerificationFeedback
    ):
        """Send real-time status update"""
        pass

@dataclass
class VerificationFeedback:
    type: FeedbackType
    message: str
    data: Optional[dict]

class FeedbackType(Enum):
    CHALLENGE_ISSUED = "challenge_issued"
    CHALLENGE_COMPLETED = "challenge_completed"
    CHALLENGE_FAILED = "challenge_failed"
    SCORE_UPDATE = "score_update"
    VERIFICATION_SUCCESS = "verification_success"
    VERIFICATION_FAILED = "verification_failed"
    ERROR = "error"
```

### 10. Database Service

**Responsibility:** Persist sessions, audit logs, and nonce tracking

**Interface:**
```python
class DatabaseService:
    def __init__(self, db_path: str):
        self.db = sqlite3.connect(db_path)
    
    def save_session(self, session: Session) -> None:
        """Store session record"""
        pass
    
    def save_verification_result(self, result: ScoringResult, session_id: str) -> None:
        """Store final scores and decision"""
        pass
    
    def save_token_issuance(self, token_id: str, user_id: str, expires_at: float) -> None:
        """Log token generation"""
        pass
    
    def check_nonce_used(self, nonce: str) -> bool:
        """Verify nonce hasn't been used"""
        pass
    
    def store_nonce(self, nonce: str, session_id: str, expires_at: float) -> None:
        """Record nonce to prevent replay"""
        pass
    
    def purge_expired_nonces(self) -> int:
        """Remove nonces older than 24 hours"""
        pass
    
    def get_audit_logs(
        self,
        user_id: Optional[str] = None,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None
    ) -> List[AuditLog]:
        """Retrieve audit records"""
        pass

@dataclass
class AuditLog:
    log_id: str
    session_id: str
    user_id: str
    event_type: str
    timestamp: float
    details: dict
```

**Database Schema:**

```sql
-- Sessions table
CREATE TABLE sessions (
    session_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    start_time REAL NOT NULL,
    end_time REAL,
    status TEXT NOT NULL,
    failed_count INTEGER DEFAULT 0
);

-- Verification results table
CREATE TABLE verification_results (
    result_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    liveness_score REAL NOT NULL,
    deepfake_score REAL NOT NULL,
    emotion_score REAL NOT NULL,
    final_score REAL NOT NULL,
    passed BOOLEAN NOT NULL,
    timestamp REAL NOT NULL,
    FOREIGN KEY (session_id) REFERENCES sessions(session_id)
);

-- Tokens table
CREATE TABLE tokens (
    token_id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    session_id TEXT NOT NULL,
    issued_at REAL NOT NULL,
    expires_at REAL NOT NULL
);

-- Nonces table (for replay attack prevention)
CREATE TABLE nonces (
    nonce TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    created_at REAL NOT NULL,
    expires_at REAL NOT NULL
);

-- Audit logs table
CREATE TABLE audit_logs (
    log_id TEXT PRIMARY KEY,
    session_id TEXT NOT NULL,
    user_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    timestamp REAL NOT NULL,
    details TEXT  -- JSON string
);

-- Indexes for performance
CREATE INDEX idx_sessions_user ON sessions(user_id);
CREATE INDEX idx_nonces_expires ON nonces(expires_at);
CREATE INDEX idx_audit_logs_user_time ON audit_logs(user_id, timestamp);
```

## Data Models

### Core Data Structures

```python
from dataclasses import dataclass
from enum import Enum
from typing import List, Optional
import numpy as np

# Challenge models
@dataclass
class Challenge:
    challenge_id: str
    type: ChallengeType
    instruction: str
    timeout_seconds: int = 10

class ChallengeType(Enum):
    GESTURE = "gesture"
    EXPRESSION = "expression"

@dataclass
class ChallengeSequence:
    session_id: str
    nonce: str
    timestamp: float
    challenges: List[Challenge]

# Verification result models
@dataclass
class ChallengeResult:
    challenge_id: str
    completed: bool
    confidence: float
    timestamp: float

@dataclass
class EmotionResult:
    dominant_emotion: str
    confidence: float
    timestamp: float

@dataclass
class ScoringResult:
    liveness_score: float
    deepfake_score: float
    emotion_score: float
    final_score: float
    passed: bool
    timestamp: float

# Session models
@dataclass
class Session:
    session_id: str
    user_id: str
    start_time: float
    challenges: List[Challenge]
    completed_challenges: List[ChallengeResult]
    failed_count: int
    status: SessionStatus

class SessionStatus(Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"

# Token models
@dataclass
class TokenValidation:
    valid: bool
    user_id: Optional[str]
    session_id: Optional[str]
    issued_at: Optional[float]
    expires_at: Optional[float]
    error: Optional[str]

# WebSocket communication models
@dataclass
class VerificationFeedback:
    type: FeedbackType
    message: str
    data: Optional[dict]

class FeedbackType(Enum):
    CHALLENGE_ISSUED = "challenge_issued"
    CHALLENGE_COMPLETED = "challenge_completed"
    CHALLENGE_FAILED = "challenge_failed"
    SCORE_UPDATE = "score_update"
    VERIFICATION_SUCCESS = "verification_success"
    VERIFICATION_FAILED = "verification_failed"
    ERROR = "error"

# Audit models
@dataclass
class AuditLog:
    log_id: str
    session_id: str
    user_id: str
    event_type: str
    timestamp: float
    details: dict
```

### Frontend Data Models (TypeScript)

```typescript
// Authentication
interface User {
  id: string
  email: string
  name: string
}

interface AuthResult {
  success: boolean
  userId: string
  sessionToken: string
  error?: string
}

// Challenges
interface Challenge {
  challengeId: string
  type: 'gesture' | 'expression'
  instruction: string
  timeoutSeconds: number
}

interface ChallengeSequence {
  sessionId: string
  nonce: string
  timestamp: number
  challenges: Challenge[]
}

// Verification feedback
interface VerificationFeedback {
  type: 'challenge_issued' | 'challenge_completed' | 'challenge_failed' | 
        'score_update' | 'verification_success' | 'verification_failed' | 'error'
  message: string
  data?: {
    challenge?: Challenge
    score?: number
    finalScore?: number
    passed?: boolean
  }
}

// Session state
interface SessionState {
  sessionId: string
  currentChallenge: Challenge | null
  completedChallenges: number
  totalChallenges: number
  currentScore: number
  status: 'idle' | 'active' | 'completed' | 'failed'
}

// Token
interface VerificationToken {
  token: string
  expiresAt: number
  finalScore: number
}
```


## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system—essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Unique Session Generation

*For any* successful authentication, the system should generate a unique session identifier that differs from all other active session identifiers.

**Validates: Requirements 1.2**

### Property 2: User Association Invariant

*For any* verification attempt, the session record should contain the authenticated user identity that initiated it.

**Validates: Requirements 1.4**

### Property 3: Challenge Sequence Uniqueness

*For any* two consecutive verification sessions, the generated challenge sequences should not be identical.

**Validates: Requirements 2.4**

### Property 4: Challenge Timestamp Presence

*For any* generated challenge sequence, it should contain a timestamp and cryptographic nonce.

**Validates: Requirements 2.5, 11.1**

### Property 5: Score Range Validity

*For any* verification component output (liveness, deepfake, emotion), the score should be a value between 0.0 and 1.0 inclusive.

**Validates: Requirements 3.4, 5.3, 6.3**

### Property 6: Challenge Completion Recording

*For any* gesture that matches the requested challenge, the system should record the completion with a timestamp.

**Validates: Requirements 4.3**

### Property 7: Minimum Challenge Requirement

*For any* verification session, successful completion should require at least 3 distinct challenges to be completed.

**Validates: Requirements 4.5**

### Property 8: Frame Analysis Completeness

*For any* captured video frame during deepfake detection, the frame should be analyzed for synthetic artifacts.

**Validates: Requirements 5.1**

### Property 9: Expression Challenge Detection

*For any* challenge that requires an expression, the emotion analyzer should perform emotion detection on the video frames.

**Validates: Requirements 6.1**

### Property 10: Scoring Formula Correctness

*For any* set of component scores (liveness, deepfake, emotion), the final score should equal exactly 0.4 × liveness_score + 0.3 × deepfake_score + 0.3 × emotion_score.

**Validates: Requirements 7.1**

### Property 11: Threshold-Based Verification Decision

*For any* calculated final score, the verification should be marked as successful if and only if the score is greater than or equal to 0.70.

**Validates: Requirements 7.2, 7.3, 7.4**

### Property 12: Audit Log Completeness

*For any* verification attempt, the system should create audit log entries containing all component scores and the final score.

**Validates: Requirements 7.5**

### Property 13: JWT Structure Validity

*For any* successful verification, the issued JWT should contain user identity, session identifier, verification timestamp, and expiration time set to exactly 15 minutes from issuance, and should have a valid signature.

**Validates: Requirements 8.1, 8.2, 8.3, 8.4**

### Property 14: Session Start Timestamp

*For any* created session, the database record should contain a start timestamp and the authenticated user identity.

**Validates: Requirements 9.1, 13.1**

### Property 15: Frame Transmission via WebSocket

*For any* captured video frame during an active session, the frame should be transmitted to the backend via the WebSocket connection.

**Validates: Requirements 10.2**

### Property 16: Status Update Propagation

*For any* significant verification event (challenge completion, score update, verification result), the system should send a status update message to the frontend.

**Validates: Requirements 10.5, 12.3**

### Property 17: Nonce Storage and Validation

*For any* verification attempt, the system should validate that the nonce matches the current session and should store used nonces with expiration timestamps.

**Validates: Requirements 11.2, 11.3**

### Property 18: Verification Result Persistence

*For any* completed verification, the system should persist all component scores, final score, and verification decision to the database.

**Validates: Requirements 13.2**

### Property 19: Token Issuance Logging

*For any* issued token, the system should create a log entry containing the token identifier, user identity, and expiration time.

**Validates: Requirements 13.3**

### Property 20: Event Timestamp Recording

*For any* significant system event (session start, challenge completion, verification result, token issuance), the audit log should contain a timestamp.

**Validates: Requirements 13.4**

### Property 21: JWT Signature Verification

*For any* presented token during validation, the system should verify the JWT signature using the public key and check the expiration timestamp.

**Validates: Requirements 14.1, 14.2**

### Property 22: Error Logging Completeness

*For any* technical error that occurs during verification, the system should create a detailed log entry for debugging purposes.

**Validates: Requirements 15.4**

## Error Handling

### Error Categories

**1. Authentication Errors**
- Invalid credentials → Deny access, return clear error message
- Session expired → Require re-authentication
- Missing authentication → Redirect to login

**2. Camera and Media Errors**
- Camera access denied → Display permission instructions, prevent verification start
- Camera not found → Display hardware error, suggest troubleshooting
- Video stream interrupted → Terminate session after 2-second grace period
- WebRTC connection failure → Display network error, offer retry

**3. WebSocket Errors**
- Connection failure → Display network error, prevent session start
- Connection dropped during session → Terminate session immediately
- Message transmission failure → Log error, retry once, then terminate

**4. Verification Errors**
- Deepfake score < 0.5 → Terminate session immediately, log security event
- Final score < 0.70 → Mark verification as failed, explain which components scored low
- Challenge timeout (10 seconds) → Mark challenge as failed, proceed to next
- 3 consecutive challenge failures → Terminate session
- Total session timeout (2 minutes) → Terminate session

**5. ML Model Errors**
- MediaPipe initialization failure → Display technical error, prevent verification
- DeepFace model loading failure → Display technical error, prevent verification
- Deepfake model loading failure → Continue without deepfake detection (optional component)
- Frame processing exception → Log error, skip frame, continue if possible

**6. Database Errors**
- Connection failure → Log error, continue session (write to memory), sync later
- Write failure → Log error, retry once, continue session
- Nonce lookup failure → Reject verification attempt (fail-secure)

**7. Token Errors**
- Token generation failure → Log error, return verification success but no token
- Invalid token signature → Reject token, log security event
- Expired token → Reject token, require new verification
- Missing token claims → Reject token, log malformed token event

**8. Replay Attack Detection**
- Reused nonce → Reject immediately, log security event, terminate session
- Timestamp too old (>5 minutes) → Reject challenge, require new session
- Timestamp in future → Reject challenge, log suspicious activity

### Error Response Format

All errors returned to the frontend follow this structure:

```typescript
interface ErrorResponse {
  error: {
    code: string          // Machine-readable error code
    message: string       // Human-readable error message
    category: string      // Error category for handling
    recoverable: boolean  // Whether user can retry
    details?: any        // Additional context for debugging
  }
}
```

### Recovery Strategies

**Automatic Recovery:**
- Single frame processing failure → Skip frame, continue with next
- Temporary network glitch → Retry once with exponential backoff
- Database write failure → Queue for retry, continue session

**User-Initiated Recovery:**
- Camera permission denied → User grants permission, restart
- Network failure → User checks connection, clicks retry
- Verification failure → User clicks "Try Again", new session starts

**No Recovery (Security):**
- Deepfake detected → Session terminated, no retry for 5 minutes
- Replay attack detected → Session terminated, security alert
- Invalid token signature → Token rejected, require new verification

### Logging Strategy

**Error Severity Levels:**
- CRITICAL: Security events (replay attacks, deepfakes, invalid signatures)
- ERROR: System failures preventing verification (model loading, database connection)
- WARNING: Recoverable issues (single frame failure, temporary network glitch)
- INFO: Normal operation events (session start, verification success)

**Log Entry Structure:**
```python
@dataclass
class ErrorLog:
    timestamp: float
    severity: str
    category: str
    error_code: str
    message: str
    session_id: Optional[str]
    user_id: Optional[str]
    stack_trace: Optional[str]
    context: dict  # Additional debugging information
```

## Testing Strategy

### Dual Testing Approach

The system requires both unit testing and property-based testing for comprehensive coverage:

**Unit Tests** focus on:
- Specific examples demonstrating correct behavior
- Edge cases (empty inputs, boundary values, extreme conditions)
- Error conditions and exception handling
- Integration points between components
- UI interactions and display logic

**Property-Based Tests** focus on:
- Universal properties that hold for all inputs
- Comprehensive input coverage through randomization
- Invariants that must be maintained across operations
- Round-trip properties (encode/decode, serialize/deserialize)
- Metamorphic properties (relationships between operations)

Both testing approaches are complementary and necessary. Unit tests catch concrete bugs in specific scenarios, while property tests verify general correctness across the input space.

### Property-Based Testing Configuration

**Testing Library:** We will use `hypothesis` for Python backend and `fast-check` for TypeScript frontend.

**Test Configuration:**
- Minimum 100 iterations per property test (due to randomization)
- Each property test must reference its design document property
- Tag format: `# Feature: proof-of-life-auth, Property {number}: {property_text}`

**Example Property Test Structure (Python):**

```python
from hypothesis import given, strategies as st
import pytest

@given(
    liveness=st.floats(min_value=0.0, max_value=1.0),
    deepfake=st.floats(min_value=0.0, max_value=1.0),
    emotion=st.floats(min_value=0.0, max_value=1.0)
)
@pytest.mark.property_test
def test_scoring_formula_correctness(liveness, deepfake, emotion):
    """
    Feature: proof-of-life-auth, Property 10: Scoring Formula Correctness
    For any set of component scores, final score should equal the weighted formula
    """
    scoring_engine = ScoringEngine()
    result = scoring_engine.compute_final_score(liveness, deepfake, emotion)
    
    expected = 0.4 * liveness + 0.3 * deepfake + 0.3 * emotion
    assert abs(result.final_score - expected) < 0.0001
    assert result.liveness_score == liveness
    assert result.deepfake_score == deepfake
    assert result.emotion_score == emotion
```

**Example Property Test Structure (TypeScript):**

```typescript
import fc from 'fast-check'
import { describe, it, expect } from 'vitest'

describe('Property Tests', () => {
  it('Property 13: JWT Structure Validity', () => {
    // Feature: proof-of-life-auth, Property 13: JWT Structure Validity
    fc.assert(
      fc.property(
        fc.string({ minLength: 1 }),  // userId
        fc.string({ minLength: 1 }),  // sessionId
        fc.float({ min: 0.7, max: 1.0 }),  // finalScore
        (userId, sessionId, finalScore) => {
          const tokenIssuer = new TokenIssuer(privateKey, publicKey)
          const token = tokenIssuer.issueJwtToken(userId, sessionId, finalScore)
          
          const decoded = jwt.decode(token)
          expect(decoded.sub).toBe(userId)
          expect(decoded.session_id).toBe(sessionId)
          expect(decoded.final_score).toBe(finalScore)
          
          const expiresIn = decoded.exp - decoded.iat
          expect(expiresIn).toBe(15 * 60)  // 15 minutes in seconds
          
          const isValid = tokenIssuer.validateToken(token)
          expect(isValid.valid).toBe(true)
        }
      ),
      { numRuns: 100 }
    )
  })
})
```

### Unit Testing Strategy

**Backend Unit Tests (pytest):**

1. **Challenge Engine Tests**
   - Test gesture pool contains at least 10 types
   - Test expression pool contains at least 5 types
   - Test nonce generation produces unique values
   - Test challenge timeout enforcement

2. **CV Verifier Tests**
   - Test liveness detection with flat image (should score low)
   - Test liveness detection with 3D video (should score high)
   - Test gesture recognition for each gesture type
   - Test video stream interruption handling

3. **Deepfake Detector Tests**
   - Test with known synthetic video (should score low)
   - Test with known authentic video (should score high)
   - Test temporal inconsistency detection
   - Test early termination when score < 0.5

4. **Emotion Analyzer Tests**
   - Test detection of 5 core emotions
   - Test natural transition scoring
   - Test unnatural transition penalty
   - Test expression matching for challenges

5. **Scoring Engine Tests**
   - Test threshold boundary (0.69 fails, 0.70 passes)
   - Test formula with known values
   - Test audit log creation

6. **Token Issuer Tests**
   - Test JWT expiration is exactly 15 minutes
   - Test token validation with expired token
   - Test token validation with invalid signature
   - Test token validation with tampered payload

7. **Session Manager Tests**
   - Test 10-second challenge timeout
   - Test 2-minute session timeout
   - Test 3 consecutive failure termination
   - Test session state transitions

8. **Database Service Tests**
   - Test nonce replay prevention
   - Test nonce expiration and purging
   - Test audit log retention (90 days)
   - Test session persistence

**Frontend Unit Tests (Vitest + React Testing Library):**

1. **Authentication Component Tests**
   - Test unauthenticated access is blocked
   - Test successful authentication flow
   - Test authentication failure handling

2. **Camera Component Tests**
   - Test camera permission request
   - Test camera access denied error
   - Test camera preview display
   - Test video stream interruption

3. **Challenge Display Tests**
   - Test challenge instructions are displayed
   - Test challenge timer countdown
   - Test challenge completion feedback

4. **WebSocket Client Tests**
   - Test connection establishment
   - Test connection drop handling
   - Test message transmission
   - Test reconnection logic

5. **UI Feedback Tests**
   - Test real-time score updates
   - Test challenge progress display
   - Test verification result display
   - Test error message display

### Integration Testing

**End-to-End Flow Tests:**

1. **Successful Verification Flow**
   - Authenticate → Start session → Complete 3 challenges → Receive token
   - Verify token is valid and contains correct data
   - Verify audit logs are created

2. **Failed Verification Flow**
   - Authenticate → Start session → Fail challenges → Verification fails
   - Verify no token is issued
   - Verify failure reason is logged

3. **Timeout Scenarios**
   - Challenge timeout → Next challenge issued
   - Session timeout → Session terminated
   - WebSocket timeout → Session terminated

4. **Security Scenarios**
   - Replay attack → Rejected immediately
   - Deepfake detection → Session terminated
   - Invalid token → Access denied

5. **Error Recovery**
   - Camera permission denied → Grant permission → Retry succeeds
   - Network failure → Reconnect → Retry succeeds
   - Verification failure → Restart → New session created

### Performance Testing

**Latency Requirements:**
- Frame processing: < 100ms per frame
- Challenge verification: < 200ms
- WebSocket round-trip: < 500ms
- Total verification time: < 60 seconds (typical)

**Load Testing:**
- Concurrent sessions: Support 100 simultaneous verifications
- Database operations: < 50ms for reads, < 100ms for writes
- Token validation: < 10ms

**Resource Monitoring:**
- Memory usage: < 500MB per session
- CPU usage: < 50% per session
- GPU usage (if available): < 70% for ML models

### Test Coverage Goals

- Backend code coverage: > 85%
- Frontend code coverage: > 80%
- Property test coverage: All 22 correctness properties
- Integration test coverage: All critical user flows
- Security test coverage: All attack vectors (replay, deepfake, token tampering)

### Continuous Integration

**CI Pipeline:**
1. Run unit tests (backend + frontend)
2. Run property-based tests (100 iterations each)
3. Run integration tests
4. Generate coverage reports
5. Run security linting (bandit, eslint-plugin-security)
6. Build and deploy to staging

**Test Execution Time:**
- Unit tests: < 2 minutes
- Property tests: < 5 minutes
- Integration tests: < 3 minutes
- Total CI time: < 10 minutes
