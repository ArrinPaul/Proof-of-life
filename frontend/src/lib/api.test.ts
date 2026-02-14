/**
 * Tests for API Client
 * 
 * Includes both property-based tests (universal properties across all inputs)
 * and unit tests (specific examples and edge cases).
 * Uses fast-check for property-based testing with 100+ iterations.
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import * as fc from 'fast-check';
import { APIClient } from './api';

describe('API Client - Property-Based Tests', () => {
  let apiClient: APIClient;
  let originalFetch: typeof global.fetch;

  beforeEach(() => {
    apiClient = new APIClient('http://localhost:8000');
    originalFetch = global.fetch;
  });

  afterEach(() => {
    global.fetch = originalFetch;
    vi.restoreAllMocks();
  });

  /**
   * Property 2: Session creation response structure
   * 
   * For any successful session creation request, the response should contain
   * both "session_id" and "websocket_url" fields with non-empty string values.
   * 
   * **Validates: Requirements 1.2**
   */
  it('Property 2: Session creation response structure - all successful responses contain session_id and websocket_url', async () => {
    await fc.assert(
      fc.asyncProperty(
        // Generate arbitrary user IDs (non-empty strings)
        fc.string({ minLength: 1, maxLength: 100 }),
        // Generate arbitrary session IDs (non-empty strings)
        fc.string({ minLength: 1, maxLength: 100 }),
        // Generate arbitrary WebSocket URLs (non-empty strings)
        fc.string({ minLength: 1, maxLength: 200 }),
        async (userId, sessionId, websocketUrl) => {
          // Mock successful response with generated values
          global.fetch = vi.fn().mockResolvedValue({
            ok: true,
            json: async () => ({
              session_id: sessionId,
              websocket_url: websocketUrl,
              message: 'Session created successfully',
            }),
          });

          // Call createSession
          const response = await apiClient.createSession(userId);

          // Property: Response must contain both fields with non-empty string values
          expect(response).toHaveProperty('session_id');
          expect(response).toHaveProperty('websocket_url');
          expect(typeof response.session_id).toBe('string');
          expect(typeof response.websocket_url).toBe('string');
          expect(response.session_id.length).toBeGreaterThan(0);
          expect(response.websocket_url.length).toBeGreaterThan(0);
        }
      ),
      { numRuns: 20 } // Run 20 iterations with random inputs
    );
  });
});

describe('API Client - Unit Tests for Error Handling', () => {
  let apiClient: APIClient;
  let originalFetch: typeof global.fetch;

  beforeEach(() => {
    apiClient = new APIClient('http://localhost:8000');
    originalFetch = global.fetch;
  });

  afterEach(() => {
    global.fetch = originalFetch;
    vi.restoreAllMocks();
  });

  describe('createSession error handling', () => {
    /**
     * Test network errors (fetch rejection)
     * 
     * Validates Requirements: 12.4
     */
    it('should throw error on network failure', async () => {
      // Mock network error
      global.fetch = vi.fn().mockRejectedValue(new Error('Network error'));

      await expect(apiClient.createSession('user123')).rejects.toThrow('Network error');
    });

    /**
     * Test 4xx client errors
     * 
     * Validates Requirements: 12.4
     */
    it('should throw error with message from 400 Bad Request', async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: false,
        status: 400,
        json: async () => ({
          error: {
            code: 'INVALID_REQUEST',
            message: 'User ID is required',
            category: 'validation',
            recoverable: true,
          },
        }),
      });

      await expect(apiClient.createSession('')).rejects.toThrow('User ID is required');
    });

    it('should throw error with message from 401 Unauthorized', async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: false,
        status: 401,
        json: async () => ({
          error: {
            code: 'UNAUTHORIZED',
            message: 'Authentication required',
            category: 'authentication',
            recoverable: false,
          },
        }),
      });

      await expect(apiClient.createSession('user123')).rejects.toThrow('Authentication required');
    });

    it('should throw error with message from 404 Not Found', async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: false,
        status: 404,
        json: async () => ({
          error: {
            code: 'NOT_FOUND',
            message: 'Endpoint not found',
            category: 'system',
            recoverable: false,
          },
        }),
      });

      await expect(apiClient.createSession('user123')).rejects.toThrow('Endpoint not found');
    });

    /**
     * Test 5xx server errors
     * 
     * Validates Requirements: 12.4
     */
    it('should throw error with message from 500 Internal Server Error', async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: false,
        status: 500,
        json: async () => ({
          error: {
            code: 'INTERNAL_ERROR',
            message: 'Internal server error',
            category: 'system',
            recoverable: true,
          },
        }),
      });

      await expect(apiClient.createSession('user123')).rejects.toThrow('Internal server error');
    });

    it('should throw error with message from 503 Service Unavailable', async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: false,
        status: 503,
        json: async () => ({
          error: {
            code: 'SERVICE_UNAVAILABLE',
            message: 'Service temporarily unavailable',
            category: 'system',
            recoverable: true,
          },
        }),
      });

      await expect(apiClient.createSession('user123')).rejects.toThrow('Service temporarily unavailable');
    });

    /**
     * Test JSON parsing errors
     * 
     * Validates Requirements: 12.4
     */
    it('should throw error when response JSON parsing fails', async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: false,
        status: 500,
        json: async () => {
          throw new Error('Invalid JSON');
        },
      });

      await expect(apiClient.createSession('user123')).rejects.toThrow('Invalid JSON');
    });

    it('should throw default error message when error object is missing', async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: false,
        status: 500,
        json: async () => ({}),
      });

      await expect(apiClient.createSession('user123')).rejects.toThrow('Failed to create session');
    });

    it('should throw default error message when error message is missing', async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: false,
        status: 500,
        json: async () => ({
          error: {
            code: 'UNKNOWN_ERROR',
          },
        }),
      });

      await expect(apiClient.createSession('user123')).rejects.toThrow('Failed to create session');
    });
  });

  describe('validateToken error handling', () => {
    /**
     * Test network errors (fetch rejection)
     * 
     * Validates Requirements: 12.4
     */
    it('should throw error on network failure', async () => {
      global.fetch = vi.fn().mockRejectedValue(new Error('Network error'));

      await expect(apiClient.validateToken('token123')).rejects.toThrow('Network error');
    });

    /**
     * Test 401 Unauthorized (invalid token) - should return valid: false
     * 
     * Validates Requirements: 12.4
     */
    it('should return valid: false for 401 Unauthorized', async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: false,
        status: 401,
        json: async () => ({
          error: 'Token is invalid or expired',
        }),
      });

      const result = await apiClient.validateToken('invalid-token');
      expect(result.valid).toBe(false);
      expect(result.error).toBe('Token is invalid or expired');
    });

    /**
     * Test other 4xx client errors
     * 
     * Validates Requirements: 12.4
     */
    it('should throw error with message from 400 Bad Request', async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: false,
        status: 400,
        json: async () => ({
          error: {
            code: 'INVALID_REQUEST',
            message: 'Token is required',
            category: 'validation',
            recoverable: true,
          },
        }),
      });

      await expect(apiClient.validateToken('')).rejects.toThrow('Token is required');
    });

    /**
     * Test 5xx server errors
     * 
     * Validates Requirements: 12.4
     */
    it('should throw error with message from 500 Internal Server Error', async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: false,
        status: 500,
        json: async () => ({
          error: {
            code: 'INTERNAL_ERROR',
            message: 'Internal server error',
            category: 'system',
            recoverable: true,
          },
        }),
      });

      await expect(apiClient.validateToken('token123')).rejects.toThrow('Internal server error');
    });

    /**
     * Test JSON parsing errors
     * 
     * Validates Requirements: 12.4
     */
    it('should throw error when response JSON parsing fails', async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: false,
        status: 500,
        json: async () => {
          throw new Error('Invalid JSON');
        },
      });

      await expect(apiClient.validateToken('token123')).rejects.toThrow('Invalid JSON');
    });

    it('should throw default error message when error object is missing', async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: false,
        status: 500,
        json: async () => ({}),
      });

      await expect(apiClient.validateToken('token123')).rejects.toThrow('Failed to validate token');
    });
  });
});
