#!/usr/bin/env python3
"""
Download MediaPipe Face Landmarker model.

This script downloads the pre-trained MediaPipe Face Landmarker model
which is required for liveness detection.
"""

import os
import urllib.request
from pathlib import Path

# Model information
MODEL_NAME = "face_landmarker.task"
MODEL_URL = "https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/latest/face_landmarker.task"

# Download location
MODELS_DIR = Path.home() / ".mediapipe_models"
MODEL_PATH = MODELS_DIR / MODEL_NAME


def download_model():
    """Download MediaPipe Face Landmarker model."""
    
    # Create models directory
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    
    # Check if already downloaded
    if MODEL_PATH.exists():
        print(f"✓ Model already exists at {MODEL_PATH}")
        file_size = MODEL_PATH.stat().st_size
        print(f"✓ Model size: {file_size / 1024 / 1024:.2f} MB")
        return True
    
    print(f"Downloading MediaPipe Face Landmarker from {MODEL_URL}...")
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
        
        print(f"\n✓ MediaPipe Face Landmarker ready at {MODEL_PATH}")
        return True
        
    except Exception as e:
        print(f"\n✗ Download failed: {e}")
        if MODEL_PATH.exists():
            MODEL_PATH.unlink()
        return False


def main():
    """Main function."""
    print("=" * 60)
    print("MediaPipe Face Landmarker Model Downloader")
    print("=" * 60)
    print()
    
    # Download model
    if download_model():
        print("\n" + "=" * 60)
        print("Setup Complete!")
        print("=" * 60)
        print("\nThe CVVerifier will now use MediaPipe Face Landmarker.")
        print(f"\nModel location: {MODEL_PATH}")
        print("\nTo use in your code:")
        print(f"  cv_verifier = CVVerifier(model_path='{MODEL_PATH}')")
        print("\nOr set environment variable:")
        print(f"  MEDIAPIPE_MODEL_PATH={MODEL_PATH}")
    else:
        print("\n" + "=" * 60)
        print("Setup Failed")
        print("=" * 60)
        print("\nPlease check your internet connection and try again.")


if __name__ == "__main__":
    main()
