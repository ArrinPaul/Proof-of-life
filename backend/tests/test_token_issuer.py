"""
Unit tests for TokenIssuer
"""
import pytest
import time
import jwt
from app.services.token_issuer import TokenIssuer


class TestTokenIssuer:
    """Test suite for TokenIssuer class"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.issuer = TokenIssuer()
    
    def test_key_pair_generation(self):
        """Test that RSA key pair is generated on initialization"""
        assert self.issuer.private_key is not None
        assert self.issuer.public_key is not None
        assert "BEGIN PRIVATE KEY" in self.issuer.private_key
        assert "BEGIN PUBLIC KEY" in self.issuer.public_key
    
    def test_issue_jwt_token_basic(self):
        """Test basic JWT token generation"""
        user_id = "user123"
        session_id = "session456"
        final_score = 0.85
        
        token = self.issuer.issue_jwt_token(user_id, session_id, final_score)
        
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 0
    
    def test_jwt_contains_required_claims(self):
        """Test that JWT contains all required claims"""
        user_id = "user123"
        session_id = "session456"
        final_score = 0.85
        
        token = self.issuer.issue_jwt_token(user_id, session_id, final_score)
        
        # Decode without verification to inspect claims
        decoded = jwt.decode(token, options={"verify_signature": False})
        
        assert decoded["sub"] == user_id
        assert decoded["session_id"] == session_id
        assert decoded["final_score"] == final_score
        assert "iat" in decoded
        assert "exp" in decoded
        assert decoded["iss"] == "proof-of-life-auth"
    
    def test_jwt_expiration_exactly_15_minutes(self):
        """
        Test that JWT expiration is set to exactly 15 minutes from issuance
        
        **Validates: Requirements 8.2**
        """
        user_id = "user123"
        session_id = "session456"
        final_score = 0.85
        
        before_issue = time.time()
        token = self.issuer.issue_jwt_token(user_id, session_id, final_score)
        after_issue = time.time()
        
        decoded = jwt.decode(token, options={"verify_signature": False})
        
        issued_at = decoded["iat"]
        expires_at = decoded["exp"]
        
        # Verify expiration is exactly 15 minutes (900 seconds) from issuance
        expiry_duration = expires_at - issued_at
        assert expiry_duration == 15 * 60, (
            f"Token expiration should be exactly 15 minutes (900 seconds), "
            f"but got {expiry_duration} seconds"
        )
        
        # Verify issued_at is within the time window
        assert before_issue <= issued_at <= after_issue
    
    def test_jwt_signature_is_valid(self):
        """
        Test that JWT is signed with private key and verifiable with public key
        
        **Validates: Requirements 8.3**
        """
        user_id = "user123"
        session_id = "session456"
        final_score = 0.85
        
        token = self.issuer.issue_jwt_token(user_id, session_id, final_score)
        
        # Should not raise exception if signature is valid
        decoded = jwt.decode(
            token,
            self.issuer.public_key,
            algorithms=["RS256"],
            issuer="proof-of-life-auth"
        )
        
        assert decoded["sub"] == user_id
    
    def test_validate_token_success(self):
        """Test successful token validation"""
        user_id = "user123"
        session_id = "session456"
        final_score = 0.85
        
        token = self.issuer.issue_jwt_token(user_id, session_id, final_score)
        validation = self.issuer.validate_token(token)
        
        assert validation.valid is True
        assert validation.user_id == user_id
        assert validation.session_id == session_id
        assert validation.issued_at is not None
        assert validation.expires_at is not None
        assert validation.error is None
    
    def test_validate_token_expired(self):
        """
        Test that expired tokens are rejected
        
        **Validates: Requirements 14.2, 14.3**
        """
        user_id = "user123"
        session_id = "session456"
        final_score = 0.85
        
        # Create a token that's already expired
        past_time = time.time() - 1000  # 1000 seconds ago
        expired_payload = {
            "sub": user_id,
            "session_id": session_id,
            "final_score": final_score,
            "iat": past_time - 900,  # Issued 900 seconds before expiry
            "exp": past_time,  # Already expired
            "iss": "proof-of-life-auth"
        }
        
        expired_token = jwt.encode(
            expired_payload,
            self.issuer.private_key,
            algorithm="RS256"
        )
        
        validation = self.issuer.validate_token(expired_token)
        
        assert validation.valid is False
        assert validation.error == "Token has expired"
        assert validation.user_id is None
        assert validation.session_id is None
    
    def test_validate_token_invalid_signature(self):
        """
        Test that tokens with invalid signatures are rejected
        
        **Validates: Requirements 14.1, 14.4**
        """
        user_id = "user123"
        session_id = "session456"
        final_score = 0.85
        
        # Create a token signed with a different key
        different_issuer = TokenIssuer()
        token = different_issuer.issue_jwt_token(user_id, session_id, final_score)
        
        # Try to validate with original issuer's public key
        validation = self.issuer.validate_token(token)
        
        assert validation.valid is False
        assert "Invalid token signature" in validation.error
        assert validation.user_id is None
        assert validation.session_id is None
    
    def test_validate_token_tampered_payload(self):
        """
        Test that tokens with tampered payloads are rejected
        
        **Validates: Requirements 14.4**
        """
        user_id = "user123"
        session_id = "session456"
        final_score = 0.85
        
        token = self.issuer.issue_jwt_token(user_id, session_id, final_score)
        
        # Tamper with the token by modifying the payload
        parts = token.split('.')
        if len(parts) == 3:
            # Modify the payload (middle part)
            import base64
            payload = parts[1]
            # Add some padding if needed
            padding = 4 - len(payload) % 4
            if padding != 4:
                payload += '=' * padding
            
            decoded_payload = base64.urlsafe_b64decode(payload)
            # Change a byte
            tampered_payload = decoded_payload[:-1] + b'X'
            tampered_b64 = base64.urlsafe_b64encode(tampered_payload).decode('utf-8').rstrip('=')
            
            tampered_token = f"{parts[0]}.{tampered_b64}.{parts[2]}"
            
            validation = self.issuer.validate_token(tampered_token)
            
            assert validation.valid is False
            assert validation.error is not None
    
    def test_validate_token_malformed(self):
        """Test that malformed tokens are rejected"""
        malformed_tokens = [
            "not.a.token",
            "invalid",
            "",
            "a.b",  # Missing part
            "a.b.c.d"  # Too many parts
        ]
        
        for token in malformed_tokens:
            validation = self.issuer.validate_token(token)
            assert validation.valid is False
            assert validation.error is not None
    
    def test_token_with_different_scores(self):
        """Test token generation with various final scores"""
        test_scores = [0.70, 0.75, 0.85, 0.95, 1.0]
        
        for score in test_scores:
            token = self.issuer.issue_jwt_token("user", "session", score)
            decoded = jwt.decode(token, options={"verify_signature": False})
            assert decoded["final_score"] == score
    
    def test_token_with_special_characters_in_ids(self):
        """Test token generation with special characters in user/session IDs"""
        user_id = "user@example.com"
        session_id = "session-123-abc-xyz"
        final_score = 0.85
        
        token = self.issuer.issue_jwt_token(user_id, session_id, final_score)
        validation = self.issuer.validate_token(token)
        
        assert validation.valid is True
        assert validation.user_id == user_id
        assert validation.session_id == session_id
    
    def test_multiple_tokens_are_unique(self):
        """Test that multiple tokens generated for same user are unique"""
        user_id = "user123"
        session_id = "session456"
        final_score = 0.85
        
        token1 = self.issuer.issue_jwt_token(user_id, session_id, final_score)
        time.sleep(0.01)  # Small delay to ensure different timestamps
        token2 = self.issuer.issue_jwt_token(user_id, session_id, final_score)
        
        assert token1 != token2
    
    def test_token_issuer_with_provided_keys(self):
        """Test TokenIssuer initialization with provided key pair"""
        # Generate a key pair
        issuer1 = TokenIssuer()
        private_key = issuer1.private_key
        public_key = issuer1.public_key
        
        # Create new issuer with same keys
        issuer2 = TokenIssuer(private_key=private_key, public_key=public_key)
        
        # Token issued by issuer1 should be valid for issuer2
        token = issuer1.issue_jwt_token("user", "session", 0.85)
        validation = issuer2.validate_token(token)
        
        assert validation.valid is True


# Property-Based Tests
from hypothesis import given, strategies as st, settings


class TestTokenIssuerProperties:
    """Property-based tests for TokenIssuer"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.issuer = TokenIssuer()
    
    @given(
        user_id=st.text(min_size=1, max_size=100),
        session_id=st.text(min_size=1, max_size=100),
        final_score=st.floats(min_value=0.7, max_value=1.0, allow_nan=False, allow_infinity=False)
    )
    def test_property_13_jwt_structure_validity(self, user_id, session_id, final_score):
        """
        Property 13: JWT Structure Validity
        
        **Validates: Requirements 8.1, 8.2, 8.3, 8.4**
        
        For any successful verification, the issued JWT should contain:
        - User identity (sub claim)
        - Session identifier (session_id claim)
        - Verification timestamp (iat claim)
        - Expiration time set to exactly 15 minutes from issuance
        - Valid signature
        """
        # Issue token
        token = self.issuer.issue_jwt_token(user_id, session_id, final_score)
        
        # Verify token is a non-empty string
        assert isinstance(token, str)
        assert len(token) > 0
        
        # Decode and verify signature
        try:
            decoded = jwt.decode(
                token,
                self.issuer.public_key,
                algorithms=["RS256"],
                issuer="proof-of-life-auth"
            )
        except jwt.InvalidTokenError as e:
            pytest.fail(f"Token validation failed: {e}")
        
        # Verify required claims are present
        assert "sub" in decoded, "Token missing 'sub' (user_id) claim"
        assert "session_id" in decoded, "Token missing 'session_id' claim"
        assert "iat" in decoded, "Token missing 'iat' (issued at) claim"
        assert "exp" in decoded, "Token missing 'exp' (expiration) claim"
        assert "iss" in decoded, "Token missing 'iss' (issuer) claim"
        assert "final_score" in decoded, "Token missing 'final_score' claim"
        
        # Verify claim values
        assert decoded["sub"] == user_id, (
            f"User ID mismatch: expected {user_id}, got {decoded['sub']}"
        )
        assert decoded["session_id"] == session_id, (
            f"Session ID mismatch: expected {session_id}, got {decoded['session_id']}"
        )
        assert decoded["final_score"] == final_score, (
            f"Final score mismatch: expected {final_score}, got {decoded['final_score']}"
        )
        assert decoded["iss"] == "proof-of-life-auth"
        
        # Verify expiration is exactly 15 minutes from issuance
        issued_at = decoded["iat"]
        expires_at = decoded["exp"]
        expiry_duration = expires_at - issued_at
        
        assert expiry_duration == 15 * 60, (
            f"Token expiration should be exactly 15 minutes (900 seconds), "
            f"but got {expiry_duration} seconds for user_id={user_id}, "
            f"session_id={session_id}, final_score={final_score}"
        )
        
        # Verify token can be validated successfully
        validation = self.issuer.validate_token(token)
        assert validation.valid is True, (
            f"Token validation failed: {validation.error}"
        )
        assert validation.user_id == user_id
        assert validation.session_id == session_id
        assert validation.issued_at == issued_at
        assert validation.expires_at == expires_at
        assert validation.error is None
    
    @settings(deadline=500)  # Increase deadline due to RSA key generation
    @given(
        user_id=st.text(min_size=1, max_size=100),
        session_id=st.text(min_size=1, max_size=100),
        final_score=st.floats(min_value=0.7, max_value=1.0, allow_nan=False, allow_infinity=False)
    )
    def test_property_21_jwt_signature_verification(self, user_id, session_id, final_score):
        """
        Property 21: JWT Signature Verification
        
        **Validates: Requirements 14.1, 14.2**
        
        For any presented token during validation, the system should:
        - Verify the JWT signature using the public key
        - Check the expiration timestamp
        - Return validation result with appropriate status
        """
        # Issue a valid token
        token = self.issuer.issue_jwt_token(user_id, session_id, final_score)
        
        # Validate the token
        validation = self.issuer.validate_token(token)
        
        # Verify validation succeeds for valid token
        assert validation.valid is True, (
            f"Valid token should pass validation, but got error: {validation.error}"
        )
        
        # Verify signature is checked (by using wrong public key)
        different_issuer = TokenIssuer()
        wrong_validation = different_issuer.validate_token(token)
        
        assert wrong_validation.valid is False, (
            "Token with wrong signature should fail validation"
        )
        assert "signature" in wrong_validation.error.lower(), (
            f"Error should mention signature, got: {wrong_validation.error}"
        )
        
        # Verify expiration is checked (by creating expired token)
        past_time = time.time() - 1000
        expired_payload = {
            "sub": user_id,
            "session_id": session_id,
            "final_score": final_score,
            "iat": past_time - 900,
            "exp": past_time,
            "iss": "proof-of-life-auth"
        }
        
        expired_token = jwt.encode(
            expired_payload,
            self.issuer.private_key,
            algorithm="RS256"
        )
        
        expired_validation = self.issuer.validate_token(expired_token)
        
        assert expired_validation.valid is False, (
            "Expired token should fail validation"
        )
        assert "expired" in expired_validation.error.lower(), (
            f"Error should mention expiration, got: {expired_validation.error}"
        )
