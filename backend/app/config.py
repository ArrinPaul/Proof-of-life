"""
Configuration management for the application
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Application configuration"""
    
    # JWT Configuration
    JWT_PRIVATE_KEY_PATH = os.getenv('JWT_PRIVATE_KEY_PATH', 'keys/private_key.pem')
    JWT_PUBLIC_KEY_PATH = os.getenv('JWT_PUBLIC_KEY_PATH', 'keys/public_key.pem')
    JWT_ALGORITHM = os.getenv('JWT_ALGORITHM', 'RS256')
    JWT_EXPIRY_MINUTES = int(os.getenv('JWT_EXPIRY_MINUTES', '15'))
    
    # Database Configuration
    DATABASE_PATH = os.getenv('DATABASE_PATH', 'data/pol_auth.db')
    
    # Server Configuration
    HOST = os.getenv('HOST', '0.0.0.0')
    PORT = int(os.getenv('PORT', '8000'))
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', 'http://localhost:3000').split(',')
    
    # ML Model Configuration
    DEEPFAKE_MODEL_PATH = os.getenv('DEEPFAKE_MODEL_PATH', 'models/deepfake_detector.h5')
    ENABLE_DEEPFAKE_DETECTION = os.getenv('ENABLE_DEEPFAKE_DETECTION', 'false').lower() == 'true'
    
    # Session Configuration
    MAX_SESSION_DURATION_SECONDS = int(os.getenv('MAX_SESSION_DURATION_SECONDS', '120'))
    MAX_CONSECUTIVE_FAILURES = int(os.getenv('MAX_CONSECUTIVE_FAILURES', '3'))
    CHALLENGE_TIMEOUT_SECONDS = int(os.getenv('CHALLENGE_TIMEOUT_SECONDS', '10'))
    
    # Security Configuration
    NONCE_EXPIRY_HOURS = int(os.getenv('NONCE_EXPIRY_HOURS', '24'))
    
    @classmethod
    def load_jwt_keys(cls):
        """Load JWT keys from files"""
        try:
            with open(cls.JWT_PRIVATE_KEY_PATH, 'r') as f:
                private_key = f.read()
            with open(cls.JWT_PUBLIC_KEY_PATH, 'r') as f:
                public_key = f.read()
            return private_key, public_key
        except FileNotFoundError as e:
            raise RuntimeError(f"JWT keys not found: {e}. Run setup.py to generate keys.")


config = Config()
