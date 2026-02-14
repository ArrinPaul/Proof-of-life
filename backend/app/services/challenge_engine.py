"""
Challenge Engine for generating random verification challenges
"""
import secrets
import time
from typing import List
from ..models.data_models import Challenge, ChallengeSequence, ChallengeType


class ChallengeEngine:
    """
    Generates unpredictable visual challenges with anti-replay protection.
    
    Validates Requirements 2.2, 2.3, 11.1
    """
    
    # Gesture pool with at least 10 distinct types (Requirement 2.2)
    GESTURE_POOL = [
        "nod_up",
        "nod_down",
        "turn_left",
        "turn_right",
        "tilt_left",
        "tilt_right",
        "open_mouth",
        "close_eyes",
        "raise_eyebrows",
        "blink"
    ]
    
    # Expression pool with at least 5 distinct types (Requirement 2.3)
    EXPRESSION_POOL = [
        "smile",
        "frown",
        "surprised",
        "neutral",
        "angry"
    ]
    
    # Human-readable instructions for each gesture
    GESTURE_INSTRUCTIONS = {
        "nod_up": "Nod your head up",
        "nod_down": "Nod your head down",
        "turn_left": "Turn your head to the left",
        "turn_right": "Turn your head to the right",
        "tilt_left": "Tilt your head to the left",
        "tilt_right": "Tilt your head to the right",
        "open_mouth": "Open your mouth wide",
        "close_eyes": "Close your eyes",
        "raise_eyebrows": "Raise your eyebrows",
        "blink": "Blink your eyes"
    }
    
    # Human-readable instructions for each expression
    EXPRESSION_INSTRUCTIONS = {
        "smile": "Smile",
        "frown": "Frown",
        "surprised": "Look surprised",
        "neutral": "Keep a neutral expression",
        "angry": "Look angry"
    }
    
    def generate_nonce(self) -> str:
        """
        Generate a cryptographic nonce for anti-replay protection.
        
        Uses secrets module for cryptographically secure random generation.
        Validates Requirement 11.1
        
        Returns:
            str: A 32-character hexadecimal nonce
        """
        return secrets.token_hex(16)  # 16 bytes = 32 hex characters
    
    def generate_challenge_sequence(
        self, 
        session_id: str, 
        num_challenges: int = 3
    ) -> ChallengeSequence:
        """
        Generate a random sequence of gestures and expressions.
        
        Validates Requirements 2.1, 2.4, 2.5
        
        Args:
            session_id: Unique identifier for the session
            num_challenges: Number of challenges to generate (default 3)
            
        Returns:
            ChallengeSequence: A sequence with nonce, timestamp, and challenges
        """
        # Generate cryptographic nonce (Requirement 11.1)
        nonce = self.generate_nonce()
        
        # Record timestamp (Requirement 2.5)
        timestamp = time.time()
        
        # Generate random challenges
        challenges = []
        for i in range(num_challenges):
            # Randomly choose between gesture and expression
            challenge_type = secrets.choice([ChallengeType.GESTURE, ChallengeType.EXPRESSION])
            
            if challenge_type == ChallengeType.GESTURE:
                # Select random gesture from pool (Requirement 2.2)
                gesture = secrets.choice(self.GESTURE_POOL)
                instruction = self.GESTURE_INSTRUCTIONS[gesture]
                challenge_id = f"{session_id}_gesture_{i}_{gesture}"
            else:
                # Select random expression from pool (Requirement 2.3)
                expression = secrets.choice(self.EXPRESSION_POOL)
                instruction = self.EXPRESSION_INSTRUCTIONS[expression]
                challenge_id = f"{session_id}_expression_{i}_{expression}"
            
            challenge = Challenge(
                challenge_id=challenge_id,
                type=challenge_type,
                instruction=instruction,
                timeout_seconds=8
            )
            challenges.append(challenge)
        
        return ChallengeSequence(
            session_id=session_id,
            nonce=nonce,
            timestamp=timestamp,
            challenges=challenges
        )
    
    def validate_nonce(self, nonce: str, session_id: str) -> bool:
        """
        Verify nonce is valid and not reused.
        
        Note: This method signature is defined for interface completeness.
        Actual nonce validation is implemented in DatabaseService to check
        against stored nonces.
        
        Args:
            nonce: The nonce to validate
            session_id: The session identifier
            
        Returns:
            bool: True if nonce is valid and not reused
        """
        # This will be implemented with database integration
        # For now, basic validation that nonce is not empty
        return bool(nonce and session_id)
