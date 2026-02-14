/**
 * Unit Tests for Camera Error Handling
 * 
 * Tests specific error scenarios and edge cases for camera capture.
 * Validates Requirements 9.1 - Error Handling and Recovery
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { CameraCapture } from './camera';

describe('Camera Error Handling - Unit Tests', () => {
  let mockGetUserMedia: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    // Reset mocks before each test
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  /**
   * Test NotAllowedError (permission denied)
   * 
   * When the user denies camera permission, getUserMedia throws a NotAllowedError.
   * The camera module should propagate this error and clean up resources.
   * 
   * Requirements: 9.1
   */
  describe('NotAllowedError (permission denied)', () => {
    it('should throw NotAllowedError when user denies camera permission', async () => {
      // Create a DOMException with NotAllowedError
      const permissionError = new DOMException(
        'Permission denied',
        'NotAllowedError'
      );

      // Mock getUserMedia to reject with NotAllowedError
      mockGetUserMedia = vi.fn().mockRejectedValue(permissionError);
      Object.defineProperty(navigator, 'mediaDevices', {
        writable: true,
        configurable: true,
        value: {
          getUserMedia: mockGetUserMedia,
        },
      });

      const camera = new CameraCapture();

      // Attempt to start camera should throw NotAllowedError
      await expect(camera.start()).rejects.toThrow('Permission denied');
      
      // Verify getUserMedia was called
      expect(mockGetUserMedia).toHaveBeenCalledTimes(1);
      expect(mockGetUserMedia).toHaveBeenCalledWith({
        video: {
          width: { ideal: 1280 },
          height: { ideal: 720 },
          facingMode: 'user'
        },
        audio: false
      });

      // Verify camera is not active after error
      expect(camera.isActive()).toBe(false);
    });

    it('should clean up resources when NotAllowedError occurs', async () => {
      const permissionError = new DOMException(
        'Permission denied',
        'NotAllowedError'
      );

      mockGetUserMedia = vi.fn().mockRejectedValue(permissionError);
      Object.defineProperty(navigator, 'mediaDevices', {
        writable: true,
        configurable: true,
        value: {
          getUserMedia: mockGetUserMedia,
        },
      });

      const camera = new CameraCapture();

      try {
        await camera.start();
      } catch (error) {
        // Expected to throw
      }

      // Verify camera is properly cleaned up
      expect(camera.isActive()).toBe(false);
      
      // Attempting to capture frame should throw error
      expect(() => camera.captureFrame()).toThrow('Camera not started');
    });
  });

  /**
   * Test NotFoundError (no camera)
   * 
   * When no camera device is available, getUserMedia throws a NotFoundError.
   * The camera module should propagate this error and clean up resources.
   * 
   * Requirements: 9.1
   */
  describe('NotFoundError (no camera)', () => {
    it('should throw NotFoundError when no camera is available', async () => {
      // Create a DOMException with NotFoundError
      const notFoundError = new DOMException(
        'Requested device not found',
        'NotFoundError'
      );

      // Mock getUserMedia to reject with NotFoundError
      mockGetUserMedia = vi.fn().mockRejectedValue(notFoundError);
      Object.defineProperty(navigator, 'mediaDevices', {
        writable: true,
        configurable: true,
        value: {
          getUserMedia: mockGetUserMedia,
        },
      });

      const camera = new CameraCapture();

      // Attempt to start camera should throw NotFoundError
      await expect(camera.start()).rejects.toThrow('Requested device not found');
      
      // Verify getUserMedia was called
      expect(mockGetUserMedia).toHaveBeenCalledTimes(1);

      // Verify camera is not active after error
      expect(camera.isActive()).toBe(false);
    });

    it('should clean up resources when NotFoundError occurs', async () => {
      const notFoundError = new DOMException(
        'Requested device not found',
        'NotFoundError'
      );

      mockGetUserMedia = vi.fn().mockRejectedValue(notFoundError);
      Object.defineProperty(navigator, 'mediaDevices', {
        writable: true,
        configurable: true,
        value: {
          getUserMedia: mockGetUserMedia,
        },
      });

      const camera = new CameraCapture();

      try {
        await camera.start();
      } catch (error) {
        // Expected to throw
      }

      // Verify camera is properly cleaned up
      expect(camera.isActive()).toBe(false);
      
      // Attempting to capture frame should throw error
      expect(() => camera.captureFrame()).toThrow('Camera not started');
    });
  });

  /**
   * Test cleanup on stop
   * 
   * When stop() is called, all resources should be properly released:
   * - Media stream tracks should be stopped
   * - Video and canvas elements should be removed from DOM
   * - Camera should no longer be active
   * 
   * Requirements: 9.1, 15.2
   */
  describe('Cleanup on stop', () => {
    it('should stop all media stream tracks when stop() is called', async () => {
      // Mock MediaStream and track
      const mockVideoTrack = {
        stop: vi.fn(),
        kind: 'video',
        enabled: true,
        id: 'mock-track-id',
        label: 'mock camera',
        muted: false,
        readyState: 'live',
      } as unknown as MediaStreamTrack;

      const mockStream = {
        getTracks: vi.fn(() => [mockVideoTrack]),
        getVideoTracks: vi.fn(() => [mockVideoTrack]),
        active: true,
      } as unknown as MediaStream;

      mockGetUserMedia = vi.fn().mockResolvedValue(mockStream);
      Object.defineProperty(navigator, 'mediaDevices', {
        writable: true,
        configurable: true,
        value: {
          getUserMedia: mockGetUserMedia,
        },
      });

      // Mock document.createElement
      const mockVideoElement = document.createElement('video');
      const mockCanvasElement = document.createElement('canvas');
      const mockContext = {
        drawImage: vi.fn(),
      } as unknown as CanvasRenderingContext2D;

      Object.defineProperty(mockVideoElement, 'videoWidth', { value: 1280 });
      Object.defineProperty(mockVideoElement, 'videoHeight', { value: 720 });
      
      vi.spyOn(mockCanvasElement, 'getContext').mockReturnValue(mockContext);
      
      const createElementSpy = vi.spyOn(document, 'createElement');
      createElementSpy.mockImplementation((tagName: string) => {
        if (tagName === 'video') {
          setTimeout(() => {
            if (mockVideoElement.onloadedmetadata) {
              mockVideoElement.onloadedmetadata(new Event('loadedmetadata'));
            }
          }, 0);
          return mockVideoElement;
        }
        if (tagName === 'canvas') {
          return mockCanvasElement;
        }
        return document.createElement(tagName);
      });

      const camera = new CameraCapture();
      await camera.start();

      // Verify camera is active
      expect(camera.isActive()).toBe(true);

      // Stop camera
      camera.stop();

      // Verify track.stop() was called
      expect(mockVideoTrack.stop).toHaveBeenCalledTimes(1);

      // Verify camera is no longer active
      expect(camera.isActive()).toBe(false);
    });

    it('should remove video and canvas elements from DOM when stop() is called', async () => {
      // Mock MediaStream
      const mockVideoTrack = {
        stop: vi.fn(),
        kind: 'video',
        enabled: true,
        id: 'mock-track-id',
        label: 'mock camera',
        muted: false,
        readyState: 'live',
      } as unknown as MediaStreamTrack;

      const mockStream = {
        getTracks: vi.fn(() => [mockVideoTrack]),
        getVideoTracks: vi.fn(() => [mockVideoTrack]),
        active: true,
      } as unknown as MediaStream;

      mockGetUserMedia = vi.fn().mockResolvedValue(mockStream);
      Object.defineProperty(navigator, 'mediaDevices', {
        writable: true,
        configurable: true,
        value: {
          getUserMedia: mockGetUserMedia,
        },
      });

      // Create real elements that can be added to DOM
      const mockVideoElement = document.createElement('video');
      const mockCanvasElement = document.createElement('canvas');
      const mockContext = {
        drawImage: vi.fn(),
      } as unknown as CanvasRenderingContext2D;

      Object.defineProperty(mockVideoElement, 'videoWidth', { value: 1280 });
      Object.defineProperty(mockVideoElement, 'videoHeight', { value: 720 });
      
      vi.spyOn(mockCanvasElement, 'getContext').mockReturnValue(mockContext);
      
      const removeChildSpy = vi.spyOn(document.body, 'removeChild');
      
      const createElementSpy = vi.spyOn(document, 'createElement');
      createElementSpy.mockImplementation((tagName: string) => {
        if (tagName === 'video') {
          setTimeout(() => {
            if (mockVideoElement.onloadedmetadata) {
              mockVideoElement.onloadedmetadata(new Event('loadedmetadata'));
            }
          }, 0);
          return mockVideoElement;
        }
        if (tagName === 'canvas') {
          return mockCanvasElement;
        }
        return document.createElement(tagName);
      });

      const camera = new CameraCapture();
      await camera.start();

      // Stop camera
      camera.stop();

      // Verify removeChild was called for both video and canvas
      expect(removeChildSpy).toHaveBeenCalledWith(mockVideoElement);
      expect(removeChildSpy).toHaveBeenCalledWith(mockCanvasElement);
    });

    it('should handle stop() being called multiple times safely', async () => {
      // Mock MediaStream
      const mockVideoTrack = {
        stop: vi.fn(),
        kind: 'video',
        enabled: true,
        id: 'mock-track-id',
        label: 'mock camera',
        muted: false,
        readyState: 'live',
      } as unknown as MediaStreamTrack;

      const mockStream = {
        getTracks: vi.fn(() => [mockVideoTrack]),
        getVideoTracks: vi.fn(() => [mockVideoTrack]),
        active: true,
      } as unknown as MediaStream;

      mockGetUserMedia = vi.fn().mockResolvedValue(mockStream);
      Object.defineProperty(navigator, 'mediaDevices', {
        writable: true,
        configurable: true,
        value: {
          getUserMedia: mockGetUserMedia,
        },
      });

      // Mock document.createElement
      const mockVideoElement = document.createElement('video');
      const mockCanvasElement = document.createElement('canvas');
      const mockContext = {
        drawImage: vi.fn(),
      } as unknown as CanvasRenderingContext2D;

      Object.defineProperty(mockVideoElement, 'videoWidth', { value: 1280 });
      Object.defineProperty(mockVideoElement, 'videoHeight', { value: 720 });
      
      vi.spyOn(mockCanvasElement, 'getContext').mockReturnValue(mockContext);
      
      const createElementSpy = vi.spyOn(document, 'createElement');
      createElementSpy.mockImplementation((tagName: string) => {
        if (tagName === 'video') {
          setTimeout(() => {
            if (mockVideoElement.onloadedmetadata) {
              mockVideoElement.onloadedmetadata(new Event('loadedmetadata'));
            }
          }, 0);
          return mockVideoElement;
        }
        if (tagName === 'canvas') {
          return mockCanvasElement;
        }
        return document.createElement(tagName);
      });

      const camera = new CameraCapture();
      await camera.start();

      // Call stop multiple times
      camera.stop();
      camera.stop();
      camera.stop();

      // Should not throw errors and track.stop should only be called once
      expect(mockVideoTrack.stop).toHaveBeenCalledTimes(1);
      expect(camera.isActive()).toBe(false);
    });

    it('should handle stop() being called before start() safely', () => {
      const camera = new CameraCapture();

      // Call stop before start - should not throw
      expect(() => camera.stop()).not.toThrow();
      
      // Camera should not be active
      expect(camera.isActive()).toBe(false);
    });

    it('should prevent frame capture after stop() is called', async () => {
      // Mock MediaStream
      const mockVideoTrack = {
        stop: vi.fn(),
        kind: 'video',
        enabled: true,
        id: 'mock-track-id',
        label: 'mock camera',
        muted: false,
        readyState: 'live',
      } as unknown as MediaStreamTrack;

      const mockStream = {
        getTracks: vi.fn(() => [mockVideoTrack]),
        getVideoTracks: vi.fn(() => [mockVideoTrack]),
        active: true,
      } as unknown as MediaStream;

      mockGetUserMedia = vi.fn().mockResolvedValue(mockStream);
      Object.defineProperty(navigator, 'mediaDevices', {
        writable: true,
        configurable: true,
        value: {
          getUserMedia: mockGetUserMedia,
        },
      });

      // Mock document.createElement
      const mockVideoElement = document.createElement('video');
      const mockCanvasElement = document.createElement('canvas');
      const mockContext = {
        drawImage: vi.fn(),
      } as unknown as CanvasRenderingContext2D;

      Object.defineProperty(mockVideoElement, 'videoWidth', { value: 1280 });
      Object.defineProperty(mockVideoElement, 'videoHeight', { value: 720 });
      
      vi.spyOn(mockCanvasElement, 'getContext').mockReturnValue(mockContext);
      vi.spyOn(mockCanvasElement, 'toDataURL').mockReturnValue('data:image/jpeg;base64,/9j/4AAQSkZJRg==');
      
      const createElementSpy = vi.spyOn(document, 'createElement');
      createElementSpy.mockImplementation((tagName: string) => {
        if (tagName === 'video') {
          setTimeout(() => {
            if (mockVideoElement.onloadedmetadata) {
              mockVideoElement.onloadedmetadata(new Event('loadedmetadata'));
            }
          }, 0);
          return mockVideoElement;
        }
        if (tagName === 'canvas') {
          return mockCanvasElement;
        }
        return document.createElement(tagName);
      });

      const camera = new CameraCapture();
      await camera.start();

      // Verify frame capture works before stop
      expect(() => camera.captureFrame()).not.toThrow();

      // Stop camera
      camera.stop();

      // Verify frame capture throws error after stop
      expect(() => camera.captureFrame()).toThrow('Camera not started');
    });
  });

  /**
   * Additional error scenarios
   */
  describe('Additional error scenarios', () => {
    it('should throw error when captureFrame() is called before start()', () => {
      const camera = new CameraCapture();

      // Attempt to capture frame before starting camera
      expect(() => camera.captureFrame()).toThrow('Camera not started');
    });

    it('should throw error when setFrameRate() is called with invalid value', () => {
      const camera = new CameraCapture();

      // Test zero frame rate
      expect(() => camera.setFrameRate(0)).toThrow('Frame rate must be positive');

      // Test negative frame rate
      expect(() => camera.setFrameRate(-5)).toThrow('Frame rate must be positive');
    });
  });
});
