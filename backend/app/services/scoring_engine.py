"""
Scoring Engine for Multi-Factor Proof of Life Authentication

This module implements the scoring engine that combines verification signals
from multiple ML models (liveness, deepfake, emotion) into a final decision.
"""
import time
from app.models.data_models import ScoringResult


class ScoringEngine:
    """
    Combines multiple verification signals into a final authentication decision.
    
    The scoring engine uses a weighted formula to compute the final score:
    final_score = 0.4 × liveness_score + 0.3 × deepfake_score + 0.3 × emotion_score
    
    A verification passes if the final score is >= 0.70.
    """
    
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
        """
        Calculate weighted final score and verification decision.
        
        Args:
            liveness_score: Score from liveness detection (0.0-1.0)
            deepfake_score: Score from deepfake detection (0.0-1.0)
            emotion_score: Score from emotion analysis (0.0-1.0)
        
        Returns:
            ScoringResult containing all scores and pass/fail decision
        
        Requirements:
            - 7.1: Uses weighted formula (0.4 × liveness + 0.3 × deepfake + 0.3 × emotion)
            - 7.2: Compares final score against threshold of 0.70
            - 7.3: Marks verification as successful if final_score >= 0.70
            - 7.4: Marks verification as failed if final_score < 0.70
        """
        # Calculate weighted final score using the formula
        final_score = (
            self.LIVENESS_WEIGHT * liveness_score +
            self.DEEPFAKE_WEIGHT * deepfake_score +
            self.EMOTION_WEIGHT * emotion_score
        )
        
        # Determine pass/fail based on threshold comparison
        passed = final_score >= self.THRESHOLD
        
        # Create and return scoring result
        return ScoringResult(
            liveness_score=liveness_score,
            deepfake_score=deepfake_score,
            emotion_score=emotion_score,
            final_score=final_score,
            passed=passed,
            timestamp=time.time()
        )
