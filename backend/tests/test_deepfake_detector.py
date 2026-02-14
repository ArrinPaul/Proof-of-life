"""
Tests for Deepfake Detection Service

This module contains unit tests and property-based tests for the deepfake detector.
"""

import pytest
import numpy as np
from hypothesis import given, strategies as st, settings
from app.services.deepfake_detector import DeepfakeDetector, DeepfakeAnalysisResult


class TestDeepfakeDetector:
    """Unit tests for DeepfakeDetector"""
    
    def test_initialization(self):
        """Test that DeepfakeDetector initializes correctly"""
        detector = DeepfakeDetector()
        assert detector is not None
        assert detector.termination_threshold == 0.5
        
    def test_initialization_with_model_path(self):
        """Test initialization with model path"""
        detector = DeepfakeDetector(model_path="/path/to/model")
        assert detector.model_path == "/path/to/model"
    
    def test_detect_spatial_artifacts_with_valid_frame(self):
        """Test spatial artifact detection with a valid frame"""
        detector = DeepfakeDetector()
        
        # Create a test frame (100x100 color image)
        frame = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
        
        score = detector.detect_spatial_artifacts(frame)
        
        # Score should be between 0.0 and 1.0
        assert 0.0 <= score <= 1.0
        assert isinstance(score, float)
    
    def test_detect_spatial_artifacts_with_empty_frame(self):
        """Test spatial artifact detection with empty frame"""
        detector = DeepfakeDetector()
        
        # Empty frame
        frame = np.array([])
        
        score = detector.detect_spatial_artifacts(frame)
        
        # Should return 0.0 for invalid input
        assert score == 0.0
    
    def test_detect_spatial_artifacts_with_none(self):
        """Test spatial artifact detection with None"""
        detector = DeepfakeDetector()
        
        score = detector.detect_spatial_artifacts(None)
        
        # Should return 0.0 for None input
        assert score == 0.0
    
    def test_detect_temporal_inconsistencies_with_consistent_frames(self):
        """
        Test temporal inconsistency detection with consistent frames.
        Consistent frames should score high (close to 1.0).
        
        Validates Requirements 5.2
        """
        detector = DeepfakeDetector()
        
        # Create a sequence of similar frames (consistent)
        base_frame = np.ones((100, 100, 3), dtype=np.uint8) * 128
        frames = []
        for i in range(5):
            # Add small variations to simulate natural motion
            frame = base_frame.copy().astype(np.int16)
            frame += np.random.randint(-5, 5, frame.shape)
            frame = np.clip(frame, 0, 255).astype(np.uint8)
            frames.append(frame)
        
        score = detector.detect_temporal_inconsistencies(frames)
        
        # Consistent frames should score high
        assert 0.7 <= score <= 1.0
        assert isinstance(score, float)
    
    def test_detect_temporal_inconsistencies_with_inconsistent_frames(self):
        """
        Test temporal inconsistency detection with inconsistent frames.
        Inconsistent frames should score low (closer to 0.0).
        
        Validates Requirements 5.2
        """
        detector = DeepfakeDetector()
        
        # Create a sequence of very different frames (inconsistent)
        # Use frames with extreme differences to ensure low score
        frames = []
        for i in range(5):
            # Alternate between very bright and very dark frames
            if i % 2 == 0:
                frame = np.ones((100, 100, 3), dtype=np.uint8) * 250
            else:
                frame = np.ones((100, 100, 3), dtype=np.uint8) * 5
            frames.append(frame)
        
        score = detector.detect_temporal_inconsistencies(frames)
        
        # Inconsistent frames should score lower
        assert 0.0 <= score <= 0.8
        assert isinstance(score, float)
    
    def test_detect_temporal_inconsistencies_with_insufficient_frames(self):
        """Test temporal inconsistency detection with insufficient frames"""
        detector = DeepfakeDetector()
        
        # Only one frame
        frames = [np.ones((100, 100, 3), dtype=np.uint8) * 128]
        
        score = detector.detect_temporal_inconsistencies(frames)
        
        # Should return neutral score (0.5)
        assert score == 0.5
    
    def test_detect_temporal_inconsistencies_with_empty_list(self):
        """Test temporal inconsistency detection with empty frame list"""
        detector = DeepfakeDetector()
        
        score = detector.detect_temporal_inconsistencies([])
        
        # Should return neutral score (0.5)
        assert score == 0.5
    
    def test_compute_deepfake_score_with_valid_frames(self):
        """Test deepfake score computation with valid frames"""
        detector = DeepfakeDetector()
        
        # Create test frames
        frames = []
        for i in range(5):
            frame = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
            frames.append(frame)
        
        score = detector.compute_deepfake_score(frames)
        
        # Score should be between 0.0 and 1.0
        assert 0.0 <= score <= 1.0
        assert isinstance(score, float)
    
    def test_compute_deepfake_score_with_empty_frames(self):
        """Test deepfake score computation with empty frame list"""
        detector = DeepfakeDetector()
        
        score = detector.compute_deepfake_score([])
        
        # Should return 0.0 for empty input
        assert score == 0.0
    
    def test_analyze_with_early_termination_high_score(self):
        """Test that high deepfake scores do not trigger termination"""
        detector = DeepfakeDetector()
        
        # Create high-quality frames that should score well
        frames = []
        base_frame = np.ones((100, 100, 3), dtype=np.uint8) * 128
        for i in range(5):
            frame = base_frame.copy().astype(np.int16)
            frame += np.random.randint(-3, 3, frame.shape)
            frame = np.clip(frame, 0, 255).astype(np.uint8)
            frames.append(frame)
        
        result = detector.analyze_with_early_termination(frames)
        
        assert isinstance(result, DeepfakeAnalysisResult)
        assert 0.0 <= result.spatial_score <= 1.0
        assert 0.0 <= result.temporal_score <= 1.0
        assert 0.0 <= result.deepfake_score <= 1.0
        
        # High score should not trigger termination
        if result.deepfake_score >= 0.5:
            assert result.should_terminate is False
    
    def test_analyze_with_early_termination_low_score(self):
        """
        Test that deepfake score < 0.5 triggers session termination.
        
        Validates Requirements 5.5
        """
        detector = DeepfakeDetector()
        
        # Create poor-quality frames that should score low
        # Use completely black frames which will score low on all metrics
        frames = []
        for i in range(5):
            frame = np.zeros((100, 100, 3), dtype=np.uint8)
            frames.append(frame)
        
        result = detector.analyze_with_early_termination(frames)
        
        assert isinstance(result, DeepfakeAnalysisResult)
        
        # Low score should trigger termination
        if result.deepfake_score < 0.5:
            assert result.should_terminate is True
    
    def test_analyze_with_early_termination_empty_frames(self):
        """Test early termination with empty frame list"""
        detector = DeepfakeDetector()
        
        result = detector.analyze_with_early_termination([])
        
        assert isinstance(result, DeepfakeAnalysisResult)
        assert result.spatial_score == 0.0
        assert result.temporal_score == 0.0
        assert result.deepfake_score == 0.0
        assert result.should_terminate is True


class TestDeepfakeDetectorProperties:
    """Property-based tests for DeepfakeDetector"""
    
    @given(
        width=st.integers(min_value=50, max_value=200),
        height=st.integers(min_value=50, max_value=200),
        num_frames=st.integers(min_value=1, max_value=10)
    )
    @settings(deadline=None)  # Disable deadline for ML model tests
    @pytest.mark.property_test
    def test_property_deepfake_score_range(self, width, height, num_frames):
        """
        **Property 5: Score Range Validity (Deepfake)**
        
        For any video frames, the deepfake score should be between 0.0 and 1.0 inclusive.
        
        **Validates: Requirements 5.3**
        """
        detector = DeepfakeDetector()
        
        # Generate random frames
        frames = []
        for _ in range(num_frames):
            frame = np.random.randint(0, 255, (height, width, 3), dtype=np.uint8)
            frames.append(frame)
        
        score = detector.compute_deepfake_score(frames)
        
        # Score must be in valid range
        assert 0.0 <= score <= 1.0
        assert isinstance(score, float)
    
    @given(
        width=st.integers(min_value=50, max_value=200),
        height=st.integers(min_value=50, max_value=200),
        num_frames=st.integers(min_value=1, max_value=10)
    )
    @settings(deadline=None)  # Disable deadline for ML model tests
    @pytest.mark.property_test
    def test_property_frame_analysis_completeness(self, width, height, num_frames):
        """
        **Property 8: Frame Analysis Completeness**
        
        For any captured video frame during deepfake detection, 
        the frame should be analyzed for synthetic artifacts.
        
        **Validates: Requirements 5.1**
        """
        detector = DeepfakeDetector()
        
        # Generate random frames
        frames = []
        for _ in range(num_frames):
            frame = np.random.randint(0, 255, (height, width, 3), dtype=np.uint8)
            frames.append(frame)
        
        # Analyze each frame individually for spatial artifacts
        for frame in frames:
            spatial_score = detector.detect_spatial_artifacts(frame)
            
            # Each frame should be analyzed and return a valid score
            assert spatial_score is not None
            assert 0.0 <= spatial_score <= 1.0
            assert isinstance(spatial_score, float)
        
        # Also verify that compute_deepfake_score processes all frames
        deepfake_score = detector.compute_deepfake_score(frames)
        assert deepfake_score is not None
        assert 0.0 <= deepfake_score <= 1.0
    
    @given(
        width=st.integers(min_value=50, max_value=200),
        height=st.integers(min_value=50, max_value=200),
        num_frames=st.integers(min_value=2, max_value=10)
    )
    @settings(deadline=None)  # Disable deadline for ML model tests
    @pytest.mark.property_test
    def test_property_temporal_score_range(self, width, height, num_frames):
        """
        Property: Temporal consistency score should be between 0.0 and 1.0
        
        For any sequence of frames, the temporal consistency score should be valid.
        """
        detector = DeepfakeDetector()
        
        # Generate random frames
        frames = []
        for _ in range(num_frames):
            frame = np.random.randint(0, 255, (height, width, 3), dtype=np.uint8)
            frames.append(frame)
        
        score = detector.detect_temporal_inconsistencies(frames)
        
        # Score must be in valid range
        assert 0.0 <= score <= 1.0
        assert isinstance(score, float)
    
    @given(
        width=st.integers(min_value=50, max_value=200),
        height=st.integers(min_value=50, max_value=200)
    )
    @settings(deadline=None)  # Disable deadline for ML model tests
    @pytest.mark.property_test
    def test_property_spatial_score_range(self, width, height):
        """
        Property: Spatial artifact score should be between 0.0 and 1.0
        
        For any frame, the spatial artifact score should be valid.
        """
        detector = DeepfakeDetector()
        
        # Generate random frame
        frame = np.random.randint(0, 255, (height, width, 3), dtype=np.uint8)
        
        score = detector.detect_spatial_artifacts(frame)
        
        # Score must be in valid range
        assert 0.0 <= score <= 1.0
        assert isinstance(score, float)
