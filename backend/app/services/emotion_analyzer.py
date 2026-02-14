"""
Emotion Analyzer for detecting and verifying emotional expressions
"""
import time
import numpy as np
from typing import List, Optional
from ..models.data_models import EmotionResult


class EmotionAnalyzer:
    """
    Verifies genuine human emotional responses using DeepFace.
    
    Validates Requirement 6.1: Emotion detection using DeepFace
    """
    
    def __init__(self):
        """
        Initialize EmotionAnalyzer with DeepFace integration.
        
        DeepFace is initialized lazily when first needed to handle cases
        where the library is not available (graceful degradation).
        
        Validates Requirement 6.1
        """
        self._deepface_available = None
        self._deepface = None
    
    @property
    def deepface_available(self) -> bool:
        """
        Check if DeepFace is available for emotion detection.
        
        Returns:
            bool: True if DeepFace can be imported, False otherwise
        """
        if self._deepface_available is None:
            try:
                from deepface import DeepFace
                self._deepface = DeepFace
                self._deepface_available = True
            except ImportError:
                self._deepface_available = False
        
        return self._deepface_available
    
    def detect_emotion(self, frame: np.ndarray) -> EmotionResult:
        """
        Identify dominant emotion in a single frame.
        
        Uses DeepFace to analyze facial expressions and detect emotions.
        Supports at least 5 emotions: happy, sad, surprised, neutral, angry.
        
        Args:
            frame: Video frame in BGR format (OpenCV default)
            
        Returns:
            EmotionResult: Dominant emotion, confidence, and timestamp
            
        Validates Requirements 6.1, 6.4
        """
        if not self.deepface_available:
            # Graceful degradation: return neutral emotion with low confidence
            return EmotionResult(
                dominant_emotion="neutral",
                confidence=0.0,
                timestamp=time.time()
            )
        
        if frame is None or frame.size == 0:
            # Invalid frame
            return EmotionResult(
                dominant_emotion="neutral",
                confidence=0.0,
                timestamp=time.time()
            )
        
        try:
            # Analyze emotion using DeepFace
            # DeepFace.analyze returns a list of dictionaries (one per face)
            # We only analyze the first detected face
            result = self._deepface.analyze(
                img_path=frame,
                actions=['emotion'],
                enforce_detection=False,  # Don't fail if no face detected
                detector_backend='opencv',  # Use OpenCV for speed
                silent=True  # Suppress DeepFace logging
            )
            
            # Handle both single face (dict) and multiple faces (list) results
            if isinstance(result, list):
                if len(result) == 0:
                    # No face detected
                    return EmotionResult(
                        dominant_emotion="neutral",
                        confidence=0.0,
                        timestamp=time.time()
                    )
                result = result[0]
            
            # Extract emotion data
            emotion_scores = result.get('emotion', {})
            
            if not emotion_scores:
                # No emotion data
                return EmotionResult(
                    dominant_emotion="neutral",
                    confidence=0.0,
                    timestamp=time.time()
                )
            
            # Find dominant emotion (highest score)
            dominant_emotion = max(emotion_scores, key=emotion_scores.get)
            confidence = emotion_scores[dominant_emotion] / 100.0  # Convert percentage to 0-1
            
            return EmotionResult(
                dominant_emotion=dominant_emotion,
                confidence=confidence,
                timestamp=time.time()
            )
        
        except Exception as e:
            # Handle any DeepFace errors gracefully
            # In production, this would be logged
            return EmotionResult(
                dominant_emotion="neutral",
                confidence=0.0,
                timestamp=time.time()
            )
    
    def verify_natural_transitions(
        self, 
        emotion_sequence: List[EmotionResult]
    ) -> float:
        """
        Check for realistic emotional state changes across frames.
        
        Analyzes the sequence of detected emotions to verify natural transitions.
        Penalizes instantaneous or unnatural changes that suggest synthetic content.
        
        Natural transitions:
        - Gradual changes in emotion over multiple frames
        - Smooth confidence changes
        - Realistic emotion progressions (e.g., neutral -> surprise -> happy)
        
        Unnatural transitions (penalized):
        - Instantaneous emotion switches (e.g., happy -> angry in 1 frame)
        - Rigid patterns (same emotion with identical confidence)
        - Impossible progressions
        
        Args:
            emotion_sequence: List of EmotionResult from consecutive frames
            
        Returns:
            float: Transition naturalness score (0.0-1.0)
                  1.0 = perfectly natural transitions
                  0.0 = highly unnatural/synthetic patterns
                  
        Validates Requirements 6.2, 6.5
        """
        if not emotion_sequence or len(emotion_sequence) < 2:
            # Need at least 2 frames to analyze transitions
            return 1.0
        
        # Track penalties for unnatural patterns
        penalty = 0.0
        max_penalty = 1.0
        
        # Analyze frame-to-frame transitions
        for i in range(1, len(emotion_sequence)):
            prev = emotion_sequence[i - 1]
            curr = emotion_sequence[i]
            
            # Check for instantaneous emotion changes
            # If emotion changes AND confidence is high on both, it's suspicious
            if prev.dominant_emotion != curr.dominant_emotion:
                if prev.confidence > 0.7 and curr.confidence > 0.7:
                    # High-confidence instantaneous change is unnatural
                    penalty += 0.2
            
            # Check for rigid patterns (identical confidence values)
            # Real emotions have natural variation in confidence
            if abs(prev.confidence - curr.confidence) < 0.01:
                # Too rigid, likely synthetic
                penalty += 0.05
            
            # Check for impossible confidence jumps
            # Natural emotions don't go from 0.1 to 0.9 instantly
            confidence_change = abs(curr.confidence - prev.confidence)
            if confidence_change > 0.5:
                penalty += 0.15
        
        # Check for overall rigidity across the sequence
        # Natural sequences have some variation
        confidences = [e.confidence for e in emotion_sequence]
        if len(set(confidences)) == 1:
            # All confidences identical = synthetic
            penalty += 0.3
        
        # Calculate final score (1.0 - normalized penalty)
        score = max(0.0, 1.0 - min(penalty, max_penalty))
        
        return score

    
    def compute_emotion_score(
        self, 
        video_frames: List[np.ndarray],
        expected_emotion: Optional[str] = None
    ) -> float:
        """
        Analyze emotional authenticity and natural transitions across video frames.
        
        Combines emotion detection and transition analysis to produce a final
        emotion authenticity score. This score represents how genuine and natural
        the emotional expressions appear across the video sequence.
        
        Process:
        1. Detect emotions in each frame
        2. Analyze transition naturalness
        3. If expected_emotion is provided, verify it was detected
        4. Combine signals into final score
        
        Args:
            video_frames: List of video frames in BGR format (OpenCV default)
            expected_emotion: Optional emotion to verify (for expression challenges)
            
        Returns:
            float: Emotion authenticity score (0.0-1.0)
                  1.0 = highly authentic, natural emotions
                  0.0 = synthetic, unnatural, or failed to detect
                  
        Validates Requirements 6.3
        """
        if not video_frames or len(video_frames) == 0:
            # No frames to analyze
            return 0.0
        
        # Step 1: Detect emotions in each frame
        emotion_sequence = []
        for frame in video_frames:
            emotion_result = self.detect_emotion(frame)
            emotion_sequence.append(emotion_result)
        
        # Step 2: Analyze transition naturalness
        transition_score = self.verify_natural_transitions(emotion_sequence)
        
        # Step 3: Calculate average confidence across frames
        avg_confidence = sum(e.confidence for e in emotion_sequence) / len(emotion_sequence)
        
        # Step 4: If expected emotion is provided, verify it was detected
        emotion_match_score = 1.0
        if expected_emotion is not None:
            # Check if the expected emotion appears in the sequence
            detected_emotions = [e.dominant_emotion for e in emotion_sequence]
            
            # Normalize emotion names (DeepFace uses 'surprise' not 'surprised')
            normalized_expected = expected_emotion.lower()
            if normalized_expected == 'surprised':
                normalized_expected = 'surprise'
            
            if normalized_expected in detected_emotions:
                # Expected emotion was detected
                # Calculate what percentage of frames showed this emotion
                match_count = detected_emotions.count(normalized_expected)
                emotion_match_score = min(1.0, match_count / len(detected_emotions) * 2)
            else:
                # Expected emotion was not detected
                emotion_match_score = 0.0
        
        # Step 5: Combine scores
        # Weight: 40% transition naturalness, 30% confidence, 30% emotion match
        final_score = (
            0.4 * transition_score +
            0.3 * avg_confidence +
            0.3 * emotion_match_score
        )
        
        # Ensure score is in valid range
        return max(0.0, min(1.0, final_score))
