"""
Unit tests for EmotionAnalyzer class
"""
import pytest
import numpy as np
from app.services.emotion_analyzer import EmotionAnalyzer
from app.models.data_models import EmotionResult


def _is_deepface_available() -> bool:
    """Helper function to check if DeepFace is available"""
    try:
        import deepface
        return True
    except ImportError:
        return False


class TestEmotionAnalyzerInitialization:
    """Test EmotionAnalyzer initialization"""
    
    def test_initialization(self):
        """Test that EmotionAnalyzer initializes correctly"""
        analyzer = EmotionAnalyzer()
        
        # Verify initialization
        assert analyzer._deepface_available is None
        assert analyzer._deepface is None
    
    def test_deepface_availability_check(self):
        """Test that deepface_available property checks for DeepFace"""
        analyzer = EmotionAnalyzer()
        
        # Check availability (will be True or False depending on environment)
        available = analyzer.deepface_available
        
        # Verify it's a boolean
        assert isinstance(available, bool)
        
        # Verify cached result is consistent
        assert analyzer.deepface_available == available


class TestEmotionDetection:
    """Test emotion detection functionality"""
    
    def test_detect_emotion_with_invalid_frame(self):
        """Test emotion detection with None frame"""
        analyzer = EmotionAnalyzer()
        
        # Test with None frame
        result = analyzer.detect_emotion(None)
        
        # Should return neutral emotion with 0 confidence
        assert isinstance(result, EmotionResult)
        assert result.dominant_emotion == "neutral"
        assert result.confidence == 0.0
        assert result.timestamp > 0
    
    def test_detect_emotion_with_empty_frame(self):
        """Test emotion detection with empty frame"""
        analyzer = EmotionAnalyzer()
        
        # Test with empty frame
        empty_frame = np.array([])
        result = analyzer.detect_emotion(empty_frame)
        
        # Should return neutral emotion with 0 confidence
        assert isinstance(result, EmotionResult)
        assert result.dominant_emotion == "neutral"
        assert result.confidence == 0.0
    
    def test_detect_emotion_without_deepface(self):
        """Test graceful degradation when DeepFace is not available"""
        analyzer = EmotionAnalyzer()
        
        # Force DeepFace to be unavailable
        analyzer._deepface_available = False
        
        # Create a test frame
        test_frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        
        # Detect emotion
        result = analyzer.detect_emotion(test_frame)
        
        # Should return neutral emotion with 0 confidence (graceful degradation)
        assert isinstance(result, EmotionResult)
        assert result.dominant_emotion == "neutral"
        assert result.confidence == 0.0
        assert result.timestamp > 0
    
    def test_detect_emotion_returns_emotion_result(self):
        """Test that detect_emotion returns EmotionResult dataclass"""
        analyzer = EmotionAnalyzer()
        
        # Create a test frame
        test_frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        
        # Detect emotion
        result = analyzer.detect_emotion(test_frame)
        
        # Verify result structure
        assert isinstance(result, EmotionResult)
        assert hasattr(result, 'dominant_emotion')
        assert hasattr(result, 'confidence')
        assert hasattr(result, 'timestamp')
        assert isinstance(result.dominant_emotion, str)
        assert isinstance(result.confidence, (float, np.floating))
        assert isinstance(result.timestamp, float)
        assert 0.0 <= result.confidence <= 1.0
    
    @pytest.mark.skipif(
        not _is_deepface_available(),
        reason="DeepFace not installed"
    )
    def test_detect_emotion_with_deepface(self):
        """Test emotion detection with DeepFace (if available)"""
        analyzer = EmotionAnalyzer()
        
        # Skip if DeepFace not available
        if not analyzer.deepface_available:
            pytest.skip("DeepFace not available")
        
        # Create a test frame (neutral face)
        test_frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        
        # Detect emotion
        result = analyzer.detect_emotion(test_frame)
        
        # Verify result
        assert isinstance(result, EmotionResult)
        assert result.dominant_emotion in [
            'happy', 'sad', 'angry', 'surprise', 'fear', 'disgust', 'neutral'
        ]
        assert 0.0 <= result.confidence <= 1.0
        assert result.timestamp > 0


class TestEmotionDetectionCoreEmotions:
    """
    Test detection of 5 core emotions (happy, sad, surprised, neutral, angry)
    Validates Requirements 6.4
    """
    
    def test_core_emotions_supported(self):
        """Test that analyzer can detect the 5 core emotions required by spec"""
        analyzer = EmotionAnalyzer()
        
        # The 5 core emotions required by Requirement 6.4
        core_emotions = ['happy', 'sad', 'surprise', 'neutral', 'angry']
        
        # DeepFace supports these emotions (plus fear and disgust)
        # We verify that the analyzer can return any of these emotions
        # by checking the detect_emotion method returns valid EmotionResult
        
        test_frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        result = analyzer.detect_emotion(test_frame)
        
        # Verify result structure is correct for emotion detection
        assert isinstance(result, EmotionResult)
        assert isinstance(result.dominant_emotion, str)
        assert isinstance(result.confidence, (float, np.floating))
        assert 0.0 <= result.confidence <= 1.0
        
        # The emotion should be one of the supported emotions
        # (including the 5 core emotions)
        supported_emotions = core_emotions + ['fear', 'disgust']
        assert result.dominant_emotion in supported_emotions
    
    @pytest.mark.skipif(
        not _is_deepface_available(),
        reason="DeepFace not installed"
    )
    def test_emotion_detection_consistency(self):
        """Test that emotion detection returns consistent results for same frame"""
        analyzer = EmotionAnalyzer()
        
        if not analyzer.deepface_available:
            pytest.skip("DeepFace not available")
        
        # Create a test frame
        test_frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        
        # Detect emotion twice
        result1 = analyzer.detect_emotion(test_frame)
        result2 = analyzer.detect_emotion(test_frame)
        
        # Results should be consistent (same emotion detected)
        assert result1.dominant_emotion == result2.dominant_emotion
        # Confidence should be similar (within 10% due to potential randomness)
        assert abs(result1.confidence - result2.confidence) < 0.1




class TestEmotionTransitionAnalysis:
    """
    Test natural transition verification
    Validates Requirements 6.2, 6.5
    """
    
    def test_natural_transitions_score_high(self):
        """Test that natural emotion transitions score high"""
        analyzer = EmotionAnalyzer()
        
        # Create a natural emotion sequence: gradual change with varying confidence
        natural_sequence = [
            EmotionResult(dominant_emotion="neutral", confidence=0.6, timestamp=1.0),
            EmotionResult(dominant_emotion="neutral", confidence=0.65, timestamp=1.1),
            EmotionResult(dominant_emotion="surprise", confidence=0.5, timestamp=1.2),
            EmotionResult(dominant_emotion="surprise", confidence=0.7, timestamp=1.3),
            EmotionResult(dominant_emotion="happy", confidence=0.6, timestamp=1.4),
            EmotionResult(dominant_emotion="happy", confidence=0.75, timestamp=1.5),
        ]
        
        score = analyzer.verify_natural_transitions(natural_sequence)
        
        # Natural transitions should score high (> 0.7)
        assert score > 0.7
        assert 0.0 <= score <= 1.0
    
    def test_unnatural_transitions_score_low(self):
        """Test that unnatural emotion transitions score low"""
        analyzer = EmotionAnalyzer()
        
        # Create an unnatural sequence: instantaneous high-confidence changes
        unnatural_sequence = [
            EmotionResult(dominant_emotion="happy", confidence=0.9, timestamp=1.0),
            EmotionResult(dominant_emotion="angry", confidence=0.9, timestamp=1.1),
            EmotionResult(dominant_emotion="sad", confidence=0.9, timestamp=1.2),
            EmotionResult(dominant_emotion="surprise", confidence=0.9, timestamp=1.3),
        ]
        
        score = analyzer.verify_natural_transitions(unnatural_sequence)
        
        # Unnatural transitions should score low (< 0.5)
        assert score < 0.5
        assert 0.0 <= score <= 1.0
    
    def test_rigid_patterns_penalized(self):
        """Test that rigid/synthetic emotional patterns are penalized"""
        analyzer = EmotionAnalyzer()
        
        # Create a rigid sequence: same emotion with identical confidence
        rigid_sequence = [
            EmotionResult(dominant_emotion="neutral", confidence=0.8, timestamp=1.0),
            EmotionResult(dominant_emotion="neutral", confidence=0.8, timestamp=1.1),
            EmotionResult(dominant_emotion="neutral", confidence=0.8, timestamp=1.2),
            EmotionResult(dominant_emotion="neutral", confidence=0.8, timestamp=1.3),
        ]
        
        score = analyzer.verify_natural_transitions(rigid_sequence)
        
        # Rigid patterns should be penalized (< 0.7)
        assert score < 0.7
        assert 0.0 <= score <= 1.0
    
    def test_empty_sequence_returns_high_score(self):
        """Test that empty or single-frame sequences return high score"""
        analyzer = EmotionAnalyzer()
        
        # Empty sequence
        score_empty = analyzer.verify_natural_transitions([])
        assert score_empty == 1.0
        
        # Single frame
        single_frame = [
            EmotionResult(dominant_emotion="happy", confidence=0.8, timestamp=1.0)
        ]
        score_single = analyzer.verify_natural_transitions(single_frame)
        assert score_single == 1.0
    
    def test_confidence_jumps_penalized(self):
        """Test that large confidence jumps are penalized"""
        analyzer = EmotionAnalyzer()
        
        # Sequence with impossible confidence jumps
        jump_sequence = [
            EmotionResult(dominant_emotion="neutral", confidence=0.1, timestamp=1.0),
            EmotionResult(dominant_emotion="neutral", confidence=0.9, timestamp=1.1),
            EmotionResult(dominant_emotion="neutral", confidence=0.2, timestamp=1.2),
            EmotionResult(dominant_emotion="neutral", confidence=0.95, timestamp=1.3),
        ]
        
        score = analyzer.verify_natural_transitions(jump_sequence)
        
        # Large jumps should be penalized
        assert score < 0.6
        assert 0.0 <= score <= 1.0
    
    def test_gradual_emotion_change_natural(self):
        """Test that gradual emotion changes are considered natural"""
        analyzer = EmotionAnalyzer()
        
        # Gradual change with low confidence during transition
        gradual_sequence = [
            EmotionResult(dominant_emotion="neutral", confidence=0.7, timestamp=1.0),
            EmotionResult(dominant_emotion="neutral", confidence=0.65, timestamp=1.1),
            EmotionResult(dominant_emotion="happy", confidence=0.4, timestamp=1.2),
            EmotionResult(dominant_emotion="happy", confidence=0.6, timestamp=1.3),
            EmotionResult(dominant_emotion="happy", confidence=0.75, timestamp=1.4),
        ]
        
        score = analyzer.verify_natural_transitions(gradual_sequence)
        
        # Gradual changes should score high
        assert score > 0.7
        assert 0.0 <= score <= 1.0



class TestEmotionScoreComputation:
    """
    Test compute_emotion_score method
    Validates Requirements 6.3
    """
    
    def test_compute_emotion_score_with_empty_frames(self):
        """Test that empty frame list returns 0.0"""
        analyzer = EmotionAnalyzer()
        
        score = analyzer.compute_emotion_score([])
        
        assert score == 0.0
    
    def test_compute_emotion_score_returns_valid_range(self):
        """Test that emotion score is always in valid range [0.0, 1.0]"""
        analyzer = EmotionAnalyzer()
        
        # Create test frames
        test_frames = [
            np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
            for _ in range(5)
        ]
        
        score = analyzer.compute_emotion_score(test_frames)
        
        # Score must be in valid range
        assert 0.0 <= score <= 1.0
        assert isinstance(score, (float, np.floating))
    
    def test_compute_emotion_score_with_expected_emotion(self):
        """Test emotion score computation with expected emotion"""
        analyzer = EmotionAnalyzer()
        
        # Create test frames
        test_frames = [
            np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
            for _ in range(3)
        ]
        
        # Compute score with expected emotion
        score = analyzer.compute_emotion_score(test_frames, expected_emotion="happy")
        
        # Score should be in valid range
        assert 0.0 <= score <= 1.0


# Property-based tests
from hypothesis import given, strategies as st


class TestEmotionScorePropertyTests:
    """
    Property-based tests for emotion analysis
    """
    
    @given(
        num_frames=st.integers(min_value=1, max_value=20),
        frame_height=st.integers(min_value=100, max_value=480),
        frame_width=st.integers(min_value=100, max_value=640)
    )
    def test_property_emotion_score_range_validity(
        self, 
        num_frames: int, 
        frame_height: int, 
        frame_width: int
    ):
        """
        Feature: proof-of-life-auth, Property 5: Score Range Validity (Emotion)
        
        For any verification component output (emotion), the score should be 
        a value between 0.0 and 1.0 inclusive.
        
        Validates Requirements 6.3
        """
        analyzer = EmotionAnalyzer()
        
        # Generate random video frames
        video_frames = [
            np.random.randint(0, 255, (frame_height, frame_width, 3), dtype=np.uint8)
            for _ in range(num_frames)
        ]
        
        # Compute emotion score
        emotion_score = analyzer.compute_emotion_score(video_frames)
        
        # Property: Score must be in valid range [0.0, 1.0]
        assert 0.0 <= emotion_score <= 1.0
        assert isinstance(emotion_score, float)
    
    @given(
        num_frames=st.integers(min_value=1, max_value=15),
        frame_height=st.integers(min_value=100, max_value=480),
        frame_width=st.integers(min_value=100, max_value=640),
        expected_emotion=st.sampled_from(['happy', 'sad', 'surprised', 'neutral', 'angry'])
    )
    def test_property_expression_challenge_detection(
        self,
        num_frames: int,
        frame_height: int,
        frame_width: int,
        expected_emotion: str
    ):
        """
        Feature: proof-of-life-auth, Property 9: Expression Challenge Detection
        
        For any challenge that requires an expression, the emotion analyzer 
        should perform emotion detection on the video frames.
        
        Validates Requirements 6.1
        """
        analyzer = EmotionAnalyzer()
        
        # Generate random video frames (simulating expression challenge)
        video_frames = [
            np.random.randint(0, 255, (frame_height, frame_width, 3), dtype=np.uint8)
            for _ in range(num_frames)
        ]
        
        # When an expression challenge is given, emotion detection should be performed
        # This is verified by calling compute_emotion_score with expected_emotion
        emotion_score = analyzer.compute_emotion_score(
            video_frames, 
            expected_emotion=expected_emotion
        )
        
        # Property 1: Emotion detection was performed (score is computed)
        assert isinstance(emotion_score, float)
        assert 0.0 <= emotion_score <= 1.0
        
        # Property 2: Each frame should be analyzable by detect_emotion
        for frame in video_frames:
            emotion_result = analyzer.detect_emotion(frame)
            
            # Verify emotion detection returns valid EmotionResult
            assert isinstance(emotion_result, EmotionResult)
            assert isinstance(emotion_result.dominant_emotion, str)
            assert isinstance(emotion_result.confidence, float)
            assert 0.0 <= emotion_result.confidence <= 1.0
            assert emotion_result.timestamp > 0
            
            # Verify detected emotion is one of the supported emotions
            supported_emotions = ['happy', 'sad', 'angry', 'surprise', 'fear', 'disgust', 'neutral']
            assert emotion_result.dominant_emotion in supported_emotions
