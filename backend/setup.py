"""
Setup script for backend development environment
"""
import os
import subprocess
import sys


def create_directories():
    """Create necessary directories"""
    directories = [
        'data',
        'keys',
        'models',
        'logs'
    ]
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"✓ Created directory: {directory}")


def generate_jwt_keys():
    """Generate RSA key pair for JWT signing"""
    if os.path.exists('keys/private_key.pem') and os.path.exists('keys/public_key.pem'):
        print("✓ JWT keys already exist")
        return
    
    try:
        # Generate private key
        subprocess.run([
            'openssl', 'genrsa',
            '-out', 'keys/private_key.pem',
            '2048'
        ], check=True, capture_output=True)
        
        # Generate public key
        subprocess.run([
            'openssl', 'rsa',
            '-in', 'keys/private_key.pem',
            '-pubout',
            '-out', 'keys/public_key.pem'
        ], check=True, capture_output=True)
        
        print("✓ Generated JWT keys")
    except subprocess.CalledProcessError as e:
        print(f"✗ Failed to generate JWT keys: {e}")
        print("  Please install OpenSSL or generate keys manually")
    except FileNotFoundError:
        print("✗ OpenSSL not found")
        print("  Please install OpenSSL or generate keys manually")


def initialize_database():
    """Initialize SQLite database with schema"""
    if os.path.exists('data/pol_auth.db'):
        print("✓ Database already exists")
        return
    
    try:
        import sqlite3
        conn = sqlite3.connect('data/pol_auth.db')
        with open('schema.sql', 'r') as f:
            conn.executescript(f.read())
        conn.close()
        print("✓ Initialized database")
    except Exception as e:
        print(f"✗ Failed to initialize database: {e}")


def create_env_file():
    """Create .env file from example if it doesn't exist"""
    if os.path.exists('.env'):
        print("✓ .env file already exists")
        return
    
    if os.path.exists('.env.example'):
        import shutil
        shutil.copy('.env.example', '.env')
        print("✓ Created .env file from .env.example")
        print("  Please edit .env with your configuration")
    else:
        print("✗ .env.example not found")


def main():
    """Run all setup steps"""
    print("Setting up Proof of Life Authentication Backend...\n")
    
    create_directories()
    generate_jwt_keys()
    initialize_database()
    create_env_file()
    
    print("\n✓ Setup complete!")
    print("\nNext steps:")
    print("1. Edit .env with your configuration")
    print("2. Install dependencies: pip install -r requirements.txt")
    print("3. Run the server: uvicorn app.main:app --reload")


if __name__ == '__main__':
    main()
