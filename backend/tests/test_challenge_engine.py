"""
Unit tests for ChallengeEngine
"""
import pytest
from app.services.challenge_engine import ChallengeEngine
from app.models.data_models import ChallengeType


class TestChallengeEngine:
    """Test suite for ChallengeEngine class"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.engine = ChallengeEngine()
    
    def test_gesture_pool_size(self):
        """
        Test that gesture pool contains at least 10 distinct types.
        Validates Requirement 2.2
        """
        assert len(self.engine.GESTURE_POOL) >= 10
        # Verify all gestures are unique
        assert len(self.engine.GESTURE_POOL) == len(set(self.engine.GESTURE_POOL))
    
    def test_gesture_pool_contains_required_types(self):
        """
        Test that gesture pool contains all required gesture types.
        Validates Requirement 2.2
        """
        required_gestures = [
            "nod_up", "nod_down", "turn_left", "turn_right",
            "tilt_left", "tilt_right", "open_mouth", "close_eyes",
            "raise_eyebrows", "blink"
        ]
        for gesture in required_gestures:
            assert gesture in self.engine.GESTURE_POOL
    
    def test_expression_pool_size(self):
        """
        Test that expression pool contains at least 5 distinct types.
        Validates Requirement 2.3
        """
        assert len(self.engine.EXPRESSION_POOL) >= 5
        # Verify all expressions are unique
        assert len(self.engine.EXPRESSION_POOL) == len(set(self.engine.EXPRESSION_POOL))
    
    def test_expression_pool_contains_required_types(self):
        """
        Test that expression pool contains all required expression types.
        Validates Requirement 2.3
        """
        required_expressions = ["smile", "frown", "surprised", "neutral", "angry"]
        for expression in required_expressions:
            assert expression in self.engine.EXPRESSION_POOL
    
    def test_generate_nonce_returns_string(self):
        """
        Test that nonce generation returns a non-empty string.
        Validates Requirement 11.1
        """
        nonce = self.engine.generate_nonce()
        assert isinstance(nonce, str)
        assert len(nonce) > 0
    
    def test_generate_nonce_is_unique(self):
        """
        Test that nonce generation produces unique values.
        Validates Requirement 11.1
        """
        nonces = [self.engine.generate_nonce() for _ in range(100)]
        # All nonces should be unique
        assert len(nonces) == len(set(nonces))
    
    def test_generate_nonce_is_cryptographically_secure(self):
        """
        Test that nonce is 32 hex characters (16 bytes).
        Validates Requirement 11.1
        """
        nonce = self.engine.generate_nonce()
        # Should be 32 hex characters (16 bytes * 2 chars per byte)
        assert len(nonce) == 32
        # Should only contain hex characters
        assert all(c in '0123456789abcdef' for c in nonce)
    
    def test_generate_challenge_sequence_returns_correct_structure(self):
        """
        Test that challenge sequence has correct structure.
        Validates Requirements 2.1, 2.5
        """
        session_id = "test_session_123"
        sequence = self.engine.generate_challenge_sequence(session_id)
        
        assert sequence.session_id == session_id
        assert isinstance(sequence.nonce, str)
        assert len(sequence.nonce) > 0
        assert isinstance(sequence.timestamp, float)
        assert sequence.timestamp > 0
        assert isinstance(sequence.challenges, list)
    
    def test_generate_challenge_sequence_default_count(self):
        """
        Test that default challenge count is 3.
        Validates Requirement 2.1
        """
        sequence = self.engine.generate_challenge_sequence("test_session")
        assert len(sequence.challenges) == 3
    
    def test_generate_challenge_sequence_custom_count(self):
        """
        Test that custom challenge count is respected.
        Validates Requirement 2.1
        """
        sequence = self.engine.generate_challenge_sequence("test_session", num_challenges=5)
        assert len(sequence.challenges) == 5
    
    def test_challenge_has_required_fields(self):
        """
        Test that each challenge has all required fields.
        Validates Requirement 2.1
        """
        sequence = self.engine.generate_challenge_sequence("test_session")
        
        for challenge in sequence.challenges:
            assert hasattr(challenge, 'challenge_id')
            assert hasattr(challenge, 'type')
            assert hasattr(challenge, 'instruction')
            assert hasattr(challenge, 'timeout_seconds')
            
            assert isinstance(challenge.challenge_id, str)
            assert isinstance(challenge.type, ChallengeType)
            assert isinstance(challenge.instruction, str)
            assert challenge.timeout_seconds == 10
    
    def test_challenge_types_are_valid(self):
        """
        Test that challenges use valid types (GESTURE or EXPRESSION).
        Validates Requirements 2.2, 2.3
        """
        sequence = self.engine.generate_challenge_sequence("test_session", num_challenges=20)
        
        for challenge in sequence.challenges:
            assert challenge.type in [ChallengeType.GESTURE, ChallengeType.EXPRESSION]
    
    def test_gesture_challenges_have_instructions(self):
        """
        Test that gesture challenges have human-readable instructions.
        Validates Requirement 2.2
        """
        # Generate many sequences to get gesture challenges
        for _ in range(10):
            sequence = self.engine.generate_challenge_sequence("test_session", num_challenges=10)
            for challenge in sequence.challenges:
                if challenge.type == ChallengeType.GESTURE:
                    assert len(challenge.instruction) > 0
                    # Instruction should be in the instruction map
                    assert challenge.instruction in self.engine.GESTURE_INSTRUCTIONS.values()
    
    def test_expression_challenges_have_instructions(self):
        """
        Test that expression challenges have human-readable instructions.
        Validates Requirement 2.3
        """
        # Generate many sequences to get expression challenges
        for _ in range(10):
            sequence = self.engine.generate_challenge_sequence("test_session", num_challenges=10)
            for challenge in sequence.challenges:
                if challenge.type == ChallengeType.EXPRESSION:
                    assert len(challenge.instruction) > 0
                    # Instruction should be in the instruction map
                    assert challenge.instruction in self.engine.EXPRESSION_INSTRUCTIONS.values()
    
    def test_challenge_ids_are_unique_within_sequence(self):
        """
        Test that challenge IDs are unique within a sequence.
        Validates Requirement 2.1
        """
        sequence = self.engine.generate_challenge_sequence("test_session", num_challenges=10)
        challenge_ids = [c.challenge_id for c in sequence.challenges]
        assert len(challenge_ids) == len(set(challenge_ids))
    
    def test_challenge_ids_contain_session_id(self):
        """
        Test that challenge IDs contain the session ID.
        Validates Requirement 2.1
        """
        session_id = "test_session_456"
        sequence = self.engine.generate_challenge_sequence(session_id)
        
        for challenge in sequence.challenges:
            assert session_id in challenge.challenge_id
    
    def test_sequences_have_different_nonces(self):
        """
        Test that different sequences have different nonces.
        Validates Requirement 11.1
        """
        sequences = [
            self.engine.generate_challenge_sequence(f"session_{i}")
            for i in range(10)
        ]
        nonces = [seq.nonce for seq in sequences]
        # All nonces should be unique
        assert len(nonces) == len(set(nonces))
    
    def test_validate_nonce_with_valid_input(self):
        """
        Test nonce validation with valid inputs.
        Validates Requirement 11.2
        """
        nonce = self.engine.generate_nonce()
        session_id = "test_session"
        assert self.engine.validate_nonce(nonce, session_id) is True
    
    def test_validate_nonce_with_empty_nonce(self):
        """
        Test nonce validation rejects empty nonce.
        Validates Requirement 11.2
        """
        assert self.engine.validate_nonce("", "test_session") is False
    
    def test_validate_nonce_with_empty_session(self):
        """
        Test nonce validation rejects empty session ID.
        Validates Requirement 11.2
        """
        nonce = self.engine.generate_nonce()
        assert self.engine.validate_nonce(nonce, "") is False
    
    def test_all_gestures_have_instructions(self):
        """
        Test that all gestures in the pool have corresponding instructions.
        Validates Requirement 2.2
        """
        for gesture in self.engine.GESTURE_POOL:
            assert gesture in self.engine.GESTURE_INSTRUCTIONS
            assert len(self.engine.GESTURE_INSTRUCTIONS[gesture]) > 0
    
    def test_all_expressions_have_instructions(self):
        """
        Test that all expressions in the pool have corresponding instructions.
        Validates Requirement 2.3
        """
        for expression in self.engine.EXPRESSION_POOL:
            assert expression in self.engine.EXPRESSION_INSTRUCTIONS
            assert len(self.engine.EXPRESSION_INSTRUCTIONS[expression]) > 0


# Property-Based Tests
from hypothesis import given, strategies as st


class TestChallengeEngineProperties:
    """Property-based tests for ChallengeEngine"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.engine = ChallengeEngine()
    
    @given(
        session_id=st.text(min_size=1, max_size=50),
        num_challenges=st.integers(min_value=3, max_value=10)
    )
    def test_property_challenge_sequence_uniqueness(self, session_id, num_challenges):
        """
        Property 3: Challenge Sequence Uniqueness
        
        For any two consecutive verification sessions, the generated challenge 
        sequences should not be identical.
        
        **Validates: Requirements 2.4**
        
        Feature: proof-of-life-auth, Property 3: Challenge Sequence Uniqueness
        """
        # Generate two consecutive sequences
        sequence1 = self.engine.generate_challenge_sequence(session_id, num_challenges)
        sequence2 = self.engine.generate_challenge_sequence(session_id, num_challenges)
        
        # Sequences should have different nonces (ensures uniqueness)
        assert sequence1.nonce != sequence2.nonce
        
        # Extract challenge instructions from both sequences
        instructions1 = [c.instruction for c in sequence1.challenges]
        instructions2 = [c.instruction for c in sequence2.challenges]
        
        # Due to randomization, sequences should not be identical
        # (with high probability given the pool sizes)
        # We verify this by checking that at least one of:
        # 1. Nonces are different (always true)
        # 2. Timestamps are different (always true for non-simultaneous calls)
        # 3. Challenge sequences are different (highly probable)
        
        # Nonces must always be different
        assert sequence1.nonce != sequence2.nonce
        
        # Timestamps should be different (even if slightly)
        assert sequence1.timestamp != sequence2.timestamp or instructions1 != instructions2
    
    @given(
        session_id=st.text(min_size=1, max_size=50),
        num_challenges=st.integers(min_value=3, max_value=10)
    )
    def test_property_challenge_timestamp_presence(self, session_id, num_challenges):
        """
        Property 4: Challenge Timestamp Presence
        
        For any generated challenge sequence, it should contain a timestamp 
        and cryptographic nonce.
        
        **Validates: Requirements 2.5, 11.1**
        
        Feature: proof-of-life-auth, Property 4: Challenge Timestamp Presence
        """
        sequence = self.engine.generate_challenge_sequence(session_id, num_challenges)
        
        # Sequence must have a timestamp
        assert hasattr(sequence, 'timestamp')
        assert isinstance(sequence.timestamp, float)
        assert sequence.timestamp > 0
        
        # Sequence must have a nonce
        assert hasattr(sequence, 'nonce')
        assert isinstance(sequence.nonce, str)
        assert len(sequence.nonce) > 0
        
        # Nonce should be cryptographically secure (32 hex characters)
        assert len(sequence.nonce) == 32
        assert all(c in '0123456789abcdef' for c in sequence.nonce)
        
        # Timestamp should be reasonable (not in the future, not too old)
        import time
        current_time = time.time()
        # Allow small time difference for test execution
        assert sequence.timestamp <= current_time + 1
        # Timestamp should be recent (within last minute)
        assert sequence.timestamp >= current_time - 60
