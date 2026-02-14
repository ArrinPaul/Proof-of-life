"""
Computer Vision Verifier for liveness detection and challenge verification
"""
import cv2
import logging
import mediapipe as mp
import numpy as np
from typing import List, Optional
from ..models.data_models import Challenge, ChallengeResult

logger = logging.getLogger(__name__)


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
        Returns None if model cannot be loaded.
        """
        if self._face_landmarker is None:
            if self.model_path is None:
                import logging
                logging.getLogger(__name__).warning(
                    "Model path not provided. Face landmarker will not be available. "
                    "Download the model using: python download_mediapipe_model.py"
                )
                return None
            
            try:
                import os
                if not os.path.exists(self.model_path):
                    import logging
                    logging.getLogger(__name__).warning(
                        f"MediaPipe model not found at {self.model_path}. "
                        "Download it using: python download_mediapipe_model.py"
                    )
                    return None

                # Create base options with model path
                base_options = mp.tasks.BaseOptions(model_asset_path=self.model_path)
                
                # Create FaceLandmarker options — use low thresholds
                # to catch faces in typical webcam conditions
                options = mp.tasks.vision.FaceLandmarkerOptions(
                    base_options=base_options,
                    running_mode=mp.tasks.vision.RunningMode.IMAGE,
                    num_faces=1,
                    min_face_detection_confidence=0.3,
                    min_face_presence_confidence=0.3,
                    output_face_blendshapes=False,
                    output_facial_transformation_matrixes=False
                )
                
                # Create FaceLandmarker
                self._face_landmarker = mp.tasks.vision.FaceLandmarker.create_from_options(options)
            except Exception as e:
                import logging
                logging.getLogger(__name__).error(f"Failed to initialize MediaPipe FaceLandmarker: {e}")
                return None
        
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
        if self.face_landmarker is None:
            return 0.5 * movement_score
        for frame in video_frames:
            # Preprocess frame
            rgb_frame = self.preprocess_frame(frame)
            
            # Convert to MediaPipe Image
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
            
            try:
                # Detect landmarks
                detection_result = self.face_landmarker.detect(mp_image)
            except Exception:
                continue
            
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
        
        # Map human-readable instructions back to action keys
        from ..models.data_models import ChallengeType
        
        INSTRUCTION_TO_ACTION = {
            "Nod your head up": "nod_up",
            "Nod your head down": "nod_down",
            "Turn your head to the left": "turn_left",
            "Turn your head to the right": "turn_right",
            "Tilt your head to the left": "tilt_left",
            "Tilt your head to the right": "tilt_right",
            "Open your mouth wide": "open_mouth",
            "Close your eyes": "close_eyes",
            "Raise your eyebrows": "raise_eyebrows",
            "Blink your eyes": "blink",
            "Smile": "smile",
            "Frown": "frown",
            "Look surprised": "surprised",
            "Keep a neutral expression": "neutral",
            "Look angry": "angry",
        }
        
        challenge_action = INSTRUCTION_TO_ACTION.get(challenge.instruction)
        logger.info(f"verify_challenge: instruction='{challenge.instruction}', mapped_action='{challenge_action}', type={challenge.type}, frames={len(video_frames)}")
        if not challenge_action:
            # Fallback: extract action from challenge_id
            # Format: {uuid}_{gesture|expression}_{index}_{action_with_underscores}
            # Find the type marker and extract everything after the index
            cid = challenge.challenge_id
            for marker in ['_gesture_', '_expression_']:
                idx = cid.find(marker)
                if idx != -1:
                    after_marker = cid[idx + len(marker):]  # e.g. "0_nod_up"
                    # Skip the index and underscore
                    underscore = after_marker.find('_')
                    if underscore != -1:
                        challenge_action = after_marker[underscore + 1:]  # e.g. "nod_up"
                    else:
                        challenge_action = after_marker
                    break
            if not challenge_action:
                challenge_action = cid.split('_')[-1]
        
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
        if self.face_landmarker is None:
            return 0.0
        for frame in frame_sequence:
            # Preprocess frame
            rgb_frame = self.preprocess_frame(frame)
            
            # Convert to MediaPipe Image
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
            
            try:
                # Detect landmarks
                detection_result = self.face_landmarker.detect(mp_image)
            except Exception:
                return 0.0
            
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
        Uses PEAK movement detection (not first-vs-last) so users can
        perform the gesture and return to neutral naturally.
        """
        if len(video_frames) < 2:
            logger.warning(f"Gesture '{gesture}': need >=2 frames, got {len(video_frames)}")
            return False, 0.0
        
        # Extract landmarks from frames — tolerate frames without face
        all_landmarks = []
        if self.face_landmarker is None:
            logger.warning("face_landmarker is None — cannot verify gesture")
            return False, 0.0
        for frame in video_frames:
            rgb_frame = self.preprocess_frame(frame)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
            try:
                detection_result = self.face_landmarker.detect(mp_image)
            except Exception:
                continue
            
            if detection_result.face_landmarks and len(detection_result.face_landmarks) > 0:
                landmarks = detection_result.face_landmarks[0]
                landmarks_array = np.array([[lm.x, lm.y, lm.z] for lm in landmarks])
                all_landmarks.append(landmarks_array)
        
        if len(all_landmarks) < 2:
            logger.warning(f"Gesture '{gesture}': only {len(all_landmarks)} frames had faces out of {len(video_frames)}")
            return False, 0.0
        
        logger.info(f"Gesture '{gesture}': {len(all_landmarks)} frames with faces")
        
        # Key landmark indices
        NOSE_TIP = 1
        CHIN = 152
        LEFT_EYE = 33
        RIGHT_EYE = 263
        
        # ---------- NOD UP / NOD DOWN ----------
        if gesture in ["nod_up", "nod_down"]:
            nose_y = [lm[NOSE_TIP][1] for lm in all_landmarks]
            chin_y = [lm[CHIN][1] for lm in all_landmarks]
            
            # Use total range of movement (peak-to-peak), NOT first-vs-last
            nose_range = max(nose_y) - min(nose_y)
            chin_range = max(chin_y) - min(chin_y)
            movement = (nose_range + chin_range) / 2.0
            
            # For direction: check if peak movement went in the right direction
            # nod_up: nose went UP at some point (y decreased from baseline)
            # nod_down: nose went DOWN at some point (y increased from baseline)
            baseline = nose_y[0]
            if gesture == "nod_up":
                peak_dir_movement = baseline - min(nose_y)  # positive means moved up
            else:
                peak_dir_movement = max(nose_y) - baseline  # positive means moved down
            
            logger.info(f"  nod: movement={movement:.5f}, peak_dir={peak_dir_movement:.5f}, nose_y_range=[{min(nose_y):.4f}, {max(nose_y):.4f}]")
            
            threshold = 0.005
            if movement > threshold and peak_dir_movement > 0.002:
                confidence = min(movement / 0.03, 1.0)
                logger.info(f"  -> PASS confidence={confidence:.3f}")
                return True, confidence
            else:
                logger.info(f"  -> FAIL (threshold={threshold})")
                return False, movement / 0.06
        
        # ---------- TURN LEFT / TURN RIGHT ----------
        elif gesture in ["turn_left", "turn_right"]:
            nose_x = [lm[NOSE_TIP][0] for lm in all_landmarks]
            movement = max(nose_x) - min(nose_x)
            
            baseline = nose_x[0]
            if gesture == "turn_left":
                peak_dir = baseline - min(nose_x)
            else:
                peak_dir = max(nose_x) - baseline
            
            logger.info(f"  turn: movement={movement:.5f}, peak_dir={peak_dir:.5f}, nose_x_range=[{min(nose_x):.4f}, {max(nose_x):.4f}]")
            
            threshold = 0.008
            if movement > threshold and peak_dir > 0.003:
                confidence = min(movement / 0.04, 1.0)
                logger.info(f"  -> PASS confidence={confidence:.3f}")
                return True, confidence
            else:
                logger.info(f"  -> FAIL (threshold={threshold})")
                return False, movement / 0.1
        
        # ---------- TILT LEFT / TILT RIGHT ----------
        elif gesture in ["tilt_left", "tilt_right"]:
            eye_angles = []
            for lm in all_landmarks:
                dy = lm[RIGHT_EYE][1] - lm[LEFT_EYE][1]
                dx = lm[RIGHT_EYE][0] - lm[LEFT_EYE][0]
                angle = np.arctan2(dy, dx)
                eye_angles.append(angle)
            
            angle_range = max(eye_angles) - min(eye_angles)
            baseline = eye_angles[0]
            if gesture == "tilt_left":
                peak_dir = max(eye_angles) - baseline
            else:
                peak_dir = baseline - min(eye_angles)
            
            logger.info(f"  tilt: angle_range={angle_range:.5f} rad, peak_dir={peak_dir:.5f}")
            
            threshold = 0.02  # ~1.1 degrees
            if angle_range > threshold and peak_dir > 0.01:
                confidence = min(angle_range / 0.1, 1.0)
                logger.info(f"  -> PASS confidence={confidence:.3f}")
                return True, confidence
            else:
                logger.info(f"  -> FAIL (threshold={threshold})")
                return False, angle_range / 0.2
        
        # ---------- OPEN MOUTH ----------
        elif gesture == "open_mouth":
            mouth_openings = []
            for lm in all_landmarks:
                upper_lip = lm[13]
                lower_lip = lm[14]
                opening = abs(lower_lip[1] - upper_lip[1])
                mouth_openings.append(opening)
            
            max_opening = max(mouth_openings)
            min_opening = min(mouth_openings)
            change = max_opening - min_opening
            
            logger.info(f"  open_mouth: max_opening={max_opening:.5f}, min={min_opening:.5f}, change={change:.5f}")
            
            # Either the mouth reached a large opening, or it changed significantly
            if max_opening > 0.006 or change > 0.003:
                confidence = min(max_opening / 0.02, 1.0)
                logger.info(f"  -> PASS confidence={confidence:.3f}")
                return True, confidence
            else:
                logger.info(f"  -> FAIL")
                return False, max_opening / 0.05
        
        # ---------- CLOSE EYES ----------
        elif gesture == "close_eyes":
            ear_values = []
            for lm in all_landmarks:
                # Proper EAR: vertical / horizontal for each eye
                left_v = abs(lm[159][1] - lm[145][1])
                left_h = abs(lm[33][0] - lm[133][0]) + 1e-6
                right_v = abs(lm[386][1] - lm[374][1])
                right_h = abs(lm[263][0] - lm[362][0]) + 1e-6
                ear = ((left_v / left_h) + (right_v / right_h)) / 2.0
                ear_values.append(ear)
            
            min_ear = min(ear_values)
            max_ear = max(ear_values)
            ear_drop = max_ear - min_ear
            
            logger.info(f"  close_eyes: min_EAR={min_ear:.5f}, max_EAR={max_ear:.5f}, drop={ear_drop:.5f}")
            
            # EAR typically ~0.25-0.35 open, drops to ~0.05-0.15 closed
            if min_ear < 0.20 or ear_drop > 0.05:
                confidence = min(ear_drop / 0.15, 1.0) if ear_drop > 0.05 else min((0.25 - min_ear) / 0.2, 1.0)
                logger.info(f"  -> PASS confidence={confidence:.3f}")
                return True, max(confidence, 0.6)
            else:
                logger.info(f"  -> FAIL")
                return False, ear_drop / 0.15
        
        # ---------- RAISE EYEBROWS ----------
        elif gesture == "raise_eyebrows":
            brow_y = []
            for lm in all_landmarks:
                avg = (lm[70][1] + lm[300][1]) / 2.0
                brow_y.append(avg)
            
            # Peak upward movement from any starting point
            movement = max(brow_y) - min(brow_y)
            # Eyebrows move up = y decreases
            peak_up = brow_y[0] - min(brow_y)
            
            logger.info(f"  raise_eyebrows: range={movement:.5f}, peak_up={peak_up:.5f}")
            
            if movement > 0.003 or peak_up > 0.002:
                confidence = min(movement / 0.015, 1.0)
                logger.info(f"  -> PASS confidence={confidence:.3f}")
                return True, max(confidence, 0.6)
            else:
                logger.info(f"  -> FAIL")
                return False, movement / 0.03
        
        # ---------- BLINK ----------
        elif gesture == "blink":
            ear_values = []
            for lm in all_landmarks:
                left_v = abs(lm[159][1] - lm[145][1])
                left_h = abs(lm[33][0] - lm[133][0]) + 1e-6
                right_v = abs(lm[386][1] - lm[374][1])
                right_h = abs(lm[263][0] - lm[362][0]) + 1e-6
                ear = ((left_v / left_h) + (right_v / right_h)) / 2.0
                ear_values.append(ear)
            
            min_ear = min(ear_values)
            max_ear = max(ear_values)
            ear_range = max_ear - min_ear
            
            logger.info(f"  blink: min_EAR={min_ear:.5f}, max_EAR={max_ear:.5f}, range={ear_range:.5f}")
            
            # Blink = EAR drops then rises (range > threshold)
            if ear_range > 0.02:
                confidence = min(ear_range / 0.1, 1.0)
                logger.info(f"  -> PASS confidence={confidence:.3f}")
                return True, max(confidence, 0.6)
            else:
                logger.info(f"  -> FAIL")
                return False, ear_range / 0.1
        
        logger.warning(f"Unknown gesture: {gesture}")
        return False, 0.0
    
    def _verify_expression(self, expression: str, video_frames: List[np.ndarray]) -> tuple[bool, float]:
        """
        Verify expression challenge using facial landmark analysis.
        Checks ALL frames and uses the best-scoring one (not just the middle frame).
        """
        if len(video_frames) == 0:
            return False, 0.0
        
        # Extract landmarks from frames
        all_landmarks = []
        if self.face_landmarker is None:
            logger.warning("face_landmarker is None — cannot verify expression")
            return False, 0.0
        for frame in video_frames:
            rgb_frame = self.preprocess_frame(frame)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb_frame)
            try:
                detection_result = self.face_landmarker.detect(mp_image)
            except Exception:
                continue
            
            if detection_result.face_landmarks and len(detection_result.face_landmarks) > 0:
                landmarks = detection_result.face_landmarks[0]
                landmarks_array = np.array([[lm.x, lm.y, lm.z] for lm in landmarks])
                all_landmarks.append(landmarks_array)
        
        if len(all_landmarks) == 0:
            logger.warning(f"Expression '{expression}': 0 frames had faces out of {len(video_frames)}")
            return False, 0.0
        
        logger.info(f"Expression '{expression}': {len(all_landmarks)} frames with faces")
        
        # Key landmarks
        LEFT_MOUTH = 61
        RIGHT_MOUTH = 291
        UPPER_LIP = 13
        LOWER_LIP = 14
        LEFT_EYEBROW = 70
        RIGHT_EYEBROW = 300
        
        # Check ALL frames and use the best score
        best_confidence = 0.0
        best_pass = False
        
        for fi, landmarks in enumerate(all_landmarks):
            passed = False
            confidence = 0.0
            
            if expression == "smile":
                left_mouth = landmarks[LEFT_MOUTH]
                right_mouth = landmarks[RIGHT_MOUTH]
                mouth_width = abs(right_mouth[0] - left_mouth[0])
                
                # Smile: corners of mouth are higher (lower y) than center of lip
                mouth_corner_avg_y = (left_mouth[1] + right_mouth[1]) / 2.0
                upper_lip_y = landmarks[UPPER_LIP][1]
                
                # Also check: mouth width relative to face width (eye-to-eye)
                face_width = abs(landmarks[263][0] - landmarks[33][0]) + 1e-6
                width_ratio = mouth_width / face_width
                
                smile_indicator = mouth_corner_avg_y - upper_lip_y
                
                if fi == 0:
                    logger.info(f"  smile: width={mouth_width:.4f}, width_ratio={width_ratio:.4f}, indicator={smile_indicator:.5f}")
                
                # Very lenient: just needs mouth to be somewhat wide  
                if width_ratio > 0.35 or smile_indicator > 0.001:
                    confidence = min(max(width_ratio / 0.5, smile_indicator / 0.02), 1.0)
                    passed = True
            
            elif expression == "frown":
                left_mouth = landmarks[LEFT_MOUTH]
                right_mouth = landmarks[RIGHT_MOUTH]
                mouth_corner_avg_y = (left_mouth[1] + right_mouth[1]) / 2.0
                
                # Frown: eyebrows lower (higher y), mouth corners down
                left_brow_y = landmarks[LEFT_EYEBROW][1]
                right_brow_y = landmarks[RIGHT_EYEBROW][1]
                avg_brow_y = (left_brow_y + right_brow_y) / 2.0
                
                if fi == 0:
                    logger.info(f"  frown: brow_y={avg_brow_y:.4f}, mouth_corner_y={mouth_corner_avg_y:.4f}")
                
                # Frown: brows are lower than usual (y > 0.33 typically)
                if avg_brow_y > 0.32:
                    confidence = min((avg_brow_y - 0.32) / 0.05, 1.0)
                    passed = True
            
            elif expression == "surprised":
                left_eye_v = abs(landmarks[159][1] - landmarks[145][1])
                right_eye_v = abs(landmarks[386][1] - landmarks[374][1])
                avg_eye = (left_eye_v + right_eye_v) / 2.0
                
                mouth_opening = abs(landmarks[LOWER_LIP][1] - landmarks[UPPER_LIP][1])
                
                if fi == 0:
                    logger.info(f"  surprised: eye_opening={avg_eye:.5f}, mouth_opening={mouth_opening:.5f}")
                
                # Either eyes wide OR mouth open counts
                if avg_eye > 0.008 or mouth_opening > 0.008:
                    confidence = min((avg_eye + mouth_opening) / 0.03, 1.0)
                    passed = True
            
            elif expression == "neutral":
                mouth_opening = abs(landmarks[LOWER_LIP][1] - landmarks[UPPER_LIP][1])
                
                if fi == 0:
                    logger.info(f"  neutral: mouth_opening={mouth_opening:.5f}")
                
                # Neutral is easy — mouth not wide open
                if mouth_opening < 0.04:
                    confidence = 0.85
                    passed = True
            
            elif expression == "angry":
                left_brow_y = landmarks[LEFT_EYEBROW][1]
                right_brow_y = landmarks[RIGHT_EYEBROW][1]
                avg_brow_y = (left_brow_y + right_brow_y) / 2.0
                
                # Brow distance (closer together = angry)
                brow_dist = abs(landmarks[LEFT_EYEBROW][0] - landmarks[RIGHT_EYEBROW][0])
                
                if fi == 0:
                    logger.info(f"  angry: brow_y={avg_brow_y:.4f}, brow_dist={brow_dist:.4f}")
                
                # Angry: brows low or close together
                if avg_brow_y > 0.30 or brow_dist < 0.15:
                    confidence = 0.7
                    passed = True
            
            if passed and confidence > best_confidence:
                best_confidence = confidence
                best_pass = True
        
        logger.info(f"  Expression '{expression}' best result: pass={best_pass}, confidence={best_confidence:.3f}")
        return best_pass, best_confidence
    
    def __del__(self):
        """Clean up MediaPipe resources"""
        if self._face_landmarker is not None:
            self._face_landmarker.close()
