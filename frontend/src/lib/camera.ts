/**
 * Camera Capture Module
 * 
 * Handles video capture from user's camera for biometric verification.
 * Captures frames at a specified rate and encodes them as base64 JPEG.
 */

export class CameraCapture {
  private stream: MediaStream | null = null;
  private videoElement: HTMLVideoElement | null = null;
  private canvasElement: HTMLCanvasElement | null = null;
  private canvasContext: CanvasRenderingContext2D | null = null;
  private captureInterval: NodeJS.Timeout | null = null;
  private frameRate: number = 30; // Default 30 FPS

  /**
   * Request camera permissions and start video stream
   */
  async start(): Promise<void> {
    try {
      // Request camera access
      this.stream = await navigator.mediaDevices.getUserMedia({
        video: {
          width: { ideal: 1280 },
          height: { ideal: 720 },
          facingMode: 'user'
        },
        audio: false
      });

      // Create hidden video element
      this.videoElement = document.createElement('video');
      this.videoElement.style.display = 'none';
      this.videoElement.srcObject = this.stream;
      this.videoElement.autoplay = true;
      this.videoElement.playsInline = true;
      document.body.appendChild(this.videoElement);

      // Wait for video to be ready
      await new Promise<void>((resolve) => {
        if (this.videoElement) {
          this.videoElement.onloadedmetadata = () => resolve();
        }
      });

      // Create hidden canvas for frame capture
      this.canvasElement = document.createElement('canvas');
      this.canvasElement.style.display = 'none';
      this.canvasElement.width = this.videoElement.videoWidth;
      this.canvasElement.height = this.videoElement.videoHeight;
      this.canvasContext = this.canvasElement.getContext('2d');
      document.body.appendChild(this.canvasElement);

    } catch (error) {
      this.cleanup();
      throw error;
    }
  }

  /**
   * Stop capture and release camera resources
   */
  stop(): void {
    // Stop frame capture interval
    if (this.captureInterval) {
      clearInterval(this.captureInterval);
      this.captureInterval = null;
    }

    this.cleanup();
  }

  /**
   * Capture current frame as base64-encoded JPEG
   */
  captureFrame(): string {
    if (!this.videoElement || !this.canvasElement || !this.canvasContext) {
      throw new Error('Camera not started');
    }

    // Draw current video frame to canvas
    this.canvasContext.drawImage(
      this.videoElement,
      0,
      0,
      this.canvasElement.width,
      this.canvasElement.height
    );

    // Convert canvas to base64 JPEG with 0.8 quality
    return this.canvasElement.toDataURL('image/jpeg', 0.8);
  }

  /**
   * Set frame capture rate in frames per second
   */
  setFrameRate(fps: number): void {
    if (fps <= 0) {
      throw new Error('Frame rate must be positive');
    }
    this.frameRate = fps;
  }

  /**
   * Get current frame rate
   */
  getFrameRate(): number {
    return this.frameRate;
  }

  /**
   * Check if camera is currently active
   */
  isActive(): boolean {
    return this.stream !== null && this.stream.active;
  }

  /**
   * Clean up all resources
   */
  private cleanup(): void {
    // Stop all media stream tracks
    if (this.stream) {
      this.stream.getTracks().forEach(track => track.stop());
      this.stream = null;
    }

    // Remove video element
    if (this.videoElement) {
      if (this.videoElement.parentNode) {
        this.videoElement.parentNode.removeChild(this.videoElement);
      }
      this.videoElement.srcObject = null;
      this.videoElement = null;
    }

    // Remove canvas element
    if (this.canvasElement) {
      if (this.canvasElement.parentNode) {
        this.canvasElement.parentNode.removeChild(this.canvasElement);
      }
      this.canvasElement = null;
    }

    this.canvasContext = null;
  }
}
