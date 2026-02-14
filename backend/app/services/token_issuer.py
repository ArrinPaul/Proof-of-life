"""
Token Issuer Service

Generates and validates time-bound JWT authentication tokens for successful
proof-of-life verifications.
"""
import os
import time
import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.backends import default_backend
from typing import Optional

from app.models.data_models import TokenValidation


class TokenIssuer:
    """
    Generates and validates JWT tokens for authenticated sessions.
    
    Tokens are signed with RSA private key and expire after exactly 15 minutes.
    """
    
    TOKEN_EXPIRY_MINUTES = 15
    ISSUER = "proof-of-life-auth"
    ALGORITHM = "RS256"
    
    def __init__(self, private_key: Optional[str] = None, public_key: Optional[str] = None):
        """
        Initialize TokenIssuer with RSA key pair.
        
        Args:
            private_key: PEM-encoded RSA private key (or None to generate)
            public_key: PEM-encoded RSA public key (or None to generate)
        """
        if private_key and public_key:
            self.private_key = private_key
            self.public_key = public_key
        else:
            # Generate RSA key pair if not provided
            self._generate_key_pair()
    
    def _generate_key_pair(self) -> None:
        """Generate a new RSA key pair for signing tokens."""
        # Generate private key
        private_key_obj = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )
        
        # Serialize private key to PEM format
        self.private_key = private_key_obj.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ).decode('utf-8')
        
        # Extract and serialize public key
        public_key_obj = private_key_obj.public_key()
        self.public_key = public_key_obj.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode('utf-8')
    
    def issue_jwt_token(
        self,
        user_id: str,
        session_id: str,
        final_score: float
    ) -> str:
        """
        Generate a signed JWT token with verification metadata.
        
        Args:
            user_id: Authenticated user identifier
            session_id: Unique session identifier
            final_score: Final verification score (0.0-1.0)
        
        Returns:
            Signed JWT token string
        
        Requirements:
            - 8.1: Include user identity and verification timestamp
            - 8.2: Set expiration to exactly 15 minutes from issuance
            - 8.3: Sign with secure private key
            - 8.4: Include session identifier in payload
        """
        current_time = time.time()
        expiration_time = current_time + (self.TOKEN_EXPIRY_MINUTES * 60)
        
        payload = {
            "sub": user_id,
            "session_id": session_id,
            "final_score": final_score,
            "iat": current_time,
            "exp": expiration_time,
            "iss": self.ISSUER
        }
        
        token = jwt.encode(
            payload,
            self.private_key,
            algorithm=self.ALGORITHM
        )
        
        return token
    
    def validate_token(self, token: str) -> TokenValidation:
        """
        Verify JWT signature and expiration.
        
        Args:
            token: JWT token string to validate
        
        Returns:
            TokenValidation result with validation status and claims
        
        Requirements:
            - 14.1: Verify JWT signature using public key
            - 14.2: Check expiration timestamp
            - 14.3: Reject expired tokens
            - 14.4: Reject invalid signatures
        """
        try:
            # Decode and verify token
            payload = jwt.decode(
                token,
                self.public_key,
                algorithms=[self.ALGORITHM],
                issuer=self.ISSUER
            )
            
            # Extract claims
            user_id = payload.get("sub")
            session_id = payload.get("session_id")
            issued_at = payload.get("iat")
            expires_at = payload.get("exp")
            
            return TokenValidation(
                valid=True,
                user_id=user_id,
                session_id=session_id,
                issued_at=issued_at,
                expires_at=expires_at,
                error=None
            )
        
        except jwt.ExpiredSignatureError:
            return TokenValidation(
                valid=False,
                user_id=None,
                session_id=None,
                issued_at=None,
                expires_at=None,
                error="Token has expired"
            )
        
        except jwt.InvalidSignatureError:
            return TokenValidation(
                valid=False,
                user_id=None,
                session_id=None,
                issued_at=None,
                expires_at=None,
                error="Invalid token signature"
            )
        
        except jwt.InvalidTokenError as e:
            return TokenValidation(
                valid=False,
                user_id=None,
                session_id=None,
                issued_at=None,
                expires_at=None,
                error=f"Invalid token: {str(e)}"
            )
