/**
 * API Client for Backend Communication
 * 
 * Centralized HTTP client for making requests to the FastAPI backend.
 * Handles session creation, token validation, and error handling.
 * 
 * Validates Requirements: 1.1, 1.2, 12.1, 12.2, 12.3, 12.4, 12.5
 */

// Get API base URL from environment variable
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

/**
 * Response from session creation endpoint
 */
export interface SessionResponse {
  session_id: string;
  websocket_url: string;
  message: string;
}

/**
 * Response from token validation endpoint
 */
export interface TokenValidationResponse {
  valid: boolean;
  user_id?: string;
  session_id?: string;
  issued_at?: number;
  expires_at?: number;
  error?: string;
}

/**
 * Structured error response from backend
 */
export interface APIError {
  code: string;
  message: string;
  category: string;
  recoverable: boolean;
}

/**
 * API Client for backend communication
 */
export class APIClient {
  private baseURL: string;

  constructor(baseURL: string = API_BASE_URL) {
    this.baseURL = baseURL;
  }

  /**
   * Create a new verification session
   * 
   * @param userId - User identifier
   * @param authToken - Optional Clerk auth token for backend validation
   * @returns Session response with session_id and websocket_url
   * @throws Error if session creation fails
   * 
   * Validates Requirements: 1.1, 1.2, 12.2
   */
  async createSession(userId: string, authToken?: string): Promise<SessionResponse> {
    try {
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
      };
      if (authToken) {
        headers['Authorization'] = `Bearer ${authToken}`;
      }

      const response = await fetch(`${this.baseURL}/api/auth/verify`, {
        method: 'POST',
        headers,
        body: JSON.stringify({ user_id: userId }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        const error = errorData.error as APIError;
        throw new Error(error?.message || 'Failed to create session');
      }

      const data: SessionResponse = await response.json();
      return data;
    } catch (error) {
      if (error instanceof Error) {
        throw error;
      }
      throw new Error('Failed to create session');
    }
  }

  /**
   * Validate a JWT token
   * 
   * @param token - JWT token to validate
   * @returns Token validation response
   * @throws Error if validation request fails
   * 
   * Validates Requirements: 12.3
   */
  async validateToken(token: string): Promise<TokenValidationResponse> {
    try {
      const response = await fetch(`${this.baseURL}/api/token/validate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ token }),
      });

      if (!response.ok) {
        // For 401 responses, the token is invalid
        if (response.status === 401) {
          const errorData = await response.json();
          return {
            valid: false,
            error: errorData.error || 'Token is invalid',
          };
        }

        // For other errors, throw
        const errorData = await response.json();
        const error = errorData.error as APIError;
        throw new Error(error?.message || 'Failed to validate token');
      }

      const data: TokenValidationResponse = await response.json();
      return data;
    } catch (error) {
      if (error instanceof Error) {
        throw error;
      }
      throw new Error('Failed to validate token');
    }
  }
}

// Export a default instance
export const apiClient = new APIClient();
