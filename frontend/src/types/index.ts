/**
 * Type definitions for the Proof of Life Authentication System
 */

// Authentication
export interface User {
  id: string
  email: string
  name: string
}

export interface AuthResult {
  success: boolean
  userId: string
  sessionToken: string
  error?: string
}

// Challenges
export interface Challenge {
  challengeId: string
  type: 'gesture' | 'expression'
  instruction: string
  timeoutSeconds: number
}

export interface ChallengeSequence {
  sessionId: string
  nonce: string
  timestamp: number
  challenges: Challenge[]
}

// Verification feedback
export type FeedbackType =
  | 'challenge_issued'
  | 'challenge_completed'
  | 'challenge_failed'
  | 'score_update'
  | 'verification_success'
  | 'verification_failed'
  | 'error'

export interface VerificationFeedback {
  type: FeedbackType
  message: string
  data?: {
    challenge?: Challenge
    score?: number
    finalScore?: number
    passed?: boolean
  }
}

// Session state
export type SessionStatus = 'idle' | 'active' | 'completed' | 'failed'

export interface SessionState {
  sessionId: string
  currentChallenge: Challenge | null
  completedChallenges: number
  totalChallenges: number
  currentScore: number
  status: SessionStatus
}

// Token
export interface VerificationToken {
  token: string
  expiresAt: number
  finalScore: number
}
