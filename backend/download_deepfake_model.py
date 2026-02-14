#!/usr/bin/env python3
"""
Download pre-trained MesoNet-4 weights for deepfake detection.

This script downloads pre-trained weights for the MesoNet-4 model,
which is a lightweight CNN designed for deepfake detection.

Usage:
    python download_deepfake_model.py
"""

import os
import urllib.request
import hashlib
from pathlib import Path

# Model information
MODEL_NAME = "mesonet4_weights.h5"
MODEL_URL = "https://github.com/DariusAf/MesoNet/raw/master/weights/Meso4_DF.h5"
MODEL_MD5 = None  # Add checksum if available

# Download location
MODELS_DIR = Path.home() / ".deepfake_models"
MODEL_PATH = MODELS_DIR / MODEL_NAME


def download_model():
    """Download pre-trained MesoNet-4 weights."""
    
    # Create models directory
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    
    # Check if already downloaded
    if MODEL_PATH.exists():
        print(f"✓ Model already exists at {MODEL_PATH}")
        return
    
    print(f"Downloading MesoNet-4 weights from {MODEL_URL}...")
    print(f"Saving to {MODEL_PATH}")
    
    try:
        # Download with progress
        def report_progress(block_num, block_size, total_size):
            downloaded = block_num * block_size
            percent = min(100, downloaded * 100 / total_size)
            print(f"\rProgress: {percent:.1f}%", end="")
        
        urllib.request.urlretrieve(MODEL_URL, MODEL_PATH, reporthook=report_progress)
        print("\n✓ Download complete!")
        
        # Verify file size
        file_size = MODEL_PATH.stat().st_size
        print(f"✓ Model size: {file_size / 1024 / 1024:.2f} MB")
        
        # Verify checksum if available
        if MODEL_MD5:
            print("Verifying checksum...")
            with open(MODEL_PATH, 'rb') as f:
                file_hash = hashlib.md5(f.read()).hexdigest()
            
            if file_hash == MODEL_MD5:
                print("✓ Checksum verified")
            else:
                print(f"✗ Checksum mismatch! Expected {MODEL_MD5}, got {file_hash}")
                MODEL_PATH.unlink()
                return False
        
        print(f"\n✓ MesoNet-4 weights ready at {MODEL_PATH}")
        return True
        
    except Exception as e:
        print(f"\n✗ Download failed: {e}")
        if MODEL_PATH.exists():
            MODEL_PATH.unlink()
        return False


def verify_tensorflow():
    """Verify TensorFlow installation."""
    try:
        import tensorflow as tf
        print(f"✓ TensorFlow {tf.__version__} installed")
        return True
    except ImportError:
        print("✗ TensorFlow not installed")
        print("  Install with: pip install tensorflow")
        return False


def main():
    """Main function."""
    print("=" * 60)
    print("MesoNet-4 Deepfake Detection Model Downloader")
    print("=" * 60)
    print()
    
    # Check TensorFlow
    if not verify_tensorflow():
        print("\nPlease install TensorFlow first:")
        print("  pip install tensorflow")
        return
    
    print()
    
    # Download model
    if download_model():
        print("\n" + "=" * 60)
        print("Setup Complete!")
        print("=" * 60)
        print("\nThe deepfake detector will now use MesoNet-4 for detection.")
        print("No configuration needed - it will load automatically.")
    else:
        print("\n" + "=" * 60)
        print("Setup Failed")
        print("=" * 60)
        print("\nThe deepfake detector will fall back to CV techniques.")


if __name__ == "__main__":
    main()
