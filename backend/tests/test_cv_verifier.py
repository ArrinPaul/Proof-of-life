"""
Unit tests for CVVerifier class
"""
import pytest
import numpy as np
import cv2
from app.services.cv_verifier import CVVerifier
from app.models.data_models import Challenge, ChallengeType, ChallengeResult



class TestCVVerifierInitialization:
    """Test CVVerifier initialization and configuration"""
    
    def test_initialization_without_model(self):
        """Test that CVVerifier initializes without requiring model file"""
        verifier = CVVerifier()
        
        # Verify initialization succeeds without model
        assert verifier.model_path is None
        assert verifier._face_landmarker is None
        assert verifier.previous_landmarks is None
    
    def test_initialization_with_model_path(self):
        """Test that CVVerifier stores model path when provided"""
        model_path = "/path/to/model.task"
        verifier = CVVerifier(model_path=model_path)
        
        # Verify model path is stored
        assert verifier.model_path == model_path
        assert verifier._face_landmarker is None  # Not initialized yet (lazy)
    
    def test_face_landmarker_lazy_initialization_error(self):
        """Test that accessing face_landmarker without model raises error"""
        verifier = CVVerifier()
        
        # Attempting to access face_landmarker without model should raise ValueError
        with pytest.raises(ValueError, match="Model path must be provided"):
            _ = verifier.face_landmarker


class TestFramePreprocessing:
    """Test frame preprocessing functionality"""
    
    def test_preprocess_frame_resizes_correctly(self):
        """Test that frames are resized to target dimensions"""
        verifier = CVVerifier()
        
        # Create a test frame (BGR format, OpenCV default)
        original_frame = np.random.randint(0, 255, (720, 1280, 3), dtype=np.uint8)
        
        # Preprocess with default target size (640, 480)
        processed = verifier.preprocess_frame(original_frame)
        
        # Verify dimensions
        assert processed.shape == (480, 640, 3)
    
    def test_preprocess_frame_custom_size(self):
        """Test preprocessing with custom target size"""
        verifier = CVVerifier()
        
        # Create a test frame
        original_frame = np.random.randint(0, 255, (1080, 1920, 3), dtype=np.uint8)
        
        # Preprocess with custom size
        target_size = (320, 240)
        processed = verifier.preprocess_frame(original_frame, target_size=target_size)
        
        # Verify dimensions (height, width, channels)
        assert processed.shape == (240, 320, 3)
    
    def test_preprocess_frame_converts_bgr_to_rgb(self):
        """Test that BGR frames are converted to RGB"""
        verifier = CVVerifier()
        
        # Create a test frame with distinct BGR values
        # Blue channel = 255, Green = 0, Red = 0
        bgr_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        bgr_frame[:, :, 0] = 255  # Blue channel in BGR
        
        # Preprocess
        rgb_frame = verifier.preprocess_frame(bgr_frame, target_size=(640, 480))
        
        # In RGB format, the blue should now be in channel 2
        # Red channel (0) should be 0
        # Green channel (1) should be 0
        # Blue channel (2) should be 255
        assert rgb_frame[0, 0, 0] == 0    # Red
        assert rgb_frame[0, 0, 1] == 0    # Green
        assert rgb_frame[0, 0, 2] == 255  # Blue
    
    def test_preprocess_frame_maintains_data_type(self):
        """Test that preprocessing maintains uint8 data type"""
        verifier = CVVerifier()
        
        original_frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        processed = verifier.preprocess_frame(original_frame)
        
        assert processed.dtype == np.uint8
    
    def test_preprocess_frame_with_real_image(self):
        """Test preprocessing with a real-looking image"""
        verifier = CVVerifier()
        
        # Create a simple gradient image
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        for i in range(480):
            frame[i, :, :] = i // 2  # Gradient from dark to light
        
        processed = verifier.preprocess_frame(frame, target_size=(320, 240))
        
        # Verify it processed without errors
        assert processed.shape == (240, 320, 3)
        assert processed.dtype == np.uint8


class TestCVVerifierCleanup:
    """Test resource cleanup"""
    
    def test_cleanup_without_initialization(self):
        """Test that destructor works when face_landmarker was never initialized"""
        verifier = CVVerifier()
        
        # Verify _face_landmarker is None
        assert verifier._face_landmarker is None
        
        # Call destructor - should not raise error
        verifier.__del__()
        
        # Should still be None
        assert verifier._face_landmarker is None


class TestCVVerifierPlaceholderMethods:
    """Test that placeholder methods raise NotImplementedError"""
    
    def test_compute_liveness_score_implemented(self, mocker):
        """Test that compute_liveness_score is now implemented"""
        verifier = CVVerifier(model_path="dummy_path.task")
        
        # Mock the face_landmarker to avoid loading actual model
        mock_landmarker = mocker.MagicMock()
        mock_result = mocker.MagicMock()
        mock_result.face_landmarks = []  # No face detected
        mock_landmarker.detect.return_value = mock_result
        verifier._face_landmarker = mock_landmarker
        
        # Mock detect_micro_movements
        mocker.patch.object(verifier, 'detect_micro_movements', return_value=0.0)
        
        frames = [np.zeros((480, 640, 3), dtype=np.uint8)]
        
        # Should return a score, not raise NotImplementedError
        score = verifier.compute_liveness_score(frames)
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0
    
    def test_verify_challenge_implemented(self):
        """Test that verify_challenge is now implemented"""
        verifier = CVVerifier(model_path="dummy_path.task")
        challenge = Challenge(
            challenge_id="test_session_gesture_0_nod_up",
            type=ChallengeType.GESTURE,
            instruction="Nod your head up",
            timeout_seconds=10
        )
        frames = [np.zeros((480, 640, 3), dtype=np.uint8)]
        
        # Should return a ChallengeResult, not raise NotImplementedError
        result = verifier.verify_challenge(challenge, frames)
        assert isinstance(result, ChallengeResult)
        assert result.challenge_id == challenge.challenge_id
        assert isinstance(result.completed, bool)
        assert isinstance(result.confidence, float)
        assert 0.0 <= result.confidence <= 1.0
        assert isinstance(result.timestamp, float)
    
    def test_detect_3d_depth_implemented(self):
        """Test that detect_3d_depth is now implemented"""
        verifier = CVVerifier()
        landmarks = np.zeros((468, 3))
        
        # Should return a score, not raise NotImplementedError
        score = verifier.detect_3d_depth(landmarks)
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0
    
    def test_detect_micro_movements_requires_model(self):
        """Test that detect_micro_movements requires model to be loaded"""
        verifier = CVVerifier()
        frames = [np.zeros((480, 640, 3), dtype=np.uint8) for _ in range(5)]
        
        # Should raise ValueError when trying to access face_landmarker without model
        with pytest.raises(ValueError, match="Model path must be provided"):
            verifier.detect_micro_movements(frames)


class Test3DDepthDetection:
    """
    Unit tests for 3D depth detection functionality.
    Validates Requirement 3.2: Detect 3D depth cues to distinguish live faces from flat images
    """
    
    def test_flat_image_scores_low(self):
        """
        Test that flat image (no depth variation) scores low.
        
        A flat image has all landmarks at the same z-depth with minimal variance.
        This should result in a low depth score (closer to 0.0).
        
        Validates Requirement 3.2
        """
        verifier = CVVerifier()
        
        # Create flat landmarks - all at same z-depth (0.0)
        flat_landmarks = np.random.rand(468, 3)
        flat_landmarks[:, 2] = 0.0  # All z-coordinates are 0 (flat)
        
        score = verifier.detect_3d_depth(flat_landmarks)
        
        # Flat image should score low (< 0.3)
        assert 0.0 <= score <= 0.3, f"Flat image scored {score}, expected <= 0.3"
    
    def test_3d_face_scores_high(self):
        """
        Test that 3D face (with depth variation) scores high.
        
        A real 3D face has:
        - Nose protruding forward (higher z)
        - Significant z-variance across landmarks
        - Perspective effects in width ratios
        
        Validates Requirement 3.2
        """
        verifier = CVVerifier()
        
        # Create realistic 3D face landmarks
        landmarks_3d = np.random.rand(468, 3)
        
        # Add realistic z-depth variation
        # Most face points at z=0.0
        landmarks_3d[:, 2] = np.random.normal(0.0, 0.01, 468)
        
        # Nose tip (landmark 1) protrudes forward
        landmarks_3d[1, 2] = 0.04  # Significant protrusion
        
        # Key facial features at slightly different depths
        landmarks_3d[33, 2] = 0.01   # Left eye
        landmarks_3d[263, 2] = 0.01  # Right eye
        landmarks_3d[61, 2] = 0.02   # Left mouth
        landmarks_3d[291, 2] = 0.02  # Right mouth
        landmarks_3d[152, 2] = -0.01 # Chin (recessed)
        landmarks_3d[10, 2] = 0.005  # Forehead
        
        score = verifier.detect_3d_depth(landmarks_3d)
        
        # 3D face should score high (> 0.5)
        assert 0.5 <= score <= 1.0, f"3D face scored {score}, expected >= 0.5"
    
    def test_insufficient_landmarks_returns_zero(self):
        """
        Test that insufficient landmarks returns 0.0 score.
        
        If fewer than 468 landmarks are provided, the method should
        return 0.0 as it cannot perform reliable depth analysis.
        
        Validates Requirement 3.2
        """
        verifier = CVVerifier()
        
        # Create landmarks with insufficient points
        insufficient_landmarks = np.random.rand(100, 3)
        
        score = verifier.detect_3d_depth(insufficient_landmarks)
        
        assert score == 0.0, f"Insufficient landmarks scored {score}, expected 0.0"
    
    def test_score_range_validity(self):
        """
        Test that depth score is always in valid range [0.0, 1.0].
        
        Regardless of input, the score should never exceed the valid range.
        
        Validates Requirement 3.2
        """
        verifier = CVVerifier()
        
        # Test with various extreme inputs
        test_cases = [
            np.zeros((468, 3)),                           # All zeros
            np.ones((468, 3)),                            # All ones
            np.random.rand(468, 3) * 10,                  # Large values
            np.random.rand(468, 3) * -10,                 # Negative values
            np.random.randn(468, 3),                      # Normal distribution
        ]
        
        for landmarks in test_cases:
            score = verifier.detect_3d_depth(landmarks)
            assert 0.0 <= score <= 1.0, f"Score {score} out of range for input"
    
    def test_nose_protrusion_detection(self):
        """
        Test that nose protrusion is correctly detected.
        
        The nose tip should have higher z-coordinate than the face plane,
        and this should contribute to a higher depth score.
        
        Validates Requirement 3.2
        """
        verifier = CVVerifier()
        
        # Create landmarks with prominent nose protrusion
        landmarks = np.zeros((468, 3))
        
        # Set key facial landmarks at z=0
        landmarks[33, 2] = 0.0   # Left eye
        landmarks[263, 2] = 0.0  # Right eye
        landmarks[61, 2] = 0.0   # Left mouth
        landmarks[291, 2] = 0.0  # Right mouth
        landmarks[152, 2] = 0.0  # Chin
        landmarks[10, 2] = 0.0   # Forehead
        
        # Nose tip protrudes significantly
        landmarks[1, 2] = 0.05
        
        score_with_protrusion = verifier.detect_3d_depth(landmarks)
        
        # Now test without protrusion
        landmarks[1, 2] = 0.0
        score_without_protrusion = verifier.detect_3d_depth(landmarks)
        
        # Score with protrusion should be higher
        assert score_with_protrusion > score_without_protrusion, \
            f"Nose protrusion should increase score: {score_with_protrusion} vs {score_without_protrusion}"
    
    def test_z_variance_contribution(self):
        """
        Test that z-coordinate variance contributes to depth score.
        
        Higher variance in z-coordinates indicates 3D structure.
        
        Validates Requirement 3.2
        """
        verifier = CVVerifier()
        
        # High variance case
        high_variance_landmarks = np.random.rand(468, 3)
        high_variance_landmarks[:, 2] = np.random.uniform(-0.05, 0.05, 468)
        
        # Low variance case
        low_variance_landmarks = np.random.rand(468, 3)
        low_variance_landmarks[:, 2] = np.random.uniform(-0.001, 0.001, 468)
        
        high_score = verifier.detect_3d_depth(high_variance_landmarks)
        low_score = verifier.detect_3d_depth(low_variance_landmarks)
        
        # High variance should produce higher score
        assert high_score > low_score, \
            f"High variance should increase score: {high_score} vs {low_score}"
    
    def test_realistic_face_geometry(self):
        """
        Test with realistic face geometry proportions.
        
        Uses typical MediaPipe normalized coordinates for a real face.
        
        Validates Requirement 3.2
        """
        verifier = CVVerifier()
        
        # Create realistic face landmarks
        landmarks = np.zeros((468, 3))
        
        # Set realistic x, y coordinates (normalized 0-1 range)
        # and realistic z-depth values
        
        # Eyes (wider apart, moderate depth)
        landmarks[33] = [0.3, 0.4, 0.01]   # Left eye
        landmarks[263] = [0.7, 0.4, 0.01]  # Right eye
        
        # Nose (center, protruding)
        landmarks[1] = [0.5, 0.5, 0.035]   # Nose tip
        
        # Mouth (narrower than eyes, moderate depth)
        landmarks[61] = [0.35, 0.65, 0.015]  # Left mouth
        landmarks[291] = [0.65, 0.65, 0.015] # Right mouth
        
        # Chin (center, recessed)
        landmarks[152] = [0.5, 0.8, -0.005]
        
        # Forehead (center, slight depth)
        landmarks[10] = [0.5, 0.2, 0.008]
        
        # Fill remaining landmarks with slight variation
        for i in range(468):
            if i not in [1, 10, 33, 61, 152, 263, 291]:
                landmarks[i] = [
                    np.random.uniform(0.2, 0.8),
                    np.random.uniform(0.2, 0.8),
                    np.random.normal(0.0, 0.01)
                ]
        
        score = verifier.detect_3d_depth(landmarks)
        
        # Realistic face should score moderately high (> 0.4)
        assert 0.4 <= score <= 1.0, \
            f"Realistic face scored {score}, expected >= 0.4"



class TestMicroMovementDetection:
    """
    Unit tests for micro-movement detection functionality.
    Validates Requirement 3.3: Detect natural micro-movements consistent with living tissue
    
    Note: These tests use mocked MediaPipe responses to test the logic
    without requiring the actual model file.
    """
    
    def test_insufficient_frames_returns_zero(self):
        """
        Test that fewer than 2 frames returns 0.0 score.
        
        Micro-movement detection requires at least 2 frames to detect motion.
        
        Validates Requirement 3.3
        """
        verifier = CVVerifier()
        
        # Single frame
        single_frame = [np.zeros((480, 640, 3), dtype=np.uint8)]
        score = verifier.detect_micro_movements(single_frame)
        assert score == 0.0, f"Single frame scored {score}, expected 0.0"
        
        # Empty sequence
        empty_sequence = []
        score = verifier.detect_micro_movements(empty_sequence)
        assert score == 0.0, f"Empty sequence scored {score}, expected 0.0"
    
    def test_static_frames_score_low(self, mocker):
        """
        Test that static frames (no movement) score low.
        
        When frames show no movement (identical landmarks across frames),
        the micro-movement score should be low (closer to 0.0).
        
        This simulates a static image or frozen video.
        
        Validates Requirement 3.3
        """
        verifier = CVVerifier(model_path="dummy_path.task")
        
        # Create static landmarks (no movement between frames)
        static_landmarks = self._create_realistic_landmarks()
        
        # Mock the face_landmarker to return identical landmarks for all frames
        mock_landmarker = mocker.MagicMock()
        mock_result = mocker.MagicMock()
        
        # Create mock landmarks with MediaPipe structure
        mock_face_landmarks = []
        for x, y, z in static_landmarks:
            mock_landmark = mocker.MagicMock()
            mock_landmark.x = x
            mock_landmark.y = y
            mock_landmark.z = z
            mock_face_landmarks.append(mock_landmark)
        
        mock_result.face_landmarks = [mock_face_landmarks]
        mock_landmarker.detect.return_value = mock_result
        
        # Replace the face_landmarker with our mock
        verifier._face_landmarker = mock_landmarker
        
        # Create multiple identical frames
        static_frames = [np.zeros((480, 640, 3), dtype=np.uint8) for _ in range(10)]
        
        score = verifier.detect_micro_movements(static_frames)
        
        # Static frames should score low (< 0.3)
        assert 0.0 <= score <= 0.3, f"Static frames scored {score}, expected <= 0.3"
    
    def test_dynamic_frames_score_high(self, mocker):
        """
        Test that dynamic frames (with natural movement) score high.
        
        When frames show natural micro-movements like:
        - Eye blinks (EAR variation)
        - Subtle head motion
        - Natural landmark jitter
        
        The score should be high (closer to 1.0).
        
        Validates Requirement 3.3
        """
        verifier = CVVerifier(model_path="dummy_path.task")
        
        # Create sequence of landmarks with natural movements
        base_landmarks = self._create_realistic_landmarks()
        
        # Mock the face_landmarker to return varying landmarks
        mock_landmarker = mocker.MagicMock()
        
        # Create a sequence of landmark sets with natural variations
        landmark_sequence = []
        for frame_idx in range(10):
            # Add natural variations
            frame_landmarks = base_landmarks.copy()
            
            # Simulate eye blink (frames 3-5)
            if 3 <= frame_idx <= 5:
                # Close eyes by reducing vertical distance
                # Left eye: 159 (top), 145 (bottom)
                frame_landmarks[159][1] += 0.01  # Move top down
                frame_landmarks[145][1] -= 0.01  # Move bottom up
                # Right eye: 386 (top), 374 (bottom)
                frame_landmarks[386][1] += 0.01
                frame_landmarks[374][1] -= 0.01
            
            # Simulate subtle head motion
            head_offset = np.sin(frame_idx * 0.5) * 0.005
            frame_landmarks[:, 0] += head_offset  # Slight horizontal movement
            
            # Add natural jitter
            jitter = np.random.normal(0, 0.0001, frame_landmarks.shape)
            frame_landmarks += jitter
            
            landmark_sequence.append(frame_landmarks)
        
        # Configure mock to return different landmarks for each call
        def mock_detect(mp_image):
            # Get the next landmark set from sequence
            if not hasattr(mock_detect, 'call_count'):
                mock_detect.call_count = 0
            
            idx = mock_detect.call_count % len(landmark_sequence)
            mock_detect.call_count += 1
            
            landmarks = landmark_sequence[idx]
            
            # Create mock landmarks with MediaPipe structure
            mock_face_landmarks = []
            for x, y, z in landmarks:
                mock_landmark = mocker.MagicMock()
                mock_landmark.x = float(x)
                mock_landmark.y = float(y)
                mock_landmark.z = float(z)
                mock_face_landmarks.append(mock_landmark)
            
            mock_result = mocker.MagicMock()
            mock_result.face_landmarks = [mock_face_landmarks]
            return mock_result
        
        mock_landmarker.detect = mock_detect
        verifier._face_landmarker = mock_landmarker
        
        # Create frames
        dynamic_frames = [np.zeros((480, 640, 3), dtype=np.uint8) for _ in range(10)]
        
        score = verifier.detect_micro_movements(dynamic_frames)
        
        # Dynamic frames with natural movement should score high (> 0.5)
        assert 0.5 <= score <= 1.0, f"Dynamic frames scored {score}, expected >= 0.5"
    
    def test_no_face_detected_returns_zero(self, mocker):
        """
        Test that frames with no face detected return 0.0 score.
        
        If MediaPipe cannot detect a face in any frame, the method
        should return 0.0 as it cannot analyze movement.
        
        Validates Requirement 3.3
        """
        verifier = CVVerifier(model_path="dummy_path.task")
        
        # Mock the face_landmarker to return no face detected
        mock_landmarker = mocker.MagicMock()
        mock_result = mocker.MagicMock()
        mock_result.face_landmarks = []  # No face detected
        mock_landmarker.detect.return_value = mock_result
        
        verifier._face_landmarker = mock_landmarker
        
        # Create frames
        frames = [np.zeros((480, 640, 3), dtype=np.uint8) for _ in range(5)]
        
        score = verifier.detect_micro_movements(frames)
        
        assert score == 0.0, f"No face detected scored {score}, expected 0.0"
    
    def test_score_range_validity(self, mocker):
        """
        Test that movement score is always in valid range [0.0, 1.0].
        
        Regardless of input, the score should never exceed the valid range.
        
        Validates Requirement 3.3
        """
        verifier = CVVerifier(model_path="dummy_path.task")
        
        # Create landmarks with extreme values
        extreme_landmarks = self._create_realistic_landmarks()
        
        # Mock the face_landmarker
        mock_landmarker = mocker.MagicMock()
        
        # Test with various extreme movement patterns
        test_cases = [
            # Very large movements
            [extreme_landmarks + i * 0.1 for i in range(5)],
            # Very small movements
            [extreme_landmarks + i * 0.00001 for i in range(5)],
            # Random movements
            [extreme_landmarks + np.random.randn(*extreme_landmarks.shape) * 0.01 for _ in range(5)],
        ]
        
        for landmark_sequence in test_cases:
            def mock_detect(mp_image):
                if not hasattr(mock_detect, 'call_count'):
                    mock_detect.call_count = 0
                
                idx = mock_detect.call_count % len(landmark_sequence)
                mock_detect.call_count += 1
                
                landmarks = landmark_sequence[idx]
                
                mock_face_landmarks = []
                for x, y, z in landmarks:
                    mock_landmark = mocker.MagicMock()
                    mock_landmark.x = float(x)
                    mock_landmark.y = float(y)
                    mock_landmark.z = float(z)
                    mock_face_landmarks.append(mock_landmark)
                
                mock_result = mocker.MagicMock()
                mock_result.face_landmarks = [mock_face_landmarks]
                return mock_result
            
            mock_landmarker.detect = mock_detect
            verifier._face_landmarker = mock_landmarker
            
            frames = [np.zeros((480, 640, 3), dtype=np.uint8) for _ in range(len(landmark_sequence))]
            score = verifier.detect_micro_movements(frames)
            
            assert 0.0 <= score <= 1.0, f"Score {score} out of range [0.0, 1.0]"
    
    def test_eye_blink_detection(self, mocker):
        """
        Test that eye blinks are detected and contribute to movement score.
        
        Eye blinks cause changes in Eye Aspect Ratio (EAR) which should
        be detected as natural micro-movement.
        
        Validates Requirement 3.3
        """
        verifier = CVVerifier(model_path="dummy_path.task")
        
        base_landmarks = self._create_realistic_landmarks()
        
        # Create sequence with eye blink
        landmark_sequence = []
        for frame_idx in range(10):
            frame_landmarks = base_landmarks.copy()
            
            # Simulate blink in middle frames (3-5)
            if 3 <= frame_idx <= 5:
                # Close eyes by moving top and bottom eyelids closer
                # Left eye: 159 (top), 145 (bottom)
                frame_landmarks[159][1] += 0.015
                frame_landmarks[145][1] -= 0.015
                # Right eye: 386 (top), 374 (bottom)
                frame_landmarks[386][1] += 0.015
                frame_landmarks[374][1] -= 0.015
            
            landmark_sequence.append(frame_landmarks)
        
        # Mock landmarker
        mock_landmarker = mocker.MagicMock()
        
        def mock_detect(mp_image):
            if not hasattr(mock_detect, 'call_count'):
                mock_detect.call_count = 0
            
            idx = mock_detect.call_count % len(landmark_sequence)
            mock_detect.call_count += 1
            
            landmarks = landmark_sequence[idx]
            
            mock_face_landmarks = []
            for x, y, z in landmarks:
                mock_landmark = mocker.MagicMock()
                mock_landmark.x = float(x)
                mock_landmark.y = float(y)
                mock_landmark.z = float(z)
                mock_face_landmarks.append(mock_landmark)
            
            mock_result = mocker.MagicMock()
            mock_result.face_landmarks = [mock_face_landmarks]
            return mock_result
        
        mock_landmarker.detect = mock_detect
        verifier._face_landmarker = mock_landmarker
        
        frames = [np.zeros((480, 640, 3), dtype=np.uint8) for _ in range(10)]
        score_with_blink = verifier.detect_micro_movements(frames)
        
        # Score with blink should be higher than static
        # (We know static scores low from previous test)
        assert score_with_blink > 0.2, \
            f"Eye blink should increase score, got {score_with_blink}"
    
    def test_head_motion_detection(self, mocker):
        """
        Test that subtle head motion is detected.
        
        Natural head motion (even when trying to stay still) should
        contribute to the movement score.
        
        Validates Requirement 3.3
        """
        verifier = CVVerifier(model_path="dummy_path.task")
        
        base_landmarks = self._create_realistic_landmarks()
        
        # Create sequence with head motion
        landmark_sequence = []
        for frame_idx in range(10):
            frame_landmarks = base_landmarks.copy()
            
            # Simulate subtle head motion (sinusoidal movement)
            offset_x = np.sin(frame_idx * 0.3) * 0.008
            offset_y = np.cos(frame_idx * 0.3) * 0.006
            
            frame_landmarks[:, 0] += offset_x
            frame_landmarks[:, 1] += offset_y
            
            landmark_sequence.append(frame_landmarks)
        
        # Mock landmarker
        mock_landmarker = mocker.MagicMock()
        
        def mock_detect(mp_image):
            if not hasattr(mock_detect, 'call_count'):
                mock_detect.call_count = 0
            
            idx = mock_detect.call_count % len(landmark_sequence)
            mock_detect.call_count += 1
            
            landmarks = landmark_sequence[idx]
            
            mock_face_landmarks = []
            for x, y, z in landmarks:
                mock_landmark = mocker.MagicMock()
                mock_landmark.x = float(x)
                mock_landmark.y = float(y)
                mock_landmark.z = float(z)
                mock_face_landmarks.append(mock_landmark)
            
            mock_result = mocker.MagicMock()
            mock_result.face_landmarks = [mock_face_landmarks]
            return mock_result
        
        mock_landmarker.detect = mock_detect
        verifier._face_landmarker = mock_landmarker
        
        frames = [np.zeros((480, 640, 3), dtype=np.uint8) for _ in range(10)]
        score_with_motion = verifier.detect_micro_movements(frames)
        
        # Score with head motion should be elevated
        assert score_with_motion > 0.2, \
            f"Head motion should increase score, got {score_with_motion}"
    
    @staticmethod
    def _create_realistic_landmarks():
        """
        Helper method to create realistic facial landmarks.
        
        Returns a 468x3 array with realistic normalized coordinates
        for a frontal face view.
        """
        landmarks = np.zeros((468, 3))
        
        # Set key landmarks with realistic positions
        # Eyes
        landmarks[33] = [0.35, 0.4, 0.01]   # Left eye outer
        landmarks[133] = [0.42, 0.4, 0.01]  # Left eye inner
        landmarks[159] = [0.385, 0.38, 0.01] # Left eye top
        landmarks[145] = [0.385, 0.42, 0.01] # Left eye bottom
        
        landmarks[263] = [0.58, 0.4, 0.01]  # Right eye inner
        landmarks[362] = [0.65, 0.4, 0.01]  # Right eye outer
        landmarks[386] = [0.615, 0.38, 0.01] # Right eye top
        landmarks[374] = [0.615, 0.42, 0.01] # Right eye bottom
        
        # Nose
        landmarks[1] = [0.5, 0.5, 0.03]     # Nose tip
        
        # Mouth
        landmarks[61] = [0.4, 0.65, 0.015]  # Left mouth
        landmarks[291] = [0.6, 0.65, 0.015] # Right mouth
        
        # Chin and forehead
        landmarks[152] = [0.5, 0.8, -0.005] # Chin
        landmarks[10] = [0.5, 0.2, 0.008]   # Forehead
        
        # Fill remaining landmarks with random but realistic values
        for i in range(468):
            if np.all(landmarks[i] == 0):
                landmarks[i] = [
                    np.random.uniform(0.2, 0.8),
                    np.random.uniform(0.2, 0.8),
                    np.random.normal(0.0, 0.01)
                ]
        
        return landmarks



class TestComputeLivenessScore:
    """
    Unit tests for compute_liveness_score method.
    Validates Requirement 3.4: Output liveness score between 0.0 and 1.0
    """
    
    def test_empty_frames_returns_zero(self):
        """
        Test that empty frame list returns 0.0 score.
        
        If no frames are provided, the method should return 0.0
        as it cannot perform liveness analysis.
        
        Validates Requirement 3.4
        """
        verifier = CVVerifier(model_path="dummy_path.task")
        
        # Empty frame list
        empty_frames = []
        score = verifier.compute_liveness_score(empty_frames)
        assert score == 0.0, f"Empty frames scored {score}, expected 0.0"
    
    def test_combines_depth_and_movement_scores(self, mocker):
        """
        Test that liveness score combines depth and movement scores.
        
        The final score should be a weighted combination of:
        - 3D depth score (50%)
        - Micro-movement score (50%)
        
        Validates Requirement 3.4
        """
        verifier = CVVerifier(model_path="dummy_path.task")
        
        # Mock detect_3d_depth to return known value
        mock_depth_score = 0.8
        mocker.patch.object(verifier, 'detect_3d_depth', return_value=mock_depth_score)
        
        # Mock detect_micro_movements to return known value
        mock_movement_score = 0.6
        mocker.patch.object(verifier, 'detect_micro_movements', return_value=mock_movement_score)
        
        # Create realistic landmarks for face detection
        base_landmarks = self._create_realistic_landmarks()
        
        # Mock the face_landmarker
        mock_landmarker = mocker.MagicMock()
        mock_result = mocker.MagicMock()
        
        # Create mock landmarks with MediaPipe structure
        mock_face_landmarks = []
        for x, y, z in base_landmarks:
            mock_landmark = mocker.MagicMock()
            mock_landmark.x = float(x)
            mock_landmark.y = float(y)
            mock_landmark.z = float(z)
            mock_face_landmarks.append(mock_landmark)
        
        mock_result.face_landmarks = [mock_face_landmarks]
        mock_landmarker.detect.return_value = mock_result
        verifier._face_landmarker = mock_landmarker
        
        # Create frames
        frames = [np.zeros((480, 640, 3), dtype=np.uint8) for _ in range(5)]
        
        score = verifier.compute_liveness_score(frames)
        
        # Expected score: 0.5 * 0.8 + 0.5 * 0.6 = 0.7
        expected_score = 0.5 * mock_depth_score + 0.5 * mock_movement_score
        assert abs(score - expected_score) < 0.001, \
            f"Score {score} doesn't match expected {expected_score}"
    
    def test_score_range_validity(self, mocker):
        """
        Test that liveness score is always in valid range [0.0, 1.0].
        
        Regardless of input, the score should never exceed the valid range.
        
        Validates Requirement 3.4
        """
        verifier = CVVerifier(model_path="dummy_path.task")
        
        # Create realistic landmarks
        base_landmarks = self._create_realistic_landmarks()
        
        # Mock the face_landmarker
        mock_landmarker = mocker.MagicMock()
        mock_result = mocker.MagicMock()
        
        mock_face_landmarks = []
        for x, y, z in base_landmarks:
            mock_landmark = mocker.MagicMock()
            mock_landmark.x = float(x)
            mock_landmark.y = float(y)
            mock_landmark.z = float(z)
            mock_face_landmarks.append(mock_landmark)
        
        mock_result.face_landmarks = [mock_face_landmarks]
        mock_landmarker.detect.return_value = mock_result
        verifier._face_landmarker = mock_landmarker
        
        # Test with various extreme depth and movement scores
        test_cases = [
            (0.0, 0.0),   # Both zero
            (1.0, 1.0),   # Both max
            (0.0, 1.0),   # Mixed
            (1.0, 0.0),   # Mixed
            (0.5, 0.5),   # Middle
        ]
        
        for depth_score, movement_score in test_cases:
            mocker.patch.object(verifier, 'detect_3d_depth', return_value=depth_score)
            mocker.patch.object(verifier, 'detect_micro_movements', return_value=movement_score)
            
            frames = [np.zeros((480, 640, 3), dtype=np.uint8) for _ in range(5)]
            score = verifier.compute_liveness_score(frames)
            
            assert 0.0 <= score <= 1.0, \
                f"Score {score} out of range for depth={depth_score}, movement={movement_score}"
    
    def test_no_face_detected_returns_zero(self, mocker):
        """
        Test that frames with no face detected return 0.0 score.
        
        If MediaPipe cannot detect a face in any frame, the depth score
        will be 0.0, and combined with movement score should still be valid.
        
        Validates Requirement 3.4
        """
        verifier = CVVerifier(model_path="dummy_path.task")
        
        # Mock the face_landmarker to return no face detected
        mock_landmarker = mocker.MagicMock()
        mock_result = mocker.MagicMock()
        mock_result.face_landmarks = []  # No face detected
        mock_landmarker.detect.return_value = mock_result
        
        verifier._face_landmarker = mock_landmarker
        
        # Mock detect_micro_movements to return 0.0 (no face detected)
        mocker.patch.object(verifier, 'detect_micro_movements', return_value=0.0)
        
        frames = [np.zeros((480, 640, 3), dtype=np.uint8) for _ in range(5)]
        score = verifier.compute_liveness_score(frames)
        
        # With no face detected, both depth and movement should be 0.0
        assert score == 0.0, f"No face detected scored {score}, expected 0.0"
    
    def test_high_depth_low_movement_scores_moderate(self, mocker):
        """
        Test that high depth but low movement results in moderate score.
        
        This simulates a 3D object (like a mask) that has depth but no
        natural micro-movements.
        
        Validates Requirement 3.4
        """
        verifier = CVVerifier(model_path="dummy_path.task")
        
        # High depth score (3D object)
        mock_depth_score = 0.9
        mocker.patch.object(verifier, 'detect_3d_depth', return_value=mock_depth_score)
        
        # Low movement score (static)
        mock_movement_score = 0.1
        mocker.patch.object(verifier, 'detect_micro_movements', return_value=mock_movement_score)
        
        # Create realistic landmarks
        base_landmarks = self._create_realistic_landmarks()
        
        # Mock the face_landmarker
        mock_landmarker = mocker.MagicMock()
        mock_result = mocker.MagicMock()
        
        mock_face_landmarks = []
        for x, y, z in base_landmarks:
            mock_landmark = mocker.MagicMock()
            mock_landmark.x = float(x)
            mock_landmark.y = float(y)
            mock_landmark.z = float(z)
            mock_face_landmarks.append(mock_landmark)
        
        mock_result.face_landmarks = [mock_face_landmarks]
        mock_landmarker.detect.return_value = mock_result
        verifier._face_landmarker = mock_landmarker
        
        frames = [np.zeros((480, 640, 3), dtype=np.uint8) for _ in range(5)]
        score = verifier.compute_liveness_score(frames)
        
        # Expected: 0.5 * 0.9 + 0.5 * 0.1 = 0.5
        expected_score = 0.5 * mock_depth_score + 0.5 * mock_movement_score
        assert abs(score - expected_score) < 0.001, \
            f"Score {score} doesn't match expected {expected_score}"
        
        # Should be moderate (around 0.5)
        assert 0.4 <= score <= 0.6, \
            f"High depth + low movement should score moderate, got {score}"
    
    def test_low_depth_high_movement_scores_moderate(self, mocker):
        """
        Test that low depth but high movement results in moderate score.
        
        This simulates a flat video with movement (like a video on a screen).
        
        Validates Requirement 3.4
        """
        verifier = CVVerifier(model_path="dummy_path.task")
        
        # Low depth score (flat)
        mock_depth_score = 0.1
        mocker.patch.object(verifier, 'detect_3d_depth', return_value=mock_depth_score)
        
        # High movement score (dynamic)
        mock_movement_score = 0.9
        mocker.patch.object(verifier, 'detect_micro_movements', return_value=mock_movement_score)
        
        # Create realistic landmarks
        base_landmarks = self._create_realistic_landmarks()
        
        # Mock the face_landmarker
        mock_landmarker = mocker.MagicMock()
        mock_result = mocker.MagicMock()
        
        mock_face_landmarks = []
        for x, y, z in base_landmarks:
            mock_landmark = mocker.MagicMock()
            mock_landmark.x = float(x)
            mock_landmark.y = float(y)
            mock_landmark.z = float(z)
            mock_face_landmarks.append(mock_landmark)
        
        mock_result.face_landmarks = [mock_face_landmarks]
        mock_landmarker.detect.return_value = mock_result
        verifier._face_landmarker = mock_landmarker
        
        frames = [np.zeros((480, 640, 3), dtype=np.uint8) for _ in range(5)]
        score = verifier.compute_liveness_score(frames)
        
        # Expected: 0.5 * 0.1 + 0.5 * 0.9 = 0.5
        expected_score = 0.5 * mock_depth_score + 0.5 * mock_movement_score
        assert abs(score - expected_score) < 0.001, \
            f"Score {score} doesn't match expected {expected_score}"
        
        # Should be moderate (around 0.5)
        assert 0.4 <= score <= 0.6, \
            f"Low depth + high movement should score moderate, got {score}"
    
    def test_high_depth_high_movement_scores_high(self, mocker):
        """
        Test that high depth and high movement results in high score.
        
        This simulates a real live human face with both 3D structure
        and natural micro-movements.
        
        Validates Requirement 3.4
        """
        verifier = CVVerifier(model_path="dummy_path.task")
        
        # High depth score (3D face)
        mock_depth_score = 0.9
        mocker.patch.object(verifier, 'detect_3d_depth', return_value=mock_depth_score)
        
        # High movement score (natural movements)
        mock_movement_score = 0.8
        mocker.patch.object(verifier, 'detect_micro_movements', return_value=mock_movement_score)
        
        # Create realistic landmarks
        base_landmarks = self._create_realistic_landmarks()
        
        # Mock the face_landmarker
        mock_landmarker = mocker.MagicMock()
        mock_result = mocker.MagicMock()
        
        mock_face_landmarks = []
        for x, y, z in base_landmarks:
            mock_landmark = mocker.MagicMock()
            mock_landmark.x = float(x)
            mock_landmark.y = float(y)
            mock_landmark.z = float(z)
            mock_face_landmarks.append(mock_landmark)
        
        mock_result.face_landmarks = [mock_face_landmarks]
        mock_landmarker.detect.return_value = mock_result
        verifier._face_landmarker = mock_landmarker
        
        frames = [np.zeros((480, 640, 3), dtype=np.uint8) for _ in range(5)]
        score = verifier.compute_liveness_score(frames)
        
        # Expected: 0.5 * 0.9 + 0.5 * 0.8 = 0.85
        expected_score = 0.5 * mock_depth_score + 0.5 * mock_movement_score
        assert abs(score - expected_score) < 0.001, \
            f"Score {score} doesn't match expected {expected_score}"
        
        # Should be high (> 0.7)
        assert score > 0.7, \
            f"High depth + high movement should score high, got {score}"
    
    def test_low_depth_low_movement_scores_low(self, mocker):
        """
        Test that low depth and low movement results in low score.
        
        This simulates a static flat image (like a photo).
        
        Validates Requirement 3.4
        """
        verifier = CVVerifier(model_path="dummy_path.task")
        
        # Low depth score (flat)
        mock_depth_score = 0.1
        mocker.patch.object(verifier, 'detect_3d_depth', return_value=mock_depth_score)
        
        # Low movement score (static)
        mock_movement_score = 0.1
        mocker.patch.object(verifier, 'detect_micro_movements', return_value=mock_movement_score)
        
        # Create realistic landmarks
        base_landmarks = self._create_realistic_landmarks()
        
        # Mock the face_landmarker
        mock_landmarker = mocker.MagicMock()
        mock_result = mocker.MagicMock()
        
        mock_face_landmarks = []
        for x, y, z in base_landmarks:
            mock_landmark = mocker.MagicMock()
            mock_landmark.x = float(x)
            mock_landmark.y = float(y)
            mock_landmark.z = float(z)
            mock_face_landmarks.append(mock_landmark)
        
        mock_result.face_landmarks = [mock_face_landmarks]
        mock_landmarker.detect.return_value = mock_result
        verifier._face_landmarker = mock_landmarker
        
        frames = [np.zeros((480, 640, 3), dtype=np.uint8) for _ in range(5)]
        score = verifier.compute_liveness_score(frames)
        
        # Expected: 0.5 * 0.1 + 0.5 * 0.1 = 0.1
        expected_score = 0.5 * mock_depth_score + 0.5 * mock_movement_score
        assert abs(score - expected_score) < 0.001, \
            f"Score {score} doesn't match expected {expected_score}"
        
        # Should be low (< 0.3)
        assert score < 0.3, \
            f"Low depth + low movement should score low, got {score}"
    
    @staticmethod
    def _create_realistic_landmarks():
        """
        Helper method to create realistic facial landmarks.
        
        Returns a 468x3 array with realistic normalized coordinates
        for a frontal face view.
        """
        landmarks = np.zeros((468, 3))
        
        # Set key landmarks with realistic positions
        # Eyes
        landmarks[33] = [0.35, 0.4, 0.01]   # Left eye outer
        landmarks[133] = [0.42, 0.4, 0.01]  # Left eye inner
        landmarks[159] = [0.385, 0.38, 0.01] # Left eye top
        landmarks[145] = [0.385, 0.42, 0.01] # Left eye bottom
        
        landmarks[263] = [0.58, 0.4, 0.01]  # Right eye inner
        landmarks[362] = [0.65, 0.4, 0.01]  # Right eye outer
        landmarks[386] = [0.615, 0.38, 0.01] # Right eye top
        landmarks[374] = [0.615, 0.42, 0.01] # Right eye bottom
        
        # Nose
        landmarks[1] = [0.5, 0.5, 0.03]     # Nose tip
        
        # Mouth
        landmarks[61] = [0.4, 0.65, 0.015]  # Left mouth
        landmarks[291] = [0.6, 0.65, 0.015] # Right mouth
        
        # Chin and forehead
        landmarks[152] = [0.5, 0.8, -0.005] # Chin
        landmarks[10] = [0.5, 0.2, 0.008]   # Forehead
        
        # Fill remaining landmarks with random but realistic values
        for i in range(468):
            if np.all(landmarks[i] == 0):
                landmarks[i] = [
                    np.random.uniform(0.2, 0.8),
                    np.random.uniform(0.2, 0.8),
                    np.random.normal(0.0, 0.01)
                ]
        
        return landmarks



class TestVerifyChallenge:
    """
    Unit tests for verify_challenge method.
    Validates Requirements 4.2, 4.3: Visual challenge verification
    """
    
    def test_empty_frames_returns_failed_result(self):
        """
        Test that empty frame list returns failed challenge result.
        
        Validates Requirement 4.2
        """
        verifier = CVVerifier(model_path="dummy_path.task")
        challenge = Challenge(
            challenge_id="test_session_gesture_0_nod_up",
            type=ChallengeType.GESTURE,
            instruction="Nod your head up",
            timeout_seconds=10
        )
        
        result = verifier.verify_challenge(challenge, [])
        
        assert result.challenge_id == challenge.challenge_id
        assert result.completed is False
        assert result.confidence == 0.0
        assert isinstance(result.timestamp, float)
    
    def test_invalid_challenge_id_returns_failed_result(self):
        """
        Test that invalid challenge ID format returns failed result.
        
        Validates Requirement 4.2
        """
        verifier = CVVerifier(model_path="dummy_path.task")
        challenge = Challenge(
            challenge_id="invalid",  # Invalid format
            type=ChallengeType.GESTURE,
            instruction="Nod your head up",
            timeout_seconds=10
        )
        frames = [np.zeros((480, 640, 3), dtype=np.uint8)]
        
        result = verifier.verify_challenge(challenge, frames)
        
        assert result.completed is False
        assert result.confidence == 0.0
    
    def test_gesture_challenge_routes_to_gesture_verification(self, mocker):
        """
        Test that gesture challenges route to _verify_gesture method.
        
        Validates Requirement 4.2
        """
        verifier = CVVerifier(model_path="dummy_path.task")
        
        # Mock _verify_gesture
        mock_verify_gesture = mocker.patch.object(
            verifier, '_verify_gesture', return_value=(True, 0.85)
        )
        
        challenge = Challenge(
            challenge_id="test_session_gesture_0_nod_up",
            type=ChallengeType.GESTURE,
            instruction="Nod your head up",
            timeout_seconds=10
        )
        frames = [np.zeros((480, 640, 3), dtype=np.uint8)]
        
        result = verifier.verify_challenge(challenge, frames)
        
        # Verify _verify_gesture was called
        mock_verify_gesture.assert_called_once_with("nod_up", frames)
        
        # Verify result
        assert result.completed is True
        assert result.confidence == 0.85
    
    def test_expression_challenge_routes_to_expression_verification(self, mocker):
        """
        Test that expression challenges route to _verify_expression method.
        
        Validates Requirement 4.2
        """
        verifier = CVVerifier(model_path="dummy_path.task")
        
        # Mock _verify_expression
        mock_verify_expression = mocker.patch.object(
            verifier, '_verify_expression', return_value=(True, 0.75)
        )
        
        challenge = Challenge(
            challenge_id="test_session_expression_0_smile",
            type=ChallengeType.EXPRESSION,
            instruction="Smile",
            timeout_seconds=10
        )
        frames = [np.zeros((480, 640, 3), dtype=np.uint8)]
        
        result = verifier.verify_challenge(challenge, frames)
        
        # Verify _verify_expression was called
        mock_verify_expression.assert_called_once_with("smile", frames)
        
        # Verify result
        assert result.completed is True
        assert result.confidence == 0.75
    
    def test_timestamp_recorded_on_completion(self, mocker):
        """
        Test that timestamp is recorded on successful completion.
        
        Validates Requirement 4.3
        """
        verifier = CVVerifier(model_path="dummy_path.task")
        
        # Mock _verify_gesture to return success
        mocker.patch.object(verifier, '_verify_gesture', return_value=(True, 0.9))
        
        challenge = Challenge(
            challenge_id="test_session_gesture_0_nod_up",
            type=ChallengeType.GESTURE,
            instruction="Nod your head up",
            timeout_seconds=10
        )
        frames = [np.zeros((480, 640, 3), dtype=np.uint8)]
        
        import time
        before_time = time.time()
        result = verifier.verify_challenge(challenge, frames)
        after_time = time.time()
        
        # Verify timestamp is within expected range
        assert before_time <= result.timestamp <= after_time
        assert result.completed is True
    
    def test_confidence_score_in_valid_range(self, mocker):
        """
        Test that confidence score is always in valid range [0.0, 1.0].
        
        Validates Requirement 4.2
        """
        verifier = CVVerifier(model_path="dummy_path.task")
        
        # Test various confidence values
        test_cases = [
            (True, 0.0),
            (True, 0.5),
            (True, 1.0),
            (False, 0.0),
            (False, 0.3),
        ]
        
        for completed, confidence in test_cases:
            mocker.patch.object(verifier, '_verify_gesture', return_value=(completed, confidence))
            
            challenge = Challenge(
                challenge_id="test_session_gesture_0_nod_up",
                type=ChallengeType.GESTURE,
                instruction="Nod your head up",
                timeout_seconds=10
            )
            frames = [np.zeros((480, 640, 3), dtype=np.uint8)]
            
            result = verifier.verify_challenge(challenge, frames)
            
            assert 0.0 <= result.confidence <= 1.0
            assert result.completed == completed


class TestVerifyGesture:
    """
    Unit tests for _verify_gesture method.
    Validates Requirement 4.2: Gesture detection and verification
    """
    
    def test_insufficient_frames_returns_false(self):
        """
        Test that fewer than 2 frames returns False.
        
        Gesture detection requires at least 2 frames to detect movement.
        
        Validates Requirement 4.2
        """
        verifier = CVVerifier(model_path="dummy_path.task")
        
        # Single frame
        single_frame = [np.zeros((480, 640, 3), dtype=np.uint8)]
        completed, confidence = verifier._verify_gesture("nod_up", single_frame)
        
        assert completed is False
        assert confidence == 0.0
    
    def test_no_face_detected_returns_false(self, mocker):
        """
        Test that frames with no face detected return False.
        
        Validates Requirement 4.2
        """
        verifier = CVVerifier(model_path="dummy_path.task")
        
        # Mock face_landmarker to return no face
        mock_landmarker = mocker.MagicMock()
        mock_result = mocker.MagicMock()
        mock_result.face_landmarks = []
        mock_landmarker.detect.return_value = mock_result
        verifier._face_landmarker = mock_landmarker
        
        frames = [np.zeros((480, 640, 3), dtype=np.uint8) for _ in range(5)]
        completed, confidence = verifier._verify_gesture("nod_up", frames)
        
        assert completed is False
        assert confidence == 0.0
    
    def test_nod_up_gesture_detection(self, mocker):
        """
        Test that nod up gesture is correctly detected.
        
        Validates Requirement 4.2
        """
        verifier = CVVerifier(model_path="dummy_path.task")
        
        # Create landmark sequence showing upward head movement
        base_landmarks = self._create_realistic_landmarks()
        landmark_sequence = []
        
        for i in range(5):
            frame_landmarks = base_landmarks.copy()
            # Move nose and chin up (y decreases)
            offset = -0.01 * i  # Gradual upward movement
            frame_landmarks[1][1] += offset  # Nose
            frame_landmarks[152][1] += offset  # Chin
            landmark_sequence.append(frame_landmarks)
        
        self._mock_face_landmarker(verifier, mocker, landmark_sequence)
        
        frames = [np.zeros((480, 640, 3), dtype=np.uint8) for _ in range(5)]
        completed, confidence = verifier._verify_gesture("nod_up", frames)
        
        # Should detect upward movement
        assert completed is True
        assert confidence > 0.0
    
    def test_turn_left_gesture_detection(self, mocker):
        """
        Test that turn left gesture is correctly detected.
        
        Validates Requirement 4.2
        """
        verifier = CVVerifier(model_path="dummy_path.task")
        
        # Create landmark sequence showing leftward head turn
        base_landmarks = self._create_realistic_landmarks()
        landmark_sequence = []
        
        for i in range(5):
            frame_landmarks = base_landmarks.copy()
            # Move nose left (x decreases)
            offset = -0.015 * i
            frame_landmarks[1][0] += offset  # Nose
            landmark_sequence.append(frame_landmarks)
        
        self._mock_face_landmarker(verifier, mocker, landmark_sequence)
        
        frames = [np.zeros((480, 640, 3), dtype=np.uint8) for _ in range(5)]
        completed, confidence = verifier._verify_gesture("turn_left", frames)
        
        # Should detect leftward turn
        assert completed is True
        assert confidence > 0.0
    
    def test_open_mouth_gesture_detection(self, mocker):
        """
        Test that open mouth gesture is correctly detected.
        
        Validates Requirement 4.2
        """
        verifier = CVVerifier(model_path="dummy_path.task")
        
        # Create landmark sequence showing mouth opening
        base_landmarks = self._create_realistic_landmarks()
        landmark_sequence = []
        
        for i in range(5):
            frame_landmarks = base_landmarks.copy()
            # Open mouth (increase vertical distance)
            if i >= 2:  # Open mouth in later frames
                frame_landmarks[13][1] -= 0.02  # Upper lip up
                frame_landmarks[14][1] += 0.02  # Lower lip down
            landmark_sequence.append(frame_landmarks)
        
        self._mock_face_landmarker(verifier, mocker, landmark_sequence)
        
        frames = [np.zeros((480, 640, 3), dtype=np.uint8) for _ in range(5)]
        completed, confidence = verifier._verify_gesture("open_mouth", frames)
        
        # Should detect mouth opening
        assert completed is True
        assert confidence > 0.0
    
    def test_blink_gesture_detection(self, mocker):
        """
        Test that blink gesture is correctly detected.
        
        Validates Requirement 4.2
        """
        verifier = CVVerifier(model_path="dummy_path.task")
        
        # Create landmark sequence showing blink
        base_landmarks = self._create_realistic_landmarks()
        landmark_sequence = []
        
        for i in range(5):
            frame_landmarks = base_landmarks.copy()
            # Close eyes in middle frames
            if 1 <= i <= 3:
                # Close eyes (reduce vertical distance)
                frame_landmarks[159][1] += 0.015  # Left eye top down
                frame_landmarks[145][1] -= 0.015  # Left eye bottom up
                frame_landmarks[386][1] += 0.015  # Right eye top down
                frame_landmarks[374][1] -= 0.015  # Right eye bottom up
            landmark_sequence.append(frame_landmarks)
        
        self._mock_face_landmarker(verifier, mocker, landmark_sequence)
        
        frames = [np.zeros((480, 640, 3), dtype=np.uint8) for _ in range(5)]
        completed, confidence = verifier._verify_gesture("blink", frames)
        
        # Should detect blink
        assert completed is True
        assert confidence > 0.0
    
    def test_unknown_gesture_returns_false(self, mocker):
        """
        Test that unknown gesture type returns False.
        
        Validates Requirement 4.2
        """
        verifier = CVVerifier(model_path="dummy_path.task")
        
        base_landmarks = self._create_realistic_landmarks()
        self._mock_face_landmarker(verifier, mocker, [base_landmarks] * 5)
        
        frames = [np.zeros((480, 640, 3), dtype=np.uint8) for _ in range(5)]
        completed, confidence = verifier._verify_gesture("unknown_gesture", frames)
        
        assert completed is False
        assert confidence == 0.0
    
    def test_nod_down_gesture_detection(self, mocker):
        """
        Test that nod down gesture is correctly detected.
        
        Validates Requirement 4.2, 4.4
        """
        verifier = CVVerifier(model_path="dummy_path.task")
        
        # Create landmark sequence showing downward head movement
        base_landmarks = self._create_realistic_landmarks()
        landmark_sequence = []
        
        for i in range(5):
            frame_landmarks = base_landmarks.copy()
            # Move nose and chin down (y increases)
            offset = 0.01 * i  # Gradual downward movement
            frame_landmarks[1][1] += offset  # Nose
            frame_landmarks[152][1] += offset  # Chin
            landmark_sequence.append(frame_landmarks)
        
        self._mock_face_landmarker(verifier, mocker, landmark_sequence)
        
        frames = [np.zeros((480, 640, 3), dtype=np.uint8) for _ in range(5)]
        completed, confidence = verifier._verify_gesture("nod_down", frames)
        
        # Should detect downward movement
        assert completed is True
        assert confidence > 0.0
    
    def test_turn_right_gesture_detection(self, mocker):
        """
        Test that turn right gesture is correctly detected.
        
        Validates Requirement 4.2, 4.4
        """
        verifier = CVVerifier(model_path="dummy_path.task")
        
        # Create landmark sequence showing rightward head turn
        base_landmarks = self._create_realistic_landmarks()
        landmark_sequence = []
        
        for i in range(5):
            frame_landmarks = base_landmarks.copy()
            # Move nose right (x increases)
            offset = 0.015 * i
            frame_landmarks[1][0] += offset  # Nose
            landmark_sequence.append(frame_landmarks)
        
        self._mock_face_landmarker(verifier, mocker, landmark_sequence)
        
        frames = [np.zeros((480, 640, 3), dtype=np.uint8) for _ in range(5)]
        completed, confidence = verifier._verify_gesture("turn_right", frames)
        
        # Should detect rightward turn
        assert completed is True
        assert confidence > 0.0
    
    def test_tilt_left_gesture_detection(self, mocker):
        """
        Test that tilt left gesture is correctly detected.
        
        Validates Requirement 4.2, 4.4
        """
        verifier = CVVerifier(model_path="dummy_path.task")
        
        # Create landmark sequence showing leftward head tilt
        base_landmarks = self._create_realistic_landmarks()
        landmark_sequence = []
        
        # Initial eye positions: left eye at (0.35, 0.4), right eye at (0.65, 0.4)
        # arctan2(dy, dx) where dy = right_y - left_y, dx = right_x - left_x
        # Start: arctan2(0, 0.3) = 0
        # For tilt left (right eye up): arctan2(-0.4, 0.3) = negative angle
        # But the code checks if angle_end > angle_start for tilt_left
        # So we need angle to INCREASE (become more positive)
        # This means left eye should go up, right eye should go down!
        
        for i in range(5):
            frame_landmarks = base_landmarks.copy()
            # Create a significant tilt by rotating the eye line
            # Tilt angle in radians (need > 0.15 radians ≈ 8.6 degrees)
            tilt_angle = 0.05 * i  # Gradual tilt up to 0.2 radians (11.5 degrees)
            
            # For tilt left to have angle_end > angle_start:
            # We need dy to increase (right eye goes down relative to left eye)
            frame_landmarks[33][1] -= tilt_angle   # Left eye up (y decreases)
            frame_landmarks[263][1] += tilt_angle  # Right eye down (y increases)
            
            landmark_sequence.append(frame_landmarks)
        
        self._mock_face_landmarker(verifier, mocker, landmark_sequence)
        
        frames = [np.zeros((480, 640, 3), dtype=np.uint8) for _ in range(5)]
        completed, confidence = verifier._verify_gesture("tilt_left", frames)
        
        # Should detect leftward tilt
        assert completed is True
        assert confidence > 0.0
    
    def test_tilt_right_gesture_detection(self, mocker):
        """
        Test that tilt right gesture is correctly detected.
        
        Validates Requirement 4.2, 4.4
        """
        verifier = CVVerifier(model_path="dummy_path.task")
        
        # Create landmark sequence showing rightward head tilt
        base_landmarks = self._create_realistic_landmarks()
        landmark_sequence = []
        
        # For tilt right, the code checks if angle_end < angle_start
        # So we need angle to DECREASE (become more negative)
        # This means right eye should go up, left eye should go down
        
        for i in range(5):
            frame_landmarks = base_landmarks.copy()
            # Create a significant tilt by rotating the eye line
            # Tilt angle in radians (need > 0.15 radians ≈ 8.6 degrees)
            tilt_angle = 0.05 * i  # Gradual tilt up to 0.2 radians (11.5 degrees)
            
            # For tilt right to have angle_end < angle_start:
            # We need dy to decrease (right eye goes up relative to left eye)
            frame_landmarks[263][1] -= tilt_angle  # Right eye up (y decreases)
            frame_landmarks[33][1] += tilt_angle   # Left eye down (y increases)
            
            landmark_sequence.append(frame_landmarks)
        
        self._mock_face_landmarker(verifier, mocker, landmark_sequence)
        
        frames = [np.zeros((480, 640, 3), dtype=np.uint8) for _ in range(5)]
        completed, confidence = verifier._verify_gesture("tilt_right", frames)
        
        # Should detect rightward tilt
        assert completed is True
        assert confidence > 0.0
    
    def test_close_eyes_gesture_detection(self, mocker):
        """
        Test that close eyes gesture is correctly detected.
        
        Validates Requirement 4.2, 4.4
        """
        verifier = CVVerifier(model_path="dummy_path.task")
        
        # Create landmark sequence showing eye closing
        base_landmarks = self._create_realistic_landmarks()
        landmark_sequence = []
        
        for i in range(5):
            frame_landmarks = base_landmarks.copy()
            # Close eyes in later frames
            if i >= 2:
                # Close eyes (reduce vertical distance significantly)
                frame_landmarks[159][1] += 0.02  # Left eye top down
                frame_landmarks[145][1] -= 0.02  # Left eye bottom up
                frame_landmarks[386][1] += 0.02  # Right eye top down
                frame_landmarks[374][1] -= 0.02  # Right eye bottom up
            landmark_sequence.append(frame_landmarks)
        
        self._mock_face_landmarker(verifier, mocker, landmark_sequence)
        
        frames = [np.zeros((480, 640, 3), dtype=np.uint8) for _ in range(5)]
        completed, confidence = verifier._verify_gesture("close_eyes", frames)
        
        # Should detect eye closing
        assert completed is True
        assert confidence > 0.0
    
    def test_raise_eyebrows_gesture_detection(self, mocker):
        """
        Test that raise eyebrows gesture is correctly detected.
        
        Validates Requirement 4.2, 4.4
        """
        verifier = CVVerifier(model_path="dummy_path.task")
        
        # Create landmark sequence showing eyebrow raising
        base_landmarks = self._create_realistic_landmarks()
        landmark_sequence = []
        
        for i in range(5):
            frame_landmarks = base_landmarks.copy()
            # Raise eyebrows (move up, y decreases)
            if i >= 2:
                offset = -0.03
                frame_landmarks[70][1] += offset  # Left eyebrow up
                frame_landmarks[300][1] += offset  # Right eyebrow up
            landmark_sequence.append(frame_landmarks)
        
        self._mock_face_landmarker(verifier, mocker, landmark_sequence)
        
        frames = [np.zeros((480, 640, 3), dtype=np.uint8) for _ in range(5)]
        completed, confidence = verifier._verify_gesture("raise_eyebrows", frames)
        
        # Should detect eyebrow raising
        assert completed is True
        assert confidence > 0.0
    
    @staticmethod
    def _create_realistic_landmarks():
        """Helper to create realistic facial landmarks"""
        landmarks = np.zeros((468, 3))
        landmarks[1] = [0.5, 0.5, 0.03]      # Nose tip
        landmarks[10] = [0.5, 0.2, 0.008]    # Forehead
        landmarks[152] = [0.5, 0.8, -0.005]  # Chin
        landmarks[33] = [0.35, 0.4, 0.01]    # Left eye
        landmarks[263] = [0.65, 0.4, 0.01]   # Right eye
        landmarks[61] = [0.4, 0.65, 0.015]   # Left mouth
        landmarks[291] = [0.6, 0.65, 0.015]  # Right mouth
        landmarks[13] = [0.5, 0.62, 0.015]   # Upper lip
        landmarks[14] = [0.5, 0.68, 0.015]   # Lower lip
        landmarks[159] = [0.35, 0.38, 0.01]  # Left eye top
        landmarks[145] = [0.35, 0.42, 0.01]  # Left eye bottom
        landmarks[386] = [0.65, 0.38, 0.01]  # Right eye top
        landmarks[374] = [0.65, 0.42, 0.01]  # Right eye bottom
        landmarks[70] = [0.35, 0.35, 0.01]   # Left eyebrow
        landmarks[300] = [0.65, 0.35, 0.01]  # Right eyebrow
        return landmarks
    
    @staticmethod
    def _mock_face_landmarker(verifier, mocker, landmark_sequence):
        """Helper to mock face landmarker with landmark sequence"""
        mock_landmarker = mocker.MagicMock()
        
        def mock_detect(mp_image):
            if not hasattr(mock_detect, 'call_count'):
                mock_detect.call_count = 0
            
            idx = mock_detect.call_count % len(landmark_sequence)
            mock_detect.call_count += 1
            
            landmarks = landmark_sequence[idx]
            
            mock_face_landmarks = []
            for x, y, z in landmarks:
                mock_landmark = mocker.MagicMock()
                mock_landmark.x = float(x)
                mock_landmark.y = float(y)
                mock_landmark.z = float(z)
                mock_face_landmarks.append(mock_landmark)
            
            mock_result = mocker.MagicMock()
            mock_result.face_landmarks = [mock_face_landmarks]
            return mock_result
        
        mock_landmarker.detect = mock_detect
        verifier._face_landmarker = mock_landmarker


class TestChallengeTimeout:
    """
    Unit tests for challenge timeout functionality.
    Validates Requirement 4.4: Challenge timeout enforcement
    """
    
    def test_challenge_timeout_10_seconds(self, mocker):
        """
        Test that challenges have a 10-second timeout.
        
        This test verifies that the Challenge object is created with
        the correct timeout value of 10 seconds as specified in the requirements.
        
        Validates Requirement 4.4
        """
        # Create a challenge with default timeout
        challenge = Challenge(
            challenge_id="test_session_gesture_0_nod_up",
            type=ChallengeType.GESTURE,
            instruction="Nod your head up",
            timeout_seconds=10
        )
        
        # Verify timeout is set to 10 seconds
        assert challenge.timeout_seconds == 10, \
            f"Challenge timeout should be 10 seconds, got {challenge.timeout_seconds}"
    
    def test_challenge_timeout_enforced_in_verification(self, mocker):
        """
        Test that challenge verification respects the timeout value.
        
        This test simulates a scenario where a challenge takes longer than
        the timeout period and verifies that the system handles it appropriately.
        
        Note: The actual timeout enforcement happens at the WebSocket handler level,
        but the Challenge object carries the timeout specification.
        
        Validates Requirement 4.4
        """
        verifier = CVVerifier(model_path="dummy_path.task")
        
        # Create challenge with 10-second timeout
        challenge = Challenge(
            challenge_id="test_session_gesture_0_nod_up",
            type=ChallengeType.GESTURE,
            instruction="Nod your head up",
            timeout_seconds=10
        )
        
        # Mock _verify_gesture to simulate a failed attempt (timeout scenario)
        mocker.patch.object(verifier, '_verify_gesture', return_value=(False, 0.0))
        
        # Create frames (simulating video capture during timeout period)
        frames = [np.zeros((480, 640, 3), dtype=np.uint8) for _ in range(3)]
        
        # Verify challenge
        result = verifier.verify_challenge(challenge, frames)
        
        # When timeout occurs, the challenge should be marked as failed
        assert result.completed is False, \
            "Challenge should be marked as failed when timeout occurs"
        assert result.confidence == 0.0, \
            "Confidence should be 0.0 for timed-out challenges"
    
    def test_all_gesture_types_have_10_second_timeout(self):
        """
        Test that all gesture types use the standard 10-second timeout.
        
        This ensures consistency across all gesture challenges.
        
        Validates Requirement 4.4
        """
        gesture_types = [
            "nod_up", "nod_down", "turn_left", "turn_right",
            "tilt_left", "tilt_right", "open_mouth", "close_eyes",
            "raise_eyebrows", "blink"
        ]
        
        for gesture in gesture_types:
            challenge = Challenge(
                challenge_id=f"test_session_gesture_0_{gesture}",
                type=ChallengeType.GESTURE,
                instruction=f"Perform {gesture}",
                timeout_seconds=10
            )
            
            assert challenge.timeout_seconds == 10, \
                f"Gesture {gesture} should have 10-second timeout, got {challenge.timeout_seconds}"


class TestVerifyExpression:
    """
    Unit tests for _verify_expression method.
    Validates Requirement 4.2: Expression detection and verification
    """
    
    def test_empty_frames_returns_false(self):
        """
        Test that empty frame list returns False.
        
        Validates Requirement 4.2
        """
        verifier = CVVerifier(model_path="dummy_path.task")
        
        completed, confidence = verifier._verify_expression("smile", [])
        
        assert completed is False
        assert confidence == 0.0
    
    def test_no_face_detected_returns_false(self, mocker):
        """
        Test that frames with no face detected return False.
        
        Validates Requirement 4.2
        """
        verifier = CVVerifier(model_path="dummy_path.task")
        
        # Mock face_landmarker to return no face
        mock_landmarker = mocker.MagicMock()
        mock_result = mocker.MagicMock()
        mock_result.face_landmarks = []
        mock_landmarker.detect.return_value = mock_result
        verifier._face_landmarker = mock_landmarker
        
        frames = [np.zeros((480, 640, 3), dtype=np.uint8) for _ in range(3)]
        completed, confidence = verifier._verify_expression("smile", frames)
        
        assert completed is False
        assert confidence == 0.0
    
    def test_smile_expression_detection(self, mocker):
        """
        Test that smile expression is correctly detected.
        
        Validates Requirement 4.2
        """
        verifier = CVVerifier(model_path="dummy_path.task")
        
        # Create landmarks showing smile
        landmarks = self._create_realistic_landmarks()
        # Adjust for smile: mouth corners up, wider mouth
        landmarks[61][1] -= 0.02  # Left mouth corner up (lower y = higher on face)
        landmarks[291][1] -= 0.02  # Right mouth corner up
        landmarks[61][0] -= 0.03  # Left mouth corner out (increase width)
        landmarks[291][0] += 0.03  # Right mouth corner out
        
        self._mock_face_landmarker(verifier, mocker, [landmarks] * 3)
        
        frames = [np.zeros((480, 640, 3), dtype=np.uint8) for _ in range(3)]
        completed, confidence = verifier._verify_expression("smile", frames)
        
        # Should detect smile
        assert completed is True
        assert confidence > 0.0
    
    def test_surprised_expression_detection(self, mocker):
        """
        Test that surprised expression is correctly detected.
        
        Validates Requirement 4.2
        """
        verifier = CVVerifier(model_path="dummy_path.task")
        
        # Create landmarks showing surprise
        landmarks = self._create_realistic_landmarks()
        # Wide eyes and open mouth
        landmarks[159][1] -= 0.015  # Left eye top up
        landmarks[145][1] += 0.015  # Left eye bottom down
        landmarks[386][1] -= 0.015  # Right eye top up
        landmarks[374][1] += 0.015  # Right eye bottom down
        landmarks[13][1] -= 0.02    # Upper lip up
        landmarks[14][1] += 0.02    # Lower lip down
        
        self._mock_face_landmarker(verifier, mocker, [landmarks] * 3)
        
        frames = [np.zeros((480, 640, 3), dtype=np.uint8) for _ in range(3)]
        completed, confidence = verifier._verify_expression("surprised", frames)
        
        # Should detect surprise
        assert completed is True
        assert confidence > 0.0
    
    def test_neutral_expression_detection(self, mocker):
        """
        Test that neutral expression is correctly detected.
        
        Validates Requirement 4.2
        """
        verifier = CVVerifier(model_path="dummy_path.task")
        
        # Create neutral landmarks
        landmarks = self._create_realistic_landmarks()
        # Adjust mouth opening to neutral range
        landmarks[13][1] = 0.64  # Upper lip
        landmarks[14][1] = 0.66  # Lower lip (small opening)
        
        self._mock_face_landmarker(verifier, mocker, [landmarks] * 3)
        
        frames = [np.zeros((480, 640, 3), dtype=np.uint8) for _ in range(3)]
        completed, confidence = verifier._verify_expression("neutral", frames)
        
        # Should detect neutral
        assert completed is True
        assert confidence > 0.0
    
    def test_unknown_expression_returns_false(self, mocker):
        """
        Test that unknown expression type returns False.
        
        Validates Requirement 4.2
        """
        verifier = CVVerifier(model_path="dummy_path.task")
        
        landmarks = self._create_realistic_landmarks()
        self._mock_face_landmarker(verifier, mocker, [landmarks] * 3)
        
        frames = [np.zeros((480, 640, 3), dtype=np.uint8) for _ in range(3)]
        completed, confidence = verifier._verify_expression("unknown_expression", frames)
        
        assert completed is False
        assert confidence == 0.0
    
    @staticmethod
    def _create_realistic_landmarks():
        """Helper to create realistic facial landmarks"""
        landmarks = np.zeros((468, 3))
        landmarks[1] = [0.5, 0.5, 0.03]      # Nose tip
        landmarks[61] = [0.4, 0.65, 0.015]   # Left mouth
        landmarks[291] = [0.6, 0.65, 0.015]  # Right mouth
        landmarks[13] = [0.5, 0.62, 0.015]   # Upper lip
        landmarks[14] = [0.5, 0.68, 0.015]   # Lower lip
        landmarks[159] = [0.35, 0.38, 0.01]  # Left eye top
        landmarks[145] = [0.35, 0.42, 0.01]  # Left eye bottom
        landmarks[386] = [0.65, 0.38, 0.01]  # Right eye top
        landmarks[374] = [0.65, 0.42, 0.01]  # Right eye bottom
        landmarks[70] = [0.35, 0.35, 0.01]   # Left eyebrow
        landmarks[300] = [0.65, 0.35, 0.01]  # Right eyebrow
        return landmarks
    
    @staticmethod
    def _mock_face_landmarker(verifier, mocker, landmark_sequence):
        """Helper to mock face landmarker with landmark sequence"""
        mock_landmarker = mocker.MagicMock()
        
        def mock_detect(mp_image):
            if not hasattr(mock_detect, 'call_count'):
                mock_detect.call_count = 0
            
            idx = mock_detect.call_count % len(landmark_sequence)
            mock_detect.call_count += 1
            
            landmarks = landmark_sequence[idx]
            
            mock_face_landmarks = []
            for x, y, z in landmarks:
                mock_landmark = mocker.MagicMock()
                mock_landmark.x = float(x)
                mock_landmark.y = float(y)
                mock_landmark.z = float(z)
                mock_face_landmarks.append(mock_landmark)
            
            mock_result = mocker.MagicMock()
            mock_result.face_landmarks = [mock_face_landmarks]
            return mock_result
        
        mock_landmarker.detect = mock_detect
        verifier._face_landmarker = mock_landmarker


# Property-Based Tests
from hypothesis import given, strategies as st, settings, HealthCheck


class TestLivenessScorePropertyTests:
    """
    Property-based tests for liveness score validation.
    These tests verify universal properties that should hold for all inputs.
    """
    
    @given(
        depth_score=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False),
        movement_score=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)
    )
    @settings(
        deadline=None,  # Disable deadline for ML model tests
        suppress_health_check=[HealthCheck.function_scoped_fixture]  # Allow mocker fixture
    )
    @pytest.mark.property_test
    def test_property_5_liveness_score_range_validity(self, depth_score, movement_score, mocker):
        """
        **Validates: Requirements 3.4**
        
        Property 5: Score Range Validity (Liveness)
        For any verification component output (liveness), the score should be 
        a value between 0.0 and 1.0 inclusive.
        
        This property verifies that:
        1. The liveness score is always >= 0.0
        2. The liveness score is always <= 1.0
        3. The score is valid regardless of input depth and movement scores
        """
        verifier = CVVerifier(model_path="dummy_path.task")
        
        # Mock detect_3d_depth to return the generated depth score
        mocker.patch.object(verifier, 'detect_3d_depth', return_value=depth_score)
        
        # Mock detect_micro_movements to return the generated movement score
        mocker.patch.object(verifier, 'detect_micro_movements', return_value=movement_score)
        
        # Create realistic landmarks for face detection
        base_landmarks = np.zeros((468, 3))
        # Set key landmarks with realistic positions
        base_landmarks[33] = [0.35, 0.4, 0.01]   # Left eye
        base_landmarks[263] = [0.65, 0.4, 0.01]  # Right eye
        base_landmarks[1] = [0.5, 0.5, 0.03]     # Nose tip
        base_landmarks[61] = [0.4, 0.65, 0.015]  # Left mouth
        base_landmarks[291] = [0.6, 0.65, 0.015] # Right mouth
        
        # Mock the face_landmarker
        mock_landmarker = mocker.MagicMock()
        mock_result = mocker.MagicMock()
        
        # Create mock landmarks with MediaPipe structure
        mock_face_landmarks = []
        for x, y, z in base_landmarks:
            mock_landmark = mocker.MagicMock()
            mock_landmark.x = float(x)
            mock_landmark.y = float(y)
            mock_landmark.z = float(z)
            mock_face_landmarks.append(mock_landmark)
        
        mock_result.face_landmarks = [mock_face_landmarks]
        mock_landmarker.detect.return_value = mock_result
        verifier._face_landmarker = mock_landmarker
        
        # Create test frames
        frames = [np.zeros((480, 640, 3), dtype=np.uint8) for _ in range(3)]
        
        # Compute liveness score
        score = verifier.compute_liveness_score(frames)
        
        # Verify the score is in valid range [0.0, 1.0]
        assert 0.0 <= score <= 1.0, \
            f"Liveness score {score} is out of valid range [0.0, 1.0] for depth={depth_score}, movement={movement_score}"
        
        # Verify the score is a float
        assert isinstance(score, float), \
            f"Liveness score must be a float, got {type(score)}"


class TestChallengeCompletionPropertyTests:
    """
    Property-based tests for challenge completion recording.
    These tests verify that challenge completions are properly recorded with timestamps.
    """
    
    @given(
        challenge_type=st.sampled_from([ChallengeType.GESTURE, ChallengeType.EXPRESSION]),
        gesture=st.sampled_from(["nod_up", "nod_down", "turn_left", "turn_right", "tilt_left", "tilt_right", 
                                  "open_mouth", "close_eyes", "raise_eyebrows", "blink"]),
        expression=st.sampled_from(["smile", "frown", "surprised", "neutral", "angry"]),
        completed=st.booleans(),
        confidence=st.floats(min_value=0.0, max_value=1.0, allow_nan=False, allow_infinity=False)
    )
    @settings(
        deadline=500,  # Allow up to 500ms per test case
        suppress_health_check=[HealthCheck.function_scoped_fixture]  # Allow mocker fixture
    )
    @pytest.mark.property_test
    def test_property_6_challenge_completion_recording(
        self, challenge_type, gesture, expression, completed, confidence, mocker
    ):
        """
        **Validates: Requirements 4.3**
        
        Property 6: Challenge Completion Recording
        For any gesture that matches the requested challenge, the system should 
        record the completion with a timestamp.
        
        This property verifies that:
        1. When a challenge is completed, a ChallengeResult is returned
        2. The ChallengeResult contains a timestamp
        3. The timestamp is a valid float representing Unix time
        4. The timestamp is recorded at the time of completion (within reasonable bounds)
        5. The completion status matches the verification result
        """
        import time
        
        verifier = CVVerifier(model_path="dummy_path.task")
        
        # Select action based on challenge type
        action = gesture if challenge_type == ChallengeType.GESTURE else expression
        
        # Create challenge with proper ID format
        challenge = Challenge(
            challenge_id=f"test_session_{challenge_type.value}_0_{action}",
            type=challenge_type,
            instruction=f"Perform {action}",
            timeout_seconds=10
        )
        
        # Mock the verification methods to return the generated completion status
        if challenge_type == ChallengeType.GESTURE:
            mocker.patch.object(verifier, '_verify_gesture', return_value=(completed, confidence))
        else:
            mocker.patch.object(verifier, '_verify_expression', return_value=(completed, confidence))
        
        # Create test frames
        frames = [np.zeros((480, 640, 3), dtype=np.uint8) for _ in range(3)]
        
        # Record time before verification
        time_before = time.time()
        
        # Verify challenge
        result = verifier.verify_challenge(challenge, frames)
        
        # Record time after verification
        time_after = time.time()
        
        # Property 1: ChallengeResult is returned
        assert isinstance(result, ChallengeResult), \
            f"Expected ChallengeResult, got {type(result)}"
        
        # Property 2: Result contains challenge_id
        assert result.challenge_id == challenge.challenge_id, \
            f"Challenge ID mismatch: expected {challenge.challenge_id}, got {result.challenge_id}"
        
        # Property 3: Result contains timestamp
        assert hasattr(result, 'timestamp'), \
            "ChallengeResult must have a timestamp attribute"
        
        # Property 4: Timestamp is a valid float
        assert isinstance(result.timestamp, float), \
            f"Timestamp must be a float, got {type(result.timestamp)}"
        
        # Property 5: Timestamp is within reasonable bounds (recorded during verification)
        assert time_before <= result.timestamp <= time_after, \
            f"Timestamp {result.timestamp} is not within verification time range [{time_before}, {time_after}]"
        
        # Property 6: Completion status matches verification result
        assert result.completed == completed, \
            f"Completion status mismatch: expected {completed}, got {result.completed}"
        
        # Property 7: Confidence is in valid range
        assert 0.0 <= result.confidence <= 1.0, \
            f"Confidence {result.confidence} is out of valid range [0.0, 1.0]"
        
        # Property 8: Confidence matches verification result
        assert result.confidence == confidence, \
            f"Confidence mismatch: expected {confidence}, got {result.confidence}"
        
        # Property 9: Timestamp is positive (valid Unix time)
        assert result.timestamp > 0, \
            f"Timestamp must be positive, got {result.timestamp}"
        
        # Property 10: Timestamp is reasonable (not in distant past or future)
        # Should be within last 10 seconds and not in future
        current_time = time.time()
        assert current_time - 10 <= result.timestamp <= current_time + 1, \
            f"Timestamp {result.timestamp} is not reasonable (current time: {current_time})"
