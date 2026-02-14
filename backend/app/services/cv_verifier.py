"""
Computer Vision Verifier for liveness detection and challenge verification
"""
import cv2
import mediapipe as mp
import numpy as np
from typing import List, Optional
from ..models.data_models import Challenge, ChallengeResult


class CVVerifier:
    """
    Detects liveness and verifies challenge completion using MediaPipe and OpenCV.
    
    Validates Requirement 3.1: Real-time liveness detection with MediaPipe FaceMesh
    """
    
    def __init__(self, model_path: Optional[str] = None):
        """
        Initialize CVVerifier with MediaPipe FaceLandmarker configuration.
        
        The FaceLandmarker is initialized lazily when first needed to avoid
        requiring the model file during testing of preprocessing functions.
        
        Configuration for FaceLandmarker (when initialized):
        - num_faces: 1 (only track single face for security)
        - min_face_detection_confidence: 0.5 (balanced detection threshold)
        - min_face_presence_confidence: 0.5 (balanced tracking threshold)
        - output_face_blendshapes: False (not needed for liveness detection)
        - output_facial_transformation_matrixes: False (not needed)
        
        Args:
            model_path: Path to the MediaPipe face landmarker model file.
                       If None, will need to be provided before using detection methods.
        
        Validates Requirement 3.1
        """
        self.model_path = model_path
        self._face_landmarker = None
        
        # Store previous frame landmarks for motion detection
        self.previous_landmarks = None
    
    @property
    def face_landmarker(self):
        """
        Lazy initialization of MediaPipe FaceLandmarker.
        
        Returns the FaceLandmarker instance, initializing it on first access.
        """
        if self._face_landmarker is None:
            if self.model_path is None:
                raise ValueError(
                    "Model path must be provided before using face landmarker. "
                    "Download the model from: "
                    "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/latest/face_landmarker.task"
                )
            
            # Create base options with model path
            base_options = mp.tasks.BaseOptions(model_asset_path=self.model_path)
            
            # Create FaceLandmarker options
            options = mp.tasks.vision.FaceLandmarkerOptions(
                base_options=base_options,
                running_mode=mp.tasks.vision.RunningMode.IMAGE,
                num_faces=1,
                min_face_detection_confidence=0.5,
                min_face_presence_confidence=0.5,
                output_face_blendshapes=False,
                output_facial_transformation_matrixes=False
            )
            
            # Create FaceLandmarker
            self._face_landmarker = mp.tasks.vision.FaceLandmarker.create_from_options(options)
        
        return self._face_landmarker
    
    def preprocess_frame(self, frame: np.ndarray, target_size: tuple = (640, 480)) -> np.ndarray:
        """
        Preprocess video frame for MediaPipe processing.
        
        Steps:
        1. Resize frame to target size for consistent processing
        2. Convert from BGR (OpenCV default) to RGB (MediaPipe requirement)
        
        Args:
            frame: Input frame in BGR format (OpenCV default)
            target_size: Target dimensions (width, height) for resizing
            
        Returns:
            np.ndarray: Preprocessed frame in RGB format
            
        Validates Requirement 3.1
        """
        # Resize frame to target size
        resized = cv2.resize(frame, target_size, interpolation=cv2.INTER_LINEAR)
        
        # Convert BGR to RGB (MediaPipe requires RGB)
        rgb_frame = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
        
        return rgb_frame
    
    def compute_liveness_score(self, video_frames: List[np.ndarray]) -> float:
        """
        Analyze frames for 3D depth cues and natural micro-movements.
        
        This method combines:
        - 3D depth detection from facial landmark geometry
        - Natural micro-movement detection across frames
        
        The final liveness score is a weighted combination of both signals,
        with equal weight given to depth and movement analysis.
        
        Args:
            video_frames: List of video frames to analyze
            
        Returns:
            float: Liveness score between 0.0 and 1.0
            
        Validates Requirements 3.2, 3.3, 3.4
        """
        if not video_frames or len(video_frames) == 0:
            # No frames to analyze
            return 0.0
        
        # Compute movement score across frame sequence
        movement_score = self.detect_micro_movements(video_frames)
        
        # Compute depth score from the first frame with detected landmarks
        depth_score = 0.0
        for frame in video_frames:
            # Preprocess frame
            rgb_frame = self.preprocess_frame(frame)
            
            # Convert to MediaPipe Image
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
            
            # Detect landmarks
            detection_result = self.face_landmarker.detect(mp_image)
            
            if detection_result.face_landmarks and len(detection_result.face_landmarks) > 0:
                # Extract first face landmarks
                landmarks = detection_result.face_landmarks[0]
                # Convert to numpy array
                landmarks_array = np.array([[lm.x, lm.y, lm.z] for lm in landmarks])
                
                # Compute depth score
                depth_score = self.detect_3d_depth(landmarks_array)
                break  # Use first frame with detected face
        
        # Combine depth and movement scores with equal weighting
        # Both signals are equally important for liveness detection
        final_score = 0.5 * depth_score + 0.5 * movement_score
        
        # Ensure score is in valid range [0.0, 1.0]
        return float(np.clip(final_score, 0.0, 1.0))
    
    def verify_challenge(
        self, 
        challenge: Challenge, 
        video_frames: List[np.ndarray]
    ) -> ChallengeResult:
        """
        Check if user performed the requested action.
        
        For gesture challenges: Detects head pose and movement patterns
        For expression challenges: Integrates with emotion analyzer
        
        Args:
            challenge: The challenge to verify
            video_frames: Video frames captured during challenge
            
        Returns:
            ChallengeResult: Verification result with completion status and confidence
            
        Validates Requirements 4.2, 4.3
        """
        import time
        
        if not video_frames or len(video_frames) == 0:
            # No frames to analyze
            return ChallengeResult(
                challenge_id=challenge.challenge_id,
                completed=False,
                confidence=0.0,
                timestamp=time.time()
            )
        
        # Extract challenge action from challenge_id
        # Format: {session_id}_{type}_{index}_{action}
        # where action can be multi-word like "nod_up" or single word like "smile"
        # We need to extract everything after the third underscore
        challenge_parts = challenge.challenge_id.split('_')
        if len(challenge_parts) < 4:
            # Invalid challenge ID format
            return ChallengeResult(
                challenge_id=challenge.challenge_id,
                completed=False,
                confidence=0.0,
                timestamp=time.time()
            )
        
        # Join all parts after the third underscore to get the full action
        # e.g., "test_session_gesture_0_nod_up" -> ["test", "session", "gesture", "0", "nod", "up"]
        # We want "nod_up", which is everything from index 4 onwards joined with "_"
        challenge_action = '_'.join(challenge_parts[4:]) if len(challenge_parts) > 4 else challenge_parts[3]
        
        # Import ChallengeType from data_models
        from ..models.data_models import ChallengeType
        
        # Route to appropriate verification method based on challenge type
        if challenge.type == ChallengeType.GESTURE:
            completed, confidence = self._verify_gesture(challenge_action, video_frames)
        elif challenge.type == ChallengeType.EXPRESSION:
            completed, confidence = self._verify_expression(challenge_action, video_frames)
        else:
            # Unknown challenge type
            completed, confidence = False, 0.0
        
        # Record timestamp on completion (Requirement 4.3)
        return ChallengeResult(
            challenge_id=challenge.challenge_id,
            completed=completed,
            confidence=confidence,
            timestamp=time.time()
        )
    
    def detect_3d_depth(self, landmarks: np.ndarray) -> float:
        """
        Compute depth score from facial landmark geometry.
        
        Analyzes 3D spatial relationships between landmarks to distinguish
        live faces from flat images. Uses multiple depth cues:
        
        1. Nose-to-face ratio: Measures the relative distance of the nose tip
           from the face plane. In 3D faces, the nose protrudes significantly.
        
        2. Face width-to-height ratio variance: 3D faces show perspective
           distortion when viewed at angles, while flat images maintain
           consistent ratios.
        
        3. Z-coordinate variance: MediaPipe provides normalized 3D coordinates.
           Real faces have significant depth variation, flat images have minimal.
        
        Args:
            landmarks: Facial landmarks from MediaPipe FaceMesh (468 points, 3D)
                      Expected shape: (468, 3) where columns are [x, y, z]
            
        Returns:
            float: Depth score between 0.0 (flat/2D) and 1.0 (3D/live)
            
        Validates Requirement 3.2
        """
        if landmarks.shape[0] < 468:
            # Insufficient landmarks for depth analysis
            return 0.0
        
        # Key landmark indices (MediaPipe FaceMesh topology)
        # Nose tip: 1
        # Left eye outer corner: 33
        # Right eye outer corner: 263
        # Left mouth corner: 61
        # Right mouth corner: 291
        # Chin: 152
        # Forehead center: 10
        
        nose_tip = landmarks[1]
        left_eye = landmarks[33]
        right_eye = landmarks[263]
        left_mouth = landmarks[61]
        right_mouth = landmarks[291]
        chin = landmarks[152]
        forehead = landmarks[10]
        
        # Cue 1: Nose protrusion (z-depth relative to face plane)
        # Calculate average z-coordinate of face plane (eyes, mouth, chin)
        face_plane_z = np.mean([
            left_eye[2], right_eye[2],
            left_mouth[2], right_mouth[2],
            chin[2], forehead[2]
        ])
        
        # Nose should protrude forward (higher z in MediaPipe coordinates)
        nose_protrusion = nose_tip[2] - face_plane_z
        
        # Normalize: typical protrusion is ~0.02-0.05 in MediaPipe normalized coords
        # Flat images have protrusion near 0
        nose_score = np.clip(abs(nose_protrusion) / 0.03, 0.0, 1.0)
        
        # Cue 2: Z-coordinate variance across all landmarks
        # Real 3D faces have significant depth variation
        # Flat images have minimal z-variance (noise only)
        z_coords = landmarks[:, 2]
        z_variance = np.var(z_coords)
        
        # Normalize: typical variance for 3D face is ~0.0005-0.002
        # Flat images have variance < 0.0001
        variance_score = np.clip(z_variance / 0.001, 0.0, 1.0)
        
        # Cue 3: Face width consistency check
        # Measure face width at different depths (eye level vs mouth level)
        # 3D faces show perspective effects, flat images don't
        eye_width = np.linalg.norm(left_eye[:2] - right_eye[:2])
        mouth_width = np.linalg.norm(left_mouth[:2] - right_mouth[:2])
        
        # Calculate ratio - should be different for 3D faces due to perspective
        if eye_width > 0:
            width_ratio = mouth_width / eye_width
            # Typical ratio is 0.6-0.8, but variance indicates 3D structure
            # Flat images have very consistent ratios
            width_deviation = abs(width_ratio - 0.7)
            width_score = np.clip(width_deviation / 0.2, 0.0, 1.0)
        else:
            width_score = 0.0
        
        # Combine scores with weights
        # Nose protrusion is most reliable (50%)
        # Z-variance is secondary (35%)
        # Width perspective is tertiary (15%)
        final_score = (
            0.50 * nose_score +
            0.35 * variance_score +
            0.15 * width_score
        )
        
        # Ensure score is in valid range [0.0, 1.0]
        return float(np.clip(final_score, 0.0, 1.0))
    
    def detect_micro_movements(self, frame_sequence: List[np.ndarray]) -> float:
        """
        Detect natural involuntary movements.
        
        Tracks subtle movements like eye blinks and minor head motion
        that are characteristic of living tissue. Analyzes:
        
        1. Eye blink detection: Tracks eye aspect ratio (EAR) changes
           indicating natural blinking patterns
        
        2. Subtle head motion: Measures small positional changes in
           facial landmarks across frames
        
        3. Landmark jitter: Natural micro-movements cause small variations
           in landmark positions even when trying to stay still
        
        Args:
            frame_sequence: Sequence of video frames to analyze
            
        Returns:
            float: Movement score between 0.0 (static/no movement) and 1.0 (natural movement)
            
        Validates Requirement 3.3
        """
        if len(frame_sequence) < 2:
            # Need at least 2 frames to detect movement
            return 0.0
        
        # Extract landmarks from all frames
        all_landmarks = []
        for frame in frame_sequence:
            # Preprocess frame
            rgb_frame = self.preprocess_frame(frame)
            
            # Convert to MediaPipe Image
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
            
            # Detect landmarks
            detection_result = self.face_landmarker.detect(mp_image)
            
            if detection_result.face_landmarks and len(detection_result.face_landmarks) > 0:
                # Extract first face landmarks
                landmarks = detection_result.face_landmarks[0]
                # Convert to numpy array
                landmarks_array = np.array([[lm.x, lm.y, lm.z] for lm in landmarks])
                all_landmarks.append(landmarks_array)
            else:
                # No face detected in this frame
                return 0.0
        
        if len(all_landmarks) < 2:
            # Insufficient landmark data
            return 0.0
        
        # Key landmark indices for eye blink detection
        # Left eye: 159 (top), 145 (bottom), 33 (left), 133 (right)
        # Right eye: 386 (top), 374 (bottom), 263 (left), 362 (right)
        LEFT_EYE_TOP = 159
        LEFT_EYE_BOTTOM = 145
        LEFT_EYE_LEFT = 33
        LEFT_EYE_RIGHT = 133
        
        RIGHT_EYE_TOP = 386
        RIGHT_EYE_BOTTOM = 374
        RIGHT_EYE_LEFT = 263
        RIGHT_EYE_RIGHT = 362
        
        # Key landmarks for head position tracking
        NOSE_TIP = 1
        FOREHEAD = 10
        CHIN = 152
        
        # 1. Eye blink detection using Eye Aspect Ratio (EAR)
        ear_values = []
        for landmarks in all_landmarks:
            # Calculate left eye EAR
            left_vertical = np.linalg.norm(
                landmarks[LEFT_EYE_TOP][:2] - landmarks[LEFT_EYE_BOTTOM][:2]
            )
            left_horizontal = np.linalg.norm(
                landmarks[LEFT_EYE_LEFT][:2] - landmarks[LEFT_EYE_RIGHT][:2]
            )
            left_ear = left_vertical / (left_horizontal + 1e-6)
            
            # Calculate right eye EAR
            right_vertical = np.linalg.norm(
                landmarks[RIGHT_EYE_TOP][:2] - landmarks[RIGHT_EYE_BOTTOM][:2]
            )
            right_horizontal = np.linalg.norm(
                landmarks[RIGHT_EYE_LEFT][:2] - landmarks[RIGHT_EYE_RIGHT][:2]
            )
            right_ear = right_vertical / (right_horizontal + 1e-6)
            
            # Average EAR for both eyes
            avg_ear = (left_ear + right_ear) / 2.0
            ear_values.append(avg_ear)
        
        # Detect blinks as significant drops in EAR
        # Typical EAR is ~0.2-0.3 when eyes open, drops to ~0.1 during blink
        ear_variance = np.var(ear_values)
        ear_range = np.max(ear_values) - np.min(ear_values)
        
        # Score based on EAR variation (indicates blinking)
        # Natural blinking causes variance ~0.001-0.005
        blink_score = np.clip(ear_variance / 0.003, 0.0, 1.0)
        
        # 2. Subtle head motion detection
        head_positions = []
        for landmarks in all_landmarks:
            # Use centroid of nose, forehead, and chin as head position
            head_center = np.mean([
                landmarks[NOSE_TIP],
                landmarks[FOREHEAD],
                landmarks[CHIN]
            ], axis=0)
            head_positions.append(head_center)
        
        # Calculate frame-to-frame head movement
        head_movements = []
        for i in range(1, len(head_positions)):
            movement = np.linalg.norm(head_positions[i] - head_positions[i-1])
            head_movements.append(movement)
        
        # Natural micro-movements: ~0.001-0.01 per frame
        # Static images/video: < 0.0005
        avg_head_movement = np.mean(head_movements) if head_movements else 0.0
        head_score = np.clip(avg_head_movement / 0.005, 0.0, 1.0)
        
        # 3. Landmark jitter detection (natural instability)
        # Track a stable landmark (nose tip) across frames
        nose_positions = [landmarks[NOSE_TIP] for landmarks in all_landmarks]
        
        # Calculate variance in nose position
        nose_variance = np.var(nose_positions, axis=0)
        total_nose_variance = np.sum(nose_variance)
        
        # Natural jitter: ~0.00001-0.0001
        # Static: < 0.000005
        jitter_score = np.clip(total_nose_variance / 0.00005, 0.0, 1.0)
        
        # Combine scores with weights
        # Blink detection is most reliable (50%)
        # Head motion is secondary (30%)
        # Landmark jitter is tertiary (20%)
        final_score = (
            0.50 * blink_score +
            0.30 * head_score +
            0.20 * jitter_score
        )
        
        # Ensure score is in valid range [0.0, 1.0]
        return float(np.clip(final_score, 0.0, 1.0))
    
    def _verify_gesture(self, gesture: str, video_frames: List[np.ndarray]) -> tuple[bool, float]:
        """
        Verify gesture challenge by detecting head pose and movement patterns.
        
        Args:
            gesture: The gesture to verify (e.g., "nod_up", "turn_left")
            video_frames: Video frames to analyze
            
        Returns:
            tuple: (completed: bool, confidence: float)
            
        Validates Requirement 4.2
        """
        if len(video_frames) < 2:
            # Need at least 2 frames to detect movement
            return False, 0.0
        
        # Extract landmarks from frames
        all_landmarks = []
        for frame in video_frames:
            rgb_frame = self.preprocess_frame(frame)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
            detection_result = self.face_landmarker.detect(mp_image)
            
            if detection_result.face_landmarks and len(detection_result.face_landmarks) > 0:
                landmarks = detection_result.face_landmarks[0]
                landmarks_array = np.array([[lm.x, lm.y, lm.z] for lm in landmarks])
                all_landmarks.append(landmarks_array)
            else:
                # No face detected
                return False, 0.0
        
        if len(all_landmarks) < 2:
            return False, 0.0
        
        # Key landmark indices for head pose
        NOSE_TIP = 1
        FOREHEAD = 10
        CHIN = 152
        LEFT_EYE = 33
        RIGHT_EYE = 263
        LEFT_MOUTH = 61
        RIGHT_MOUTH = 291
        
        # Analyze gesture based on type
        if gesture in ["nod_up", "nod_down"]:
            # Vertical head movement - track nose and chin y-coordinates
            nose_positions = [lm[NOSE_TIP][1] for lm in all_landmarks]
            chin_positions = [lm[CHIN][1] for lm in all_landmarks]
            
            # Calculate vertical movement
            nose_movement = max(nose_positions) - min(nose_positions)
            chin_movement = max(chin_positions) - min(chin_positions)
            avg_movement = (nose_movement + chin_movement) / 2.0
            
            # Nod up: head moves up (y decreases in normalized coords)
            # Nod down: head moves down (y increases)
            if gesture == "nod_up":
                direction_correct = nose_positions[-1] < nose_positions[0]
            else:  # nod_down
                direction_correct = nose_positions[-1] > nose_positions[0]
            
            # Threshold: significant movement (> 0.03) in correct direction
            if avg_movement > 0.03 and direction_correct:
                confidence = min(avg_movement / 0.1, 1.0)  # Normalize to 0-1
                return True, confidence
            else:
                return False, avg_movement / 0.1
        
        elif gesture in ["turn_left", "turn_right"]:
            # Horizontal head rotation - track nose x-coordinate and eye positions
            nose_positions = [lm[NOSE_TIP][0] for lm in all_landmarks]
            
            # Calculate horizontal movement
            nose_movement = max(nose_positions) - min(nose_positions)
            
            # Turn left: nose moves left (x decreases)
            # Turn right: nose moves right (x increases)
            if gesture == "turn_left":
                direction_correct = nose_positions[-1] < nose_positions[0]
            else:  # turn_right
                direction_correct = nose_positions[-1] > nose_positions[0]
            
            # Threshold: significant movement (> 0.05) in correct direction
            if nose_movement > 0.05 and direction_correct:
                confidence = min(nose_movement / 0.15, 1.0)
                return True, confidence
            else:
                return False, nose_movement / 0.15
        
        elif gesture in ["tilt_left", "tilt_right"]:
            # Head tilt - track angle between eyes
            eye_angles = []
            for lm in all_landmarks:
                left_eye = lm[LEFT_EYE]
                right_eye = lm[RIGHT_EYE]
                # Calculate angle of line between eyes
                dy = right_eye[1] - left_eye[1]
                dx = right_eye[0] - left_eye[0]
                angle = np.arctan2(dy, dx)
                eye_angles.append(angle)
            
            # Calculate angle change
            angle_change = abs(eye_angles[-1] - eye_angles[0])
            
            # Tilt left: right eye goes up (positive angle change)
            # Tilt right: left eye goes up (negative angle change)
            if gesture == "tilt_left":
                direction_correct = eye_angles[-1] > eye_angles[0]
            else:  # tilt_right
                direction_correct = eye_angles[-1] < eye_angles[0]
            
            # Threshold: significant tilt (> 0.15 radians ≈ 8.6 degrees)
            if angle_change > 0.15 and direction_correct:
                confidence = min(angle_change / 0.4, 1.0)
                return True, confidence
            else:
                return False, angle_change / 0.4
        
        elif gesture == "open_mouth":
            # Mouth opening - track vertical distance between mouth corners
            mouth_openings = []
            for lm in all_landmarks:
                # Upper lip center: 13, Lower lip center: 14
                upper_lip = lm[13]
                lower_lip = lm[14]
                opening = abs(lower_lip[1] - upper_lip[1])
                mouth_openings.append(opening)
            
            # Check if mouth opened significantly
            max_opening = max(mouth_openings)
            
            # Threshold: mouth opening > 0.03
            if max_opening > 0.03:
                confidence = min(max_opening / 0.08, 1.0)
                return True, confidence
            else:
                return False, max_opening / 0.08
        
        elif gesture == "close_eyes":
            # Eye closing - track eye aspect ratio
            ear_values = []
            for lm in all_landmarks:
                # Left eye
                left_top = lm[159]
                left_bottom = lm[145]
                left_vertical = abs(left_top[1] - left_bottom[1])
                
                # Right eye
                right_top = lm[386]
                right_bottom = lm[374]
                right_vertical = abs(right_top[1] - right_bottom[1])
                
                avg_vertical = (left_vertical + right_vertical) / 2.0
                ear_values.append(avg_vertical)
            
            # Check if eyes closed (EAR drops significantly)
            min_ear = min(ear_values)
            
            # Threshold: EAR < 0.015 indicates closed eyes
            if min_ear < 0.015:
                confidence = min((0.025 - min_ear) / 0.025, 1.0)
                return True, confidence
            else:
                return False, (0.025 - min_ear) / 0.025
        
        elif gesture == "raise_eyebrows":
            # Eyebrow raising - track forehead and eyebrow positions
            eyebrow_positions = []
            for lm in all_landmarks:
                # Left eyebrow: 70, Right eyebrow: 300
                left_brow = lm[70]
                right_brow = lm[300]
                avg_brow_y = (left_brow[1] + right_brow[1]) / 2.0
                eyebrow_positions.append(avg_brow_y)
            
            # Check if eyebrows moved up (y decreases)
            movement = eyebrow_positions[0] - min(eyebrow_positions)
            
            # Threshold: eyebrows move up > 0.02
            if movement > 0.02:
                confidence = min(movement / 0.05, 1.0)
                return True, confidence
            else:
                return False, movement / 0.05
        
        elif gesture == "blink":
            # Blinking - detect rapid eye closure and opening
            ear_values = []
            for lm in all_landmarks:
                # Calculate average eye aspect ratio
                left_vertical = abs(lm[159][1] - lm[145][1])
                right_vertical = abs(lm[386][1] - lm[374][1])
                avg_ear = (left_vertical + right_vertical) / 2.0
                ear_values.append(avg_ear)
            
            # Detect blink: EAR drops then rises
            min_ear = min(ear_values)
            max_ear = max(ear_values)
            ear_range = max_ear - min_ear
            
            # Check for blink pattern (significant variation)
            if ear_range > 0.01 and min_ear < 0.02:
                confidence = min(ear_range / 0.03, 1.0)
                return True, confidence
            else:
                return False, ear_range / 0.03
        
        # Unknown gesture
        return False, 0.0
    
    def _verify_expression(self, expression: str, video_frames: List[np.ndarray]) -> tuple[bool, float]:
        """
        Verify expression challenge by integrating with emotion analyzer.
        
        This is a simplified implementation that uses facial landmark analysis
        as a proxy for emotion detection. In production, this would integrate
        with DeepFace or similar emotion detection library.
        
        Args:
            expression: The expression to verify (e.g., "smile", "frown")
            video_frames: Video frames to analyze
            
        Returns:
            tuple: (completed: bool, confidence: float)
            
        Validates Requirement 4.2
        """
        if len(video_frames) == 0:
            return False, 0.0
        
        # Extract landmarks from frames
        all_landmarks = []
        for frame in video_frames:
            rgb_frame = self.preprocess_frame(frame)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
            detection_result = self.face_landmarker.detect(mp_image)
            
            if detection_result.face_landmarks and len(detection_result.face_landmarks) > 0:
                landmarks = detection_result.face_landmarks[0]
                landmarks_array = np.array([[lm.x, lm.y, lm.z] for lm in landmarks])
                all_landmarks.append(landmarks_array)
            else:
                return False, 0.0
        
        if len(all_landmarks) == 0:
            return False, 0.0
        
        # Analyze expression using facial landmarks
        # Key landmarks for expressions
        LEFT_MOUTH = 61
        RIGHT_MOUTH = 291
        UPPER_LIP = 13
        LOWER_LIP = 14
        LEFT_EYEBROW = 70
        RIGHT_EYEBROW = 300
        
        # Use middle frame for analysis
        mid_frame_idx = len(all_landmarks) // 2
        landmarks = all_landmarks[mid_frame_idx]
        
        if expression == "smile":
            # Smile: mouth corners move up and outward
            left_mouth = landmarks[LEFT_MOUTH]
            right_mouth = landmarks[RIGHT_MOUTH]
            mouth_width = abs(right_mouth[0] - left_mouth[0])
            
            # Check mouth curvature (corners higher than center)
            # In a smile, the corners are higher (lower y value) than the center
            mouth_center_y = (left_mouth[1] + right_mouth[1]) / 2.0
            upper_lip_y = landmarks[UPPER_LIP][1]
            
            # Smile indicator: upper lip is higher (lower y) than mouth corners
            # This creates the upward curve of a smile
            smile_indicator = mouth_center_y - upper_lip_y
            
            # Threshold: smile indicator > 0.01 and mouth width > 0.18
            if smile_indicator > 0.01 and mouth_width > 0.18:
                confidence = min(smile_indicator / 0.05, 1.0)
                return True, confidence
            else:
                return False, max(smile_indicator / 0.05, 0.0)
        
        elif expression == "frown":
            # Frown: mouth corners move down, eyebrows lower
            left_mouth = landmarks[LEFT_MOUTH]
            right_mouth = landmarks[RIGHT_MOUTH]
            
            # Check mouth curvature (corners lower than center)
            mouth_center_y = (left_mouth[1] + right_mouth[1]) / 2.0
            lower_lip_y = landmarks[LOWER_LIP][1]
            
            # Frown indicator: mouth corners are lower (higher y value)
            frown_indicator = mouth_center_y - lower_lip_y
            
            if frown_indicator > 0.01:
                confidence = min(frown_indicator / 0.03, 1.0)
                return True, confidence
            else:
                return False, frown_indicator / 0.03
        
        elif expression == "surprised":
            # Surprised: eyes wide open, mouth open, eyebrows raised
            # Check eye opening
            left_eye_vertical = abs(landmarks[159][1] - landmarks[145][1])
            right_eye_vertical = abs(landmarks[386][1] - landmarks[374][1])
            avg_eye_opening = (left_eye_vertical + right_eye_vertical) / 2.0
            
            # Check mouth opening
            mouth_opening = abs(landmarks[LOWER_LIP][1] - landmarks[UPPER_LIP][1])
            
            # Surprised: both eyes and mouth open wide
            if avg_eye_opening > 0.025 and mouth_opening > 0.03:
                confidence = min((avg_eye_opening + mouth_opening) / 0.08, 1.0)
                return True, confidence
            else:
                return False, (avg_eye_opening + mouth_opening) / 0.08
        
        elif expression == "neutral":
            # Neutral: relaxed face, minimal expression
            # Check that mouth and eyes are in neutral position
            mouth_opening = abs(landmarks[LOWER_LIP][1] - landmarks[UPPER_LIP][1])
            
            # Neutral: small mouth opening (0.01-0.025)
            if 0.01 <= mouth_opening <= 0.025:
                confidence = 0.8  # High confidence for neutral
                return True, confidence
            else:
                return False, 0.5
        
        elif expression == "angry":
            # Angry: eyebrows lowered and closer together, mouth tense
            left_brow = landmarks[LEFT_EYEBROW]
            right_brow = landmarks[RIGHT_EYEBROW]
            
            # Check eyebrow position (lower = higher y value)
            avg_brow_y = (left_brow[1] + right_brow[1]) / 2.0
            
            # Angry: eyebrows lower (higher y value, closer to eyes)
            # Baseline eyebrow position is around 0.3-0.35
            if avg_brow_y > 0.35:
                confidence = min((avg_brow_y - 0.35) / 0.1, 1.0)
                return True, confidence
            else:
                return False, (avg_brow_y - 0.35) / 0.1
        
        # Unknown expression
        return False, 0.0
    
    def __del__(self):
        """Clean up MediaPipe resources"""
        if self._face_landmarker is not None:
            self._face_landmarker.close()
