/**
 * Property-Based Tests for WebSocket Client
 * 
 * Tests universal properties that should hold across all valid inputs.
 * Uses fast-check for property-based testing.
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import * as fc from 'fast-check';
import { WebSocketClient } from './websocket';

describe('WebSocket Client - Property-Based Tests', () => {
  let mockWebSocket: any;
  let mockWebSocketInstances: any[] = [];

  beforeEach(() => {
    // Clear instances array
    mockWebSocketInstances = [];

    // Mock WebSocket constructor with proper constants
    const MockWebSocketClass = vi.fn().mockImplementation((url: string) => {
      const instance = {
        url,
        readyState: 0, // CONNECTING
        send: vi.fn(),
        close: vi.fn(),
        onopen: null as ((event: Event) => void) | null,
        onmessage: null as ((event: MessageEvent) => void) | null,
        onerror: null as ((event: Event) => void) | null,
        onclose: null as ((event: CloseEvent) => void) | null,
        CONNECTING: 0,
        OPEN: 1,
        CLOSING: 2,
        CLOSED: 3,
      };
      
      mockWebSocketInstances.push(instance);
      return instance;
    }) as any;

    // Set WebSocket constants on the constructor
    MockWebSocketClass.CONNECTING = 0;
    MockWebSocketClass.OPEN = 1;
    MockWebSocketClass.CLOSING = 2;
    MockWebSocketClass.CLOSED = 3;

    global.WebSocket = MockWebSocketClass;
  });

  afterEach(() => {
    vi.restoreAllMocks();
    mockWebSocketInstances = [];
  });

  /**
   * Property 5: WebSocket URL construction
   * 
   * For any session_id string, the WebSocket client should construct a URL matching
   * the pattern `{WS_BASE_URL}/ws/verify/{session_id}` where WS_BASE_URL comes from
   * environment configuration.
   * 
   * **Validates: Requirements 2.1**
   */
  it('Property 5: WebSocket URL construction - URL matches expected pattern for any session_id', async () => {
    await fc.assert(
      fc.asyncProperty(
        // Generate arbitrary session IDs (alphanumeric strings, UUIDs, etc.)
        fc.oneof(
          fc.uuid(),
          fc.hexaString({ minLength: 8, maxLength: 32 }),
          fc.stringMatching(/^[a-zA-Z0-9_-]{8,32}$/),
        ),
        async (sessionId) => {
          // Set environment variable for WebSocket base URL
          const wsBaseUrl = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000';
          
          // Create WebSocket client with session ID
          const client = new WebSocketClient(sessionId);
          
          // Attempt to connect (this will construct the URL)
          const connectPromise = client.connect();
          
          // Wait a tick for WebSocket constructor to be called
          await new Promise(resolve => setTimeout(resolve, 0));
          
          // Property 1: WebSocket constructor should have been called
          expect(global.WebSocket).toHaveBeenCalled();
          
          // Property 2: URL should match the expected pattern
          const constructedUrl = mockWebSocketInstances[mockWebSocketInstances.length - 1].url;
          const expectedUrl = `${wsBaseUrl}/ws/verify/${sessionId}`;
          expect(constructedUrl).toBe(expectedUrl);
          
          // Property 3: URL should contain the session ID
          expect(constructedUrl).toContain(sessionId);
          
          // Property 4: URL should start with ws:// or wss://
          expect(constructedUrl).toMatch(/^wss?:\/\//);
          
          // Property 5: URL should contain /ws/verify/ path
          expect(constructedUrl).toContain('/ws/verify/');
          
          // Clean up
          client.disconnect();
        }
      ),
      { 
        numRuns: 15, // Run 15 iterations with random session IDs
      }
    );
  });

  /**
   * Property 26: Frontend message type field
   * 
   * For any message sent by the frontend WebSocket client, the message should be
   * valid JSON containing a "type" field with a string value.
   * 
   * **Validates: Requirements 13.1**
   */
  it('Property 26: Frontend message type field - all sent messages have valid type field', async () => {
    await fc.assert(
      fc.asyncProperty(
        // Generate arbitrary session ID
        fc.uuid(),
        // Generate arbitrary frame data (base64-like strings)
        fc.base64String({ minLength: 10, maxLength: 100 }),
        async (sessionId, frameData) => {
          const client = new WebSocketClient(sessionId);
          
          // Start connection
          const connectPromise = client.connect();
          
          // Wait a tick for WebSocket constructor to be called
          await new Promise(resolve => setTimeout(resolve, 0));
          
          const wsInstance = mockWebSocketInstances[mockWebSocketInstances.length - 1];
          
          // Set readyState to OPEN before triggering onopen
          wsInstance.readyState = 1; // OPEN
          
          // Trigger onopen callback to resolve the connect promise
          if (wsInstance.onopen) {
            wsInstance.onopen(new Event('open'));
          }
          
          // Wait for connection to complete
          await connectPromise;
          
          // Ensure readyState is still OPEN
          wsInstance.readyState = 1;
          
          // Send a frame
          client.sendFrame(frameData);
          
          // Property 1: send should have been called
          expect(wsInstance.send).toHaveBeenCalled();
          
          // Get the sent message
          const sentMessage = wsInstance.send.mock.calls[0][0];
          
          // Property 2: Message should be valid JSON
          let parsedMessage: any;
          expect(() => {
            parsedMessage = JSON.parse(sentMessage);
          }).not.toThrow();
          
          // Property 3: Message should have a "type" field
          expect(parsedMessage).toHaveProperty('type');
          
          // Property 4: "type" field should be a string
          expect(typeof parsedMessage.type).toBe('string');
          
          // Property 5: "type" field should not be empty
          expect(parsedMessage.type.length).toBeGreaterThan(0);
          
          // Property 6: For video frames, type should be "video_frame"
          expect(parsedMessage.type).toBe('video_frame');
          
          // Property 7: Message should have a "frame" field with the frame data
          expect(parsedMessage).toHaveProperty('frame');
          expect(parsedMessage.frame).toBe(frameData);
          
          // Clean up
          client.disconnect();
        }
      ),
      { 
        numRuns: 15, // Run 15 iterations
      }
    );
  });

  /**
   * Property 22: Reconnection attempt limit
   * 
   * For any unexpected WebSocket disconnection during verification, exactly one
   * reconnection attempt should be made. If reconnection fails, no further attempts
   * should be made.
   * 
   * **Validates: Requirements 9.2, 9.3**
   */
  it('Property 22: Reconnection attempt limit - exactly one reconnection attempt on unexpected disconnect', async () => {
    await fc.assert(
      fc.asyncProperty(
        // Generate arbitrary session ID
        fc.uuid(),
        // Generate arbitrary close codes (non-1000 for unexpected disconnect)
        fc.integer({ min: 1001, max: 1011 }).filter(code => code !== 1000),
        async (sessionId, closeCode) => {
          // Reset mock call history for this iteration
          vi.clearAllMocks();
          mockWebSocketInstances = [];
          
          const client = new WebSocketClient(sessionId);
          
          // Start connection
          const connectPromise = client.connect();
          await new Promise(resolve => setTimeout(resolve, 0));
          
          const firstInstance = mockWebSocketInstances[mockWebSocketInstances.length - 1];
          
          // Set readyState to OPEN before triggering onopen
          firstInstance.readyState = 1; // OPEN
          
          // Trigger onopen callback
          if (firstInstance.onopen) {
            firstInstance.onopen(new Event('open'));
          }
          
          await connectPromise;
          
          // Property 1: Initial connection should have created one WebSocket
          expect((global.WebSocket as any).mock.calls.length).toBe(1);
          
          // Simulate unexpected disconnect (wasClean = false, code != 1000)
          const closeEvent = {
            wasClean: false,
            code: closeCode,
            reason: 'Unexpected disconnect',
          } as CloseEvent;
          
          if (firstInstance.onclose) {
            firstInstance.onclose(closeEvent);
          }
          
          // Wait for reconnection attempt (2 second delay + small buffer)
          await new Promise(resolve => setTimeout(resolve, 2100));
          
          // Property 2: Exactly one reconnection attempt should have been made
          expect((global.WebSocket as any).mock.calls.length).toBe(2);
          
          // Get the second instance and complete its connection
          const secondInstance = mockWebSocketInstances[mockWebSocketInstances.length - 1];
          secondInstance.readyState = 1; // OPEN
          
          if (secondInstance.onopen) {
            secondInstance.onopen(new Event('open'));
          }
          
          // Wait a bit for connection to stabilize
          await new Promise(resolve => setTimeout(resolve, 50));
          
          // Simulate second disconnect
          if (secondInstance.onclose) {
            secondInstance.onclose(closeEvent);
          }
          
          // Wait for potential second reconnection attempt (2 second delay + buffer)
          await new Promise(resolve => setTimeout(resolve, 2100));
          
          // Property 3: No additional reconnection attempts should be made
          // Should still be at 2 (no third connection)
          expect((global.WebSocket as any).mock.calls.length).toBe(2);
          
          // Clean up
          client.disconnect();
        }
      ),
      { 
        numRuns: 10, // Run 10 iterations
      }
    );
  }, 60000); // 60 second timeout for the entire test
});
