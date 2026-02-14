'use client'

import { useEffect, useState, useCallback } from 'react'
import { useAuth, useUser } from '@clerk/nextjs'
import { useRouter } from 'next/navigation'
import CameraCapture from '@/components/CameraCapture'
import ChallengeDisplay from '@/components/ChallengeDisplay'
import FeedbackDisplay from '@/components/FeedbackDisplay'
import { VerificationProvider, useVerification } from '@/lib/verification-context'
import { WebSocketClient } from '@/lib/websocket'
import { Challenge, VerificationFeedback } from '@/types'

function VerificationContent() {
  const { getToken } = useAuth()
  const { user } = useUser()
  const router = useRouter()
  const {
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
    reset
  } = useVerification()

  const [wsClient, setWsClient] = useState<WebSocketClient | null>(null)
  const [timeRemaining, setTimeRemaining] = useState(10)
  const [isStarting, setIsStarting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleWebSocketMessage = useCallback((data: any) => {
    console.log('WebSocket message:', data)

    if (data.type === 'challenge_issued') {
      const challenge: Challenge = {
        challengeId: data.challenge_id,
        type: data.challenge_type,
        instruction: data.instruction,
        timeoutSeconds: data.timeout || 10
      }
      updateChallenge(challenge)
      setTimeRemaining(challenge.timeoutSeconds)
      addFeedback({
        type: 'challenge_issued',
        message: `New challenge: ${challenge.instruction}`,
        data: { challenge }
      })
    } else if (data.type === 'challenge_completed') {
      incrementCompleted()
      addFeedback({
        type: 'challenge_completed',
        message: 'Challenge completed successfully!',
        data: { score: data.score }
      })
    } else if (data.type === 'challenge_failed') {
      addFeedback({
        type: 'challenge_failed',
        message: data.message || 'Challenge failed',
      })
    } else if (data.type === 'score_update') {
      updateScore(data.score)
      addFeedback({
        type: 'score_update',
        message: `Score updated: ${(data.score * 100).toFixed(0)}%`,
        data: { score: data.score }
      })
    } else if (data.type === 'verification_success') {
      updateStatus('completed')
      setToken({
        token: data.token,
        expiresAt: data.expires_at,
        finalScore: data.final_score
      })
      addFeedback({
        type: 'verification_success',
        message: 'Verification successful! You are authenticated.',
        data: { finalScore: data.final_score, passed: true }
      })
    } else if (data.type === 'verification_failed') {
      updateStatus('failed')
      addFeedback({
        type: 'verification_failed',
        message: data.message || 'Verification failed. Please try again.',
        data: { finalScore: data.final_score, passed: false }
      })
    } else if (data.type === 'error') {
      setError(data.message)
      addFeedback({
        type: 'error',
        message: data.message
      })
    }
  }, [updateChallenge, incrementCompleted, updateScore, updateStatus, addFeedback, setToken])

  const startVerification = async () => {
    try {
      setIsStarting(true)
      setError(null)

      const clerkToken = await getToken()
      if (!clerkToken) {
        throw new Error('Not authenticated')
      }

      const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const response = await fetch(`${apiUrl}/api/auth/verify`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${clerkToken}`
        },
        body: JSON.stringify({
          user_id: user?.id
        })
      })

      if (!response.ok) {
        throw new Error('Failed to start verification session')
      }

      const data = await response.json()
      const sessionId = data.session_id
      const wsUrl = data.websocket_url || `ws://localhost:8000/ws/verify/${sessionId}`

      startSession(sessionId, [])

      const client = new WebSocketClient(wsUrl)
      client.onMessage(handleWebSocketMessage)
      client.onError((error) => {
        console.error('WebSocket error:', error)
        setError('Connection error. Please try again.')
        updateStatus('failed')
      })
      client.onClose(() => {
        console.log('WebSocket closed')
        if (sessionState.status === 'active') {
          setError('Connection lost. Please try again.')
          updateStatus('failed')
        }
      })

      await client.connect()
      setWsClient(client)
      updateStatus('active')
    } catch (err) {
      console.error('Start verification error:', err)
      setError(err instanceof Error ? err.message : 'Failed to start verification')
      updateStatus('failed')
    } finally {
      setIsStarting(false)
    }
  }

  const handleFrame = useCallback((frameData: string) => {
    if (wsClient && wsClient.isConnected() && sessionState.status === 'active') {
      wsClient.sendFrame(frameData)
    }
  }, [wsClient, sessionState.status])

  const handleRestart = () => {
    if (wsClient) {
      wsClient.close()
    }
    reset()
    setError(null)
    setTimeRemaining(10)
  }

  useEffect(() => {
    let interval: NodeJS.Timeout
    if (sessionState.currentChallenge && sessionState.status === 'active') {
      interval = setInterval(() => {
        setTimeRemaining(prev => {
          if (prev <= 1) {
            return sessionState.currentChallenge?.timeoutSeconds || 10
          }
          return prev - 1
        })
      }, 1000)
    }
    return () => {
      if (interval) clearInterval(interval)
    }
  }, [sessionState.currentChallenge, sessionState.status])

  useEffect(() => {
    return () => {
      if (wsClient) {
        wsClient.close()
      }
    }
  }, [wsClient])

  if (!user) {
    router.push('/sign-in')
    return null
  }

  if (sessionState.status === 'completed' && token) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-green-50 to-white p-8">
        <div className="max-w-2xl mx-auto">
          <div className="bg-white rounded-lg shadow-xl p-8 text-center">
            <div className="text-6xl mb-4">✅</div>
            <h1 className="text-3xl font-bold text-green-600 mb-4">
              Verification Successful!
            </h1>
            <p className="text-gray-600 mb-6">
              You have been authenticated successfully.
            </p>
            <div className="bg-gray-50 rounded-lg p-4 mb-6">
              <p className="text-sm text-gray-600 mb-2">Final Score</p>
              <p className="text-4xl font-bold text-gray-900">
                {(token.finalScore * 100).toFixed(0)}%
              </p>
            </div>
            <div className="bg-blue-50 rounded-lg p-4 mb-6 text-left">
              <p className="text-sm font-medium text-gray-700 mb-2">Your Token:</p>
              <code className="text-xs text-gray-600 break-all block">
                {token.token.substring(0, 50)}...
              </code>
            </div>
            <button
              onClick={() => router.push('/profile')}
              className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition"
            >
              Go to Profile
            </button>
          </div>
        </div>
      </div>
    )
  }

  if (sessionState.status === 'failed') {
    return (
      <div className="min-h-screen bg-gradient-to-b from-red-50 to-white p-8">
        <div className="max-w-2xl mx-auto">
          <div className="bg-white rounded-lg shadow-xl p-8 text-center">
            <div className="text-6xl mb-4">❌</div>
            <h1 className="text-3xl font-bold text-red-600 mb-4">
              Verification Failed
            </h1>
            <p className="text-gray-600 mb-6">
              {error || 'Unable to verify your identity. Please try again.'}
            </p>
            <button
              onClick={handleRestart}
              className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition"
            >
              Try Again
            </button>
          </div>
        </div>
      </div>
    )
  }

  if (sessionState.status === 'idle') {
    return (
      <div className="min-h-screen bg-gradient-to-b from-blue-50 to-white p-8">
        <div className="max-w-2xl mx-auto">
          <div className="bg-white rounded-lg shadow-xl p-8">
            <h1 className="text-3xl font-bold text-gray-900 mb-4">
              Proof of Life Verification
            </h1>
            <p className="text-gray-600 mb-6">
              Welcome, {user.firstName || user.emailAddresses[0].emailAddress}!
            </p>
            <div className="bg-blue-50 rounded-lg p-6 mb-6">
              <h2 className="font-semibold text-gray-900 mb-3">What to expect:</h2>
              <ul className="space-y-2 text-gray-700">
                <li className="flex items-start gap-2">
                  <span>📹</span>
                  <span>You'll be asked to grant camera access</span>
                </li>
                <li className="flex items-start gap-2">
                  <span>🎯</span>
                  <span>Complete 3+ challenges (gestures and expressions)</span>
                </li>
                <li className="flex items-start gap-2">
                  <span>🤖</span>
                  <span>AI will verify you're a real person (not a deepfake)</span>
                </li>
                <li className="flex items-start gap-2">
                  <span>⏱️</span>
                  <span>Each challenge has a 10-second timeout</span>
                </li>
                <li className="flex items-start gap-2">
                  <span>🎉</span>
                  <span>Score 70% or higher to pass</span>
                </li>
              </ul>
            </div>
            <button
              onClick={startVerification}
              disabled={isStarting}
              className="w-full px-6 py-4 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition disabled:bg-gray-400 disabled:cursor-not-allowed text-lg font-semibold"
            >
              {isStarting ? 'Starting...' : 'Start Verification'}
            </button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-blue-50 to-white p-8">
      <div className="max-w-6xl mx-auto">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          <div className="space-y-6">
            <div className="bg-white rounded-lg shadow-lg p-6">
              <h2 className="text-xl font-bold text-gray-900 mb-4">Camera Feed</h2>
              <CameraCapture 
                onFrame={handleFrame}
                fps={10}
                isActive={sessionState.status === 'active'}
              />
            </div>
            <ChallengeDisplay 
              challenge={sessionState.currentChallenge}
              timeRemaining={timeRemaining}
            />
          </div>
          <div>
            <FeedbackDisplay 
              feedback={feedback}
              currentScore={sessionState.currentScore}
            />
          </div>
        </div>
      </div>
    </div>
  )
}

export default function VerifyPage() {
  return (
    <VerificationProvider>
      <VerificationContent />
    </VerificationProvider>
  )
}
