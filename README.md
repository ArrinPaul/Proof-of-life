# Proof-of-Life Authentication System

A next-generation biometric authentication system that uses real-time video analysis with ML-powered liveness detection, emotion recognition, and deepfake detection to verify human presence.

## Overview

This system provides secure, AI-driven authentication by analyzing live video streams to detect genuine human presence. It combines multiple verification techniques including 3D depth analysis, micro-movement detection, emotion recognition, and deepfake detection to prevent spoofing attacks.

## Key Features

- **Multi-Modal Verification**: Combines liveness, emotion, and deepfake detection
- **Real-Time Processing**: WebSocket-based video stream analysis
- **Interactive Challenges**: Dynamic gesture and expression challenges
- **ML-Powered Detection**: Uses MediaPipe, DeepFace, and MesoNet-4
- **Secure Token Issuance**: JWT tokens with RS256 signing
- **Comprehensive Audit Logging**: 90-day retention with detailed event tracking
- **Replay Attack Prevention**: Cryptographic nonce validation

## Technology Stack

### Backend
- **Framework**: FastAPI (Python 3.11)
- **ML Models**:
  - MediaPipe FaceMesh (3D face landmarks, liveness detection)
  - DeepFace with VGG-Face (emotion recognition)
  - MesoNet-4 (deepfake detection)
- **Database**: SQLite with async support
- **Authentication**: JWT with RS256
- **WebSocket**: Real-time bidirectional communication

### Frontend
- **Framework**: Next.js 14 (React, TypeScript)
- **Styling**: Tailwind CSS
- **State Management**: React Context API
- **Camera**: MediaDevices API

## Architecture

```
┌─────────────┐         WebSocket          ┌──────────────┐
│   Frontend  │ ◄─────────────────────────► │   Backend    │
│  (Next.js)  │                             │  (FastAPI)   │
└─────────────┘                             └──────┬───────┘
                                                   │
                                    ┌──────────────┼──────────────┐
                                    │              │              │
                              ┌─────▼────┐  ┌─────▼────┐  ┌─────▼────┐
                              │MediaPipe │  │ DeepFace │  │MesoNet-4 │
                              │FaceMesh  │  │VGG-Face  │  │ Detector │
                              └──────────┘  └──────────┘  └──────────┘
```

## Installation

### Prerequisites

- Python 3.11 (required for TensorFlow 2.20.0 compatibility)
- Node.js 18+ and npm
- Git

### Backend Setup

1. **Clone the repository**
```bash
git clone <repository-url>
cd backend
```

2. **Create virtual environment with Python 3.11**
```bash
python3.11 -m venv venv311
# Windows
venv311\Scripts\activate
# Linux/Mac
source venv311/bin/activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Download ML models**
```bash
python download_mediapipe_model.py
python download_deepfake_model.py
```

5. **Configure environment**
```bash
cp .env.example .env
# Edit .env with your configuration
```

6. **Run the server**
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Setup

1. **Navigate to frontend directory**
```bash
cd frontend
```

2. **Install dependencies**
```bash
npm install
```

3. **Configure environment**
```bash
cp .env.local.example .env.local
# Edit .env.local with backend URL
```

4. **Run development server**
```bash
npm run dev
```

5. **Access the application**
```
http://localhost:3000
```

## API Endpoints

### Authentication Flow

1. **POST /auth/verify** - Initialize authentication session
   - Request: `{ "user_id": "string" }`
   - Response: `{ "session_id": "string", "websocket_url": "string" }`

2. **WebSocket /ws/verify/{session_id}** - Real-time verification
   - Receives: Challenge sequences
   - Sends: Video frames (base64 encoded)
   - Receives: Real-time feedback and scores

3. **POST /token/validate** - Validate issued JWT token
   - Request: `{ "token": "string" }`
   - Response: `{ "valid": boolean, "payload": object }`

### Health & Monitoring

- **GET /** - Root endpoint
- **GET /health** - Health check

## Verification Process

### Phase 1: Session Initialization
1. Client requests authentication with user_id
2. Server creates session and generates unique session_id
3. Server returns WebSocket URL for real-time communication

### Phase 2: Challenge Sequence
1. Server generates 3-5 random challenges (gestures/expressions)
2. Each challenge includes:
   - Unique challenge_id
   - Type (gesture/expression)
   - Instruction text
   - Cryptographic nonce (replay prevention)

### Phase 3: Real-Time Verification
1. Client streams video frames via WebSocket
2. Server analyzes each frame using ML models:
   - **Liveness Detection**: 3D depth + micro-movements
   - **Emotion Recognition**: DeepFace emotion analysis
   - **Deepfake Detection**: MesoNet-4 artifact detection
3. Server sends real-time feedback to client

### Phase 4: Scoring & Decision
1. Server computes final score using weighted formula:
   - Liveness: 50%
   - Emotion: 25%
   - Deepfake: 25%
2. Pass threshold: 0.70 (70%)
3. If passed: Issue JWT token (15-minute expiry)
4. If failed: Terminate session with reason

## ML Models

### MediaPipe FaceMesh
- **Purpose**: 3D face landmark detection, liveness verification
- **Features**: 478 facial landmarks, 3D depth estimation
- **Model Size**: ~3.58 MB
- **Location**: `~/.mediapipe_models/face_landmarker.task`

### DeepFace (VGG-Face + FER)
- **Purpose**: Emotion recognition
- **Emotions**: Happy, sad, angry, surprise, fear, disgust, neutral
- **Model Size**: ~5.98 MB
- **Location**: `~/.deepface/weights/`

### MesoNet-4
- **Purpose**: Deepfake detection
- **Features**: Spatial artifact detection, temporal consistency
- **Model Size**: ~0.15 MB
- **Location**: `~/.deepfake_models/mesonet4_weights.h5`

## Security Features

### Replay Attack Prevention
- Cryptographic nonces generated per challenge
- Nonces stored with 5-minute expiration
- Validation ensures nonce matches session
- Used nonces are immediately invalidated

### Token Security
- RS256 asymmetric signing
- 15-minute token expiration
- Includes session_id, user_id, verification_score
- Signature verification on validation

### Session Management
- 2-minute session timeout
- 3 consecutive failure limit
- Automatic session termination
- Secure session state tracking

## Testing

### Run All Tests
```bash
cd backend
pytest
```

### Run Specific Test Suites
```bash
# Unit tests only
pytest -k "not property"

# Property-based tests only
pytest -k "property"

# Specific service tests
pytest tests/test_emotion_analyzer.py
pytest tests/test_deepfake_detector.py
pytest tests/test_cv_verifier.py
```

### Test ML Models
```bash
python test_models_live.py
```

### Test Coverage
- 328 total tests
- 291 unit tests
- 37 property-based tests
- All core functionality covered

## Configuration

### Backend Environment Variables
```env
# Server
HOST=0.0.0.0
PORT=8000

# Security
JWT_EXPIRY_MINUTES=15
SESSION_TIMEOUT_SECONDS=120

# ML Models
MEDIAPIPE_MODEL_PATH=~/.mediapipe_models/face_landmarker.task
DEEPFAKE_MODEL_PATH=~/.deepfake_models/mesonet4_weights.h5

# Database
DATABASE_URL=sqlite:///./pol_auth.db
```

### Frontend Environment Variables
```env
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_WS_URL=ws://localhost:8000
```

## Performance

- **Frame Processing**: ~100-200ms per frame
- **Challenge Completion**: 5-10 seconds average
- **Full Verification**: 30-60 seconds
- **Concurrent Sessions**: Supports multiple simultaneous users

## Deployment

### Docker Deployment
```bash
# Backend
cd backend
docker build -t pol-auth-backend .
docker run -p 8000:8000 pol-auth-backend

# Frontend
cd frontend
docker build -t pol-auth-frontend .
docker run -p 3000:3000 pol-auth-frontend
```

### Production Considerations
- Use production ASGI server (Gunicorn + Uvicorn workers)
- Enable HTTPS/WSS for secure communication
- Configure CORS for production domains
- Set up database backups
- Monitor ML model performance
- Implement rate limiting
- Use CDN for frontend assets

## Troubleshooting

### ML Models Not Loading
```bash
# Re-download models
python backend/download_mediapipe_model.py
python backend/download_deepfake_model.py
```

### Python Version Issues
- Ensure Python 3.11 is installed
- TensorFlow 2.20.0 requires Python 3.11
- Use `py -3.11` on Windows or `python3.11` on Linux/Mac

### WebSocket Connection Errors
- Check CORS configuration
- Verify WebSocket URL format
- Ensure backend is running
- Check firewall settings

### Camera Access Issues
- Grant browser camera permissions
- Use HTTPS in production (required for camera access)
- Check browser compatibility

## Project Structure

```
.
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI application
│   │   ├── models/
│   │   │   └── data_models.py      # Data structures
│   │   └── services/
│   │       ├── challenge_engine.py  # Challenge generation
│   │       ├── cv_verifier.py       # Liveness detection
│   │       ├── emotion_analyzer.py  # Emotion recognition
│   │       ├── deepfake_detector.py # Deepfake detection
│   │       ├── scoring_engine.py    # Score computation
│   │       ├── session_manager.py   # Session handling
│   │       ├── token_issuer.py      # JWT management
│   │       ├── database_service.py  # Data persistence
│   │       └── websocket_handler.py # WebSocket communication
│   ├── tests/                       # Comprehensive test suite
│   ├── requirements.txt             # Python dependencies
│   └── pytest.ini                   # Test configuration
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   └── verify/
│   │   │       └── page.tsx         # Verification page
│   │   ├── components/
│   │   │   ├── CameraCapture.tsx    # Camera handling
│   │   │   ├── ChallengeDisplay.tsx # Challenge UI
│   │   │   └── FeedbackDisplay.tsx  # Real-time feedback
│   │   └── lib/
│   │       └── verification-context.tsx # State management
│   ├── package.json                 # Node dependencies
│   └── tailwind.config.ts           # Styling configuration
└── .kiro/specs/proof-of-life-auth/
    ├── requirements.md              # Feature requirements
    ├── design.md                    # Technical design
    └── tasks.md                     # Implementation tasks
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests: `pytest`
5. Submit a pull request

## License

[Your License Here]

## Support

For issues and questions:
- GitHub Issues: [repository-url]/issues
- Documentation: [docs-url]
- Email: [support-email]

## Acknowledgments

- MediaPipe by Google
- DeepFace by Serengil
- MesoNet-4 by Afchar et al.
- FastAPI framework
- Next.js framework
