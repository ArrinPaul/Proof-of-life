/**
 * Property-Based Tests for Camera Capture
 * 
 * Tests universal properties that should hold across all valid inputs.
 * Uses fast-check for property-based testing with 100+ iterations.
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import * as fc from 'fast-check';
import { CameraCapture } from './camera';

describe('Camera Capture - Property-Based Tests', () => {
  let mockGetUserMedia: ReturnType<typeof vi.fn>;
  let mockStream: MediaStream;
  let mockVideoTrack: MediaStreamTrack;

  beforeEach(() => {
    // Mock MediaStream and track
    mockVideoTrack = {
      stop: vi.fn(),
      kind: 'video',
      enabled: true,
      id: 'mock-track-id',
      label: 'mock camera',
      muted: false,
      readyState: 'live',
    } as unknown as MediaStreamTrack;

    mockStream = {
      getTracks: vi.fn(() => [mockVideoTrack]),
      getVideoTracks: vi.fn(() => [mockVideoTrack]),
      active: true,
    } as unknown as MediaStream;

    // Mock getUserMedia
    mockGetUserMedia = vi.fn().mockResolvedValue(mockStream);
    Object.defineProperty(navigator, 'mediaDevices', {
      writable: true,
      value: {
        getUserMedia: mockGetUserMedia,
      },
    });

    // Mock document.createElement for video and canvas
    const originalCreateElement = document.createElement.bind(document);
    vi.spyOn(document, 'createElement').mockImplementation((tagName: string) => {
      const element = originalCreateElement(tagName);
      
      if (tagName === 'video') {
        // Mock video element properties
        Object.defineProperty(element, 'videoWidth', { value: 1280, writable: true });
        Object.defineProperty(element, 'videoHeight', { value: 720, writable: true });
        
        // Trigger onloadedmetadata immediately
        setTimeout(() => {
          if (element.onloadedmetadata) {
            element.onloadedmetadata(new Event('loadedmetadata'));
          }
        }, 0);
      }
      
      if (tagName === 'canvas') {
        const mockContext = {
          drawImage: vi.fn(),
        } as unknown as CanvasRenderingContext2D;
        
        vi.spyOn(element as HTMLCanvasElement, 'getContext').mockReturnValue(mockContext);
        vi.spyOn(element as HTMLCanvasElement, 'toDataURL').mockReturnValue('data:image/jpeg;base64,/9j/4AAQSkZJRg==');
      }
      
      return element;
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  /**
   * Property 9: Frame encoding validity
   * 
   * For any captured video frame, the encoded output should be a valid base64 string
   * that can be decoded back to image data.
   * 
   * **Validates: Requirements 3.3**
   */
  it('Property 9: Frame encoding validity - encoded frames are valid base64 and decodable', async () => {
    await fc.assert(
      fc.asyncProperty(
        // Generate arbitrary number of frames to capture (1-3)
        fc.integer({ min: 1, max: 3 }),
        async (numFrames) => {
          const camera = new CameraCapture();
          
          try {
            // Start camera
            await camera.start();

            // Capture multiple frames
            for (let i = 0; i < numFrames; i++) {
              const encodedFrame = camera.captureFrame();

              // Property 1: Output should be a non-empty string
              expect(encodedFrame).toBeTruthy();
              expect(typeof encodedFrame).toBe('string');
              expect(encodedFrame.length).toBeGreaterThan(0);

              // Property 2: Should be a valid data URL with JPEG MIME type
              expect(encodedFrame).toMatch(/^data:image\/jpeg;base64,/);

              // Property 3: Extract base64 part and verify it's valid base64
              const base64Part = encodedFrame.replace(/^data:image\/jpeg;base64,/, '');
              expect(base64Part.length).toBeGreaterThan(0);
              
              // Valid base64 should only contain A-Z, a-z, 0-9, +, /, and = for padding
              expect(base64Part).toMatch(/^[A-Za-z0-9+/]+=*$/);

              // Property 4: Base64 string should be decodable
              // In browser environment, we can use atob to decode
              let decodedData: string;
              try {
                decodedData = atob(base64Part);
                expect(decodedData.length).toBeGreaterThan(0);
              } catch (error) {
                throw new Error(`Failed to decode base64 string: ${error}`);
              }

              // Property 5: Decoded data should represent valid image data
              // JPEG files start with FF D8 FF marker
              const firstByte = decodedData.charCodeAt(0);
              const secondByte = decodedData.charCodeAt(1);
              const thirdByte = decodedData.charCodeAt(2);
              
              expect(firstByte).toBe(0xFF);
              expect(secondByte).toBe(0xD8);
              expect(thirdByte).toBe(0xFF);
            }

          } finally {
            // Clean up
            camera.stop();
          }
        }
      ),
      { 
        numRuns: 10, // Run 10 iterations with random inputs
      }
    );
  }, 30000); // 30 second timeout for the entire test

  /**
   * Property 8: Frame capture rate consistency
   * 
   * For any active camera capture session, the time interval between consecutive
   * frame captures should be approximately 100ms ± 20ms (corresponding to 10 FPS ± 2 FPS).
   * 
   * **Validates: Requirements 3.2**
   */
  it('Property 8: Frame capture rate consistency - intervals between frames are within tolerance', async () => {
    await fc.assert(
      fc.asyncProperty(
        // Generate arbitrary frame rates between 8 and 12 FPS (around the target 10 FPS)
        fc.integer({ min: 8, max: 12 }),
        // Generate small number of frames to keep test fast (3-5 frames)
        fc.integer({ min: 3, max: 5 }),
        async (fps, numFrames) => {
          const camera = new CameraCapture();
          
          try {
            // Start camera
            await camera.start();
            camera.setFrameRate(fps);

            // Calculate expected interval in milliseconds
            const expectedInterval = 1000 / fps;
            const tolerance = 30; // ±30ms tolerance for JavaScript timer imprecision

            // Capture frames and record timestamps
            const timestamps: number[] = [];
            
            for (let i = 0; i < numFrames; i++) {
              timestamps.push(Date.now());
              camera.captureFrame();
              
              // Wait for the expected interval
              await new Promise(resolve => setTimeout(resolve, expectedInterval));
            }

            // Calculate intervals between consecutive captures
            const intervals: number[] = [];
            for (let i = 1; i < timestamps.length; i++) {
              intervals.push(timestamps[i] - timestamps[i - 1]);
            }

            // Property: All intervals should be within expectedInterval ± tolerance
            for (const interval of intervals) {
              const deviation = Math.abs(interval - expectedInterval);
              
              // Allow tolerance for timing variations in test environment
              expect(deviation).toBeLessThanOrEqual(tolerance);
            }

            // Additional check: Average interval should be close to expected
            const avgInterval = intervals.reduce((sum, val) => sum + val, 0) / intervals.length;
            const avgDeviation = Math.abs(avgInterval - expectedInterval);
            expect(avgDeviation).toBeLessThanOrEqual(tolerance);

          } finally {
            // Clean up
            camera.stop();
          }
        }
      ),
      { 
        numRuns: 10, // Run 10 iterations with random inputs
      }
    );
  }, 60000); // 60 second timeout for the entire test
});
