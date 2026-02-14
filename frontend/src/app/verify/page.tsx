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
    setTotalChallenges,
    reset
  } = useVerification()

  const [wsClient, setWsClient] = useState<WebSocketClient | null>(null)
  const [timeRemaining, setTimeRemaining] = useState(20)
  const [isStarting, setIsStarting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [challengeStatus, setChallengeStatus] = useState<string>('')

  const handleWebSocketMessage = useCallback((data: any) => {
    console.log('WebSocket message:', data)

    if (data.type === 'challenge_issued') {
      const challenge: Challenge = {
        challengeId: data.data?.challenge_id || '',
        type: data.data?.type || 'gesture',
        instruction: data.data?.instruction || data.message || '',
        timeoutSeconds: data.data?.timeout_seconds || 20
      }
      updateChallenge(challenge)
      setTimeRemaining(challenge.timeoutSeconds)
      setChallengeStatus('get-ready')
      const challengeNum = data.data?.challenge_number || ''
      const totalNum = data.data?.total_challenges || ''
      if (totalNum) setTotalChallenges(totalNum)
      addFeedback({
        type: 'challenge_issued',
        message: `Challenge ${challengeNum}/${totalNum}: ${challenge.instruction}`,
        data: { challenge }
      })
    } else if (data.type === 'challenge_completed') {
      incrementCompleted()
      addFeedback({
        type: 'challenge_completed',
        message: 'Challenge completed successfully!',
        data: { score: data.data?.confidence }
      })
    } else if (data.type === 'challenge_failed') {
      addFeedback({
        type: 'challenge_failed',
        message: data.message || 'Challenge failed',
      })
    } else if (data.type === 'score_update') {
      const score = data.data?.liveness_score || 0
      updateScore(score)
      // Handle status messages (get ready / go)
      if (data.data?.status === 'preparing') {
        setChallengeStatus('get-ready')
      } else if (data.data?.status === 'recording') {
        setChallengeStatus('recording')
      }
      if (data.data?.completed_count !== undefined) {
        addFeedback({
          type: 'score_update',
          message: data.message || `Progress: ${(score * 100).toFixed(0)}%`,
          data: { score, completed_count: data.data.completed_count, total_challenges: data.data.total_challenges }
        })
      }
    } else if (data.type === 'verification_success') {
      updateStatus('completed')
      setToken({
        token: data.data?.token,
        expiresAt: data.data?.expires_at,
        finalScore: data.data?.final_score
      })
      addFeedback({
        type: 'verification_success',
        message: 'Verification successful! You are authenticated.',
        data: { finalScore: data.data?.final_score, passed: true }
      })
    } else if (data.type === 'verification_failed') {
      updateStatus('failed')
      addFeedback({
        type: 'verification_failed',
        message: data.message || 'Verification failed. Please try again.',
        data: { finalScore: data.data?.final_score, passed: false }
      })
    } else if (data.type === 'error') {
      setError(data.message)
      addFeedback({
        type: 'error',
        message: data.message
      })
    }
  }, [updateChallenge, incrementCompleted, updateScore, updateStatus, addFeedback, setToken, setTotalChallenges])

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

      startSession(sessionId, [])

      const client = new WebSocketClient(sessionId)
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
      wsClient.disconnect()
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
        wsClient.disconnect()
      }
    }
  }, [wsClient])

  if (!user) {
    router.push('/sign-in')
    return null
  }

  if (sessionState.status === 'completed' && token) {
    return (
      <div className="min-h-screen bg-grid relative overflow-hidden p-8">
        <div className="absolute inset-0 pointer-events-none">
          <div className="absolute top-1/3 left-1/2 -translate-x-1/2 w-[500px] h-[500px] bg-neon-green/[0.04] rounded-full blur-[120px]" />
        </div>
        <div className="max-w-2xl mx-auto relative z-10">
          <div className="bg-void-100/80 backdrop-blur-xl border border-neon-green/20 p-8 text-center shadow-glow-green" style={{ borderRadius: '2px' }}>
            <div className="w-14 h-14 mx-auto flex items-center justify-center bg-neon-green/[0.08] border border-neon-green/20 mb-6" style={{ borderRadius: '2px' }}>
              <svg className="w-7 h-7 text-neon-green" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
              </svg>
            </div>
            <h1 className="font-display text-3xl font-bold text-ink-100 mb-3">
              Identity Verified
            </h1>
            <p className="text-ink-400 font-mono text-sm mb-8">
              Authentication token issued successfully.
            </p>
            <div className="bg-void-200/60 border border-white/[0.06] p-5 mb-6" style={{ borderRadius: '2px' }}>
              <p className="text-[10px] font-mono tracking-[0.2em] uppercase text-ink-500 mb-2">Final Score</p>
              <p className="font-mono text-4xl font-bold text-neon-green">
                {(token.finalScore * 100).toFixed(0)}%
              </p>
            </div>
            <div className="bg-void-200/40 border border-white/[0.06] p-4 mb-6 text-left" style={{ borderRadius: '2px' }}>
              <p className="text-[10px] font-mono tracking-[0.2em] uppercase text-ink-500 mb-2">Token</p>
              <code className="text-[11px] font-mono text-ink-400 break-all block">
                {token.token.substring(0, 50)}...
              </code>
            </div>
            <div className="flex gap-3 justify-center">
              <button
                onClick={() => router.push('/profile')}
                className="px-6 py-3 font-mono text-sm tracking-[0.15em] uppercase bg-neon-cyan text-void-50 font-bold clip-corner shadow-glow-cyan"
              >
                Go to Profile
              </button>
              <button
                onClick={() => router.push('/blockchain')}
                className="px-6 py-3 font-mono text-sm tracking-[0.15em] uppercase border border-neon-purple/30 text-neon-purple clip-corner hover:bg-neon-purple/[0.05] transition-colors"
              >
                View Ledger
              </button>
            </div>
          </div>
        </div>
      </div>
    )
  }

  if (sessionState.status === 'failed') {
    return (
      <div className="min-h-screen bg-grid relative overflow-hidden p-8">
        <div className="absolute inset-0 pointer-events-none">
          <div className="absolute top-1/3 left-1/2 -translate-x-1/2 w-[500px] h-[500px] bg-neon-red/[0.04] rounded-full blur-[120px]" />
        </div>
        <div className="max-w-2xl mx-auto relative z-10">
          <div className="bg-void-100/80 backdrop-blur-xl border border-neon-red/20 p-8 text-center shadow-glow-red" style={{ borderRadius: '2px' }}>
            <div className="w-14 h-14 mx-auto flex items-center justify-center bg-neon-red/[0.08] border border-neon-red/20 mb-6" style={{ borderRadius: '2px' }}>
              <svg className="w-7 h-7 text-neon-red" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </div>
            <h1 className="font-display text-3xl font-bold text-ink-100 mb-3">
              Verification Failed
            </h1>
            <p className="text-ink-400 font-mono text-sm mb-8">
              {error || 'Unable to verify identity. Retry recommended.'}
            </p>
            <button
              onClick={handleRestart}
              className="px-6 py-3 font-mono text-sm tracking-[0.15em] uppercase bg-void-200/80 text-ink-200 border border-white/[0.08]"
              style={{ borderRadius: '2px' }}
            >
              Retry Protocol
            </button>
          </div>
        </div>
      </div>
    )
  }

  if (sessionState.status === 'idle') {
    return (
      <div className="min-h-screen bg-grid relative overflow-hidden p-8">
        <div className="absolute inset-0 pointer-events-none">
          <div className="absolute top-1/3 left-1/2 -translate-x-1/2 w-[500px] h-[500px] bg-neon-cyan/[0.03] rounded-full blur-[120px]" />
        </div>
        <div className="max-w-2xl mx-auto relative z-10">
          <div className="bg-void-100/80 backdrop-blur-xl border border-white/[0.06] p-8" style={{ borderRadius: '2px' }}>
            <div className="absolute top-0 left-0 right-0 h-px bg-gradient-to-r from-transparent via-neon-cyan/30 to-transparent" />
            <h1 className="font-display text-3xl font-bold text-ink-100 mb-2">
              SENTINEL
            </h1>
            <p className="font-mono text-xs tracking-[0.2em] uppercase text-neon-cyan/60 mb-6">
              Proof-of-Life Protocol
            </p>
            <p className="text-ink-300 font-mono text-sm mb-8">
              Welcome, {user.firstName || user.emailAddresses[0].emailAddress}
            </p>
            <div className="bg-void-200/60 border border-white/[0.06] p-5 mb-8" style={{ borderRadius: '2px' }}>
              <h2 className="font-mono text-[10px] tracking-[0.2em] uppercase text-ink-400 mb-4">Protocol Steps</h2>
              <ul className="space-y-3 text-sm font-mono text-ink-400">
                <li className="flex items-start gap-3">
                  <span className="text-neon-cyan text-xs mt-0.5">01</span>
                  <span>Grant camera access for biometric capture</span>
                </li>
                <li className="flex items-start gap-3">
                  <span className="text-neon-cyan text-xs mt-0.5">02</span>
                  <span>Complete 8 gesture &amp; expression challenges</span>
                </li>
                <li className="flex items-start gap-3">
                  <span className="text-neon-cyan text-xs mt-0.5">03</span>
                  <span>ML pipeline verifies liveness &amp; deepfake detection</span>
                </li>
                <li className="flex items-start gap-3">
                  <span className="text-neon-cyan text-xs mt-0.5">04</span>
                  <span>20-second window per challenge with 3s prep time</span>
                </li>
                <li className="flex items-start gap-3">
                  <span className="text-neon-cyan text-xs mt-0.5">05</span>
                  <span>Score 70%+ threshold to receive JWT token</span>
                </li>
              </ul>
            </div>
            <button
              onClick={startVerification}
              disabled={isStarting}
              className="w-full py-4 font-mono text-sm tracking-[0.15em] uppercase text-void-50 bg-neon-cyan font-bold clip-corner shadow-glow-cyan disabled:opacity-40 disabled:cursor-not-allowed"
            >
              {isStarting ? 'Initializing...' : 'Initialize Scan'}
            </button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-grid relative overflow-hidden p-6">
      <div className="absolute inset-0 pointer-events-none">
        <div className="absolute top-1/4 left-1/4 w-[400px] h-[400px] bg-neon-cyan/[0.02] rounded-full blur-[100px]" />
        <div className="absolute bottom-1/4 right-1/4 w-[400px] h-[400px] bg-neon-purple/[0.02] rounded-full blur-[100px]" />
      </div>
      <div className="max-w-6xl mx-auto relative z-10">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="space-y-4">
            <div className="bg-void-100/80 backdrop-blur-xl border border-white/[0.06] p-5" style={{ borderRadius: '2px' }}>
              <h2 className="font-mono text-[10px] tracking-[0.2em] uppercase text-ink-400 mb-4">Camera Feed</h2>
              <CameraCapture 
                onFrame={handleFrame}
                fps={30}
                isActive={sessionState.status === 'active'}
              />
            </div>
            <ChallengeDisplay 
              challenge={sessionState.currentChallenge}
              timeRemaining={timeRemaining}
              status={challengeStatus}
            />
          </div>
          <div>
            <FeedbackDisplay 
              feedback={feedback}
              currentScore={sessionState.currentScore}
              completedCount={sessionState.completedChallenges}
              totalChallenges={sessionState.totalChallenges}
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
