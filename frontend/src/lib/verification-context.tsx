'use client'

import { createContext, useContext, useState, useCallback, ReactNode } from 'react'
import { SessionState, Challenge, VerificationFeedback, VerificationToken, SessionStatus } from '@/types'

interface VerificationContextType {
  sessionState: SessionState
  feedback: VerificationFeedback[]
  token: VerificationToken | null
  startSession: (sessionId: string, challenges: Challenge[]) => void
  updateChallenge: (challenge: Challenge | null) => void
  incrementCompleted: () => void
  updateScore: (score: number) => void
  updateStatus: (status: SessionStatus) => void
  addFeedback: (feedback: VerificationFeedback) => void
  setToken: (token: VerificationToken) => void
  setTotalChallenges: (total: number) => void
  reset: () => void
}

const VerificationContext = createContext<VerificationContextType | undefined>(undefined)

const initialState: SessionState = {
  sessionId: '',
  currentChallenge: null,
  completedChallenges: 0,
  totalChallenges: 0,
  currentScore: 0,
  status: 'idle'
}

export function VerificationProvider({ children }: { children: ReactNode }) {
  const [sessionState, setSessionState] = useState<SessionState>(initialState)
  const [feedback, setFeedback] = useState<VerificationFeedback[]>([])
  const [token, setTokenState] = useState<VerificationToken | null>(null)

  const startSession = useCallback((sessionId: string, challenges: Challenge[]) => {
    setSessionState({
      sessionId,
      currentChallenge: null,
      completedChallenges: 0,
      totalChallenges: challenges.length,
      currentScore: 0,
      status: 'active'
    })
    setFeedback([])
    setTokenState(null)
  }, [])

  const updateChallenge = useCallback((challenge: Challenge | null) => {
    setSessionState(prev => ({ ...prev, currentChallenge: challenge }))
  }, [])

  const incrementCompleted = useCallback(() => {
    setSessionState(prev => ({ 
      ...prev, 
      completedChallenges: prev.completedChallenges + 1 
    }))
  }, [])

  const updateScore = useCallback((score: number) => {
    setSessionState(prev => ({ ...prev, currentScore: score }))
  }, [])

  const updateStatus = useCallback((status: SessionStatus) => {
    setSessionState(prev => ({ ...prev, status }))
  }, [])

  const addFeedback = useCallback((newFeedback: VerificationFeedback) => {
    setFeedback(prev => [...prev, newFeedback])
  }, [])

  const setToken = useCallback((newToken: VerificationToken) => {
    setTokenState(newToken)
  }, [])

  const setTotalChallenges = useCallback((total: number) => {
    setSessionState(prev => ({ ...prev, totalChallenges: total }))
  }, [])

  const reset = useCallback(() => {
    setSessionState(initialState)
    setFeedback([])
    setTokenState(null)
  }, [])

  return (
    <VerificationContext.Provider
      value={{
        sessionState,
        feedback,
        token,
        startSession,
        updateChallenge,
        incrementCompleted,
        updateScore,
        updateStatus,
        addFeedback,
        setToken,
        setTotalChallenges,
        reset
      }}
    >
      {children}
    </VerificationContext.Provider>
  )
}

export function useVerification() {
  const context = useContext(VerificationContext)
  if (context === undefined) {
    throw new Error('useVerification must be used within a VerificationProvider')
  }
  return context
}
