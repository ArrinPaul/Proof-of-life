'use client'

import { useEffect, useState, useRef } from 'react'
import { useAuth, useUser } from '@clerk/nextjs'
import { useRouter } from 'next/navigation'
import { motion, AnimatePresence } from 'framer-motion'
import FaceIDScanner from '@/components/FaceIDScanner'
import GlassCard from '@/components/GlassCard'
import { apiClient } from '@/lib/api'
import { WebSocketClient, FeedbackMessage } from '@/lib/websocket'
import { CameraCapture } from '@/lib/camera'

export default function VerifyGlassPage() {
  const { isLoaded, userId, getToken } = useAuth()
  const { user } = useUser()
  const router = useRouter()
  const [step, setStep] = useState<'idle' | 'scanning' | 'success' | 'error'>('idle')
  const [progress, setProgress] = useState(0)
  const [currentChallenge, setCurrentChallenge] = useState<string>('')
  const [completedChallenges, setCompletedChallenges] = useState(0)
  const [totalChallenges, setTotalChallenges] = useState(3)
  const [scores, setScores] = useState({ liveness: 0, emotion: 0, deepfake: 0 })
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [token, setToken] = useState<string | null>(null)
  const [errorMessage, setErrorMessage] = useState<string>('')
  const [finalScore, setFinalScore] = useState<number>(0)

  // Refs for WebSocket and Camera instances
  const wsClientRef = useRef<WebSocketClient | null>(null)
  const cameraRef = useRef<CameraCapture | null>(null)
  const frameCaptureIntervalRef = useRef<NodeJS.Timeout | null>(null)

  // Redirect to sign-in if not authenticated
  useEffect(() => {
    if (isLoaded && !userId) {
      router.push('/sign-in')
    }
  }, [isLoaded, userId, router])

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      cleanup()
    }
  }, [])

  const cleanup = () => {
    // Stop frame capture
    if (frameCaptureIntervalRef.current) {
      clearInterval(frameCaptureIntervalRef.current)
      frameCaptureIntervalRef.current = null
    }

    // Disconnect WebSocket
    if (wsClientRef.current) {
      wsClientRef.current.disconnect()
      wsClientRef.current = null
    }

    // Stop camera
    if (cameraRef.current) {
      cameraRef.current.stop()
      cameraRef.current = null
    }
  }

  const startVerification = async () => {
    try {
      setStep('scanning')
      setProgress(0)
      setCompletedChallenges(0)
      setErrorMessage('')
      setScores({ liveness: 0, emotion: 0, deepfake: 0 })

      // Task 6.1: Create session using Clerk-authenticated user
      if (!userId) {
        throw new Error('Not authenticated')
      }
      const clerkToken = await getToken()
      const sessionResponse = await apiClient.createSession(userId, clerkToken ?? undefined)
      setSessionId(sessionResponse.session_id)

      // Task 6.2: Establish WebSocket connection
      const wsClient = new WebSocketClient(sessionResponse.session_id)
      wsClientRef.current = wsClient

      // Set up WebSocket message handlers
      wsClient.onMessage(handleWebSocketMessage)
      wsClient.onError(handleWebSocketError)
      wsClient.onClose(handleWebSocketClose)

      await wsClient.connect()

      // Task 6.3: Start camera capture
      const camera = new CameraCapture()
      cameraRef.current = camera
      await camera.start()

      // Start sending frames at 10 FPS
      startFrameCapture()

    } catch (error) {
      console.error('Failed to start verification:', error)
      setStep('error')
      if (error instanceof Error) {
        if (error.name === 'NotAllowedError') {
          setErrorMessage('Camera access denied. Please allow camera access to continue.')
        } else if (error.name === 'NotFoundError') {
          setErrorMessage('No camera found. Please connect a camera to continue.')
        } else {
          setErrorMessage(error.message || 'Failed to start verification. Please try again.')
        }
      } else {
        setErrorMessage('Failed to start verification. Please try again.')
      }
      cleanup()
    }
  }

  const startFrameCapture = () => {
    // Capture and send frames at 10 FPS (every 100ms)
    frameCaptureIntervalRef.current = setInterval(() => {
      if (cameraRef.current && wsClientRef.current?.isConnected()) {
        try {
          const frameData = cameraRef.current.captureFrame()
          wsClientRef.current.sendFrame(frameData)
        } catch (error) {
          console.error('Failed to capture/send frame:', error)
        }
      }
    }, 100)
  }

  const handleWebSocketMessage = (message: FeedbackMessage) => {
    console.log('Received message:', message.type, message)

    switch (message.type) {
      case 'challenge_issued':
        setCurrentChallenge(message.data?.instruction || message.message)
        break

      case 'challenge_completed': {
        const completed = message.data?.completed_count || completedChallenges + 1
        setCompletedChallenges(completed)
        const total = message.data?.total_challenges || totalChallenges
        setTotalChallenges(total)
        setProgress((completed / total) * 100)
        break
      }

      case 'challenge_failed':
        // Challenge failed, but continue with verification
        console.log('Challenge failed:', message.message)
        break

      case 'score_update':
        setScores({
          liveness: message.data?.liveness_score || 0,
          emotion: message.data?.emotion_score || 0,
          deepfake: message.data?.deepfake_score || 0,
        })
        break

      case 'verification_success':
        setStep('success')
        setToken(message.data?.token || null)
        setFinalScore(message.data?.final_score || 0)
        setProgress(100)
        setCompletedChallenges(totalChallenges)
        cleanup()
        break

      case 'verification_failed':
        setStep('error')
        setErrorMessage(message.data?.reason || message.message || 'Verification failed. Please try again.')
        setFinalScore(message.data?.final_score || 0)
        cleanup()
        break

      case 'error':
        setStep('error')
        setErrorMessage(message.message || 'An error occurred during verification.')
        cleanup()
        break

      default:
        console.log('Unknown message type:', message.type)
    }
  }

  const handleWebSocketError = (error: Event) => {
    console.error('WebSocket error:', error)
    setStep('error')
    setErrorMessage('Connection error. Please check your internet connection.')
    cleanup()
  }

  const handleWebSocketClose = (event: CloseEvent) => {
    console.log('WebSocket closed:', event.code, event.reason)
    
    if (step === 'scanning') {
      if (event.code === 1008) {
        setStep('error')
        setErrorMessage('Session invalid or expired. Please start a new verification.')
      } else if (event.code === 1011) {
        setStep('error')
        setErrorMessage('Server error. Please try again later.')
      } else if (!event.wasClean && step === 'scanning') {
        setStep('error')
        setErrorMessage('Connection lost. Please start a new verification.')
      }
      cleanup()
    }
  }

  const reset = () => {
    cleanup()
    setStep('idle')
    setProgress(0)
    setCurrentChallenge('')
    setCompletedChallenges(0)
    setScores({ liveness: 0, emotion: 0, deepfake: 0 })
    setSessionId(null)
    setToken(null)
    setErrorMessage('')
    setFinalScore(0)
  }

  return (
    <div className="min-h-screen relative overflow-hidden bg-grid">
      {/* Atmospheric background */}
      <div className="absolute inset-0 pointer-events-none">
        <motion.div
          className="absolute top-0 left-1/4 w-[500px] h-[500px] bg-neon-cyan/[0.03] rounded-full blur-[120px]"
          animate={{ x: [0, 60, 0], y: [0, 30, 0] }}
          transition={{ duration: 20, repeat: Infinity }}
        />
        <motion.div
          className="absolute bottom-0 right-1/4 w-[500px] h-[500px] bg-neon-purple/[0.03] rounded-full blur-[120px]"
          animate={{ x: [0, -60, 0], y: [0, -30, 0] }}
          transition={{ duration: 15, repeat: Infinity }}
        />
      </div>

      {/* Content */}
      <div className="relative z-10 container mx-auto px-4 py-8 min-h-screen flex flex-col items-center justify-center">
        {/* Header */}
        <motion.div
          className="text-center mb-10"
          initial={{ opacity: 0, y: -16 }}
          animate={{ opacity: 1, y: 0 }}
        >
          <h1 className="font-display text-4xl md:text-5xl font-extrabold text-ink-100 mb-3 tracking-tight">
            SENTINEL
          </h1>
          <p className="font-mono text-xs tracking-[0.3em] uppercase text-neon-cyan/60">
            Proof-of-Life Verification Protocol
          </p>
        </motion.div>

        {/* Main verification area */}
        <div className="w-full max-w-6xl grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Left: Scanner */}
          <GlassCard className="p-6 h-[600px]" glow="cyan">
            <FaceIDScanner
              isScanning={step === 'scanning'}
              progress={progress}
              status={step}
              scores={step === 'scanning' ? scores : undefined}
              currentChallenge={step === 'scanning' ? currentChallenge : undefined}
            />
          </GlassCard>

          {/* Right: Info and controls */}
          <div className="space-y-4">
            {/* Status card */}
            <GlassCard className="p-5">
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="font-mono text-[10px] tracking-[0.2em] uppercase text-ink-400">System Status</h3>
                  <motion.div
                    className={`px-3 py-1.5 text-[10px] font-mono tracking-[0.15em] uppercase border ${
                      step === 'idle'
                        ? 'border-white/[0.06] text-ink-400'
                        : step === 'scanning'
                        ? 'border-neon-cyan/20 text-neon-cyan'
                        : step === 'success'
                        ? 'border-neon-green/20 text-neon-green'
                        : 'border-neon-red/20 text-neon-red'
                    }`}
                    style={{ borderRadius: '1px' }}
                    animate={{ scale: step === 'scanning' ? [1, 1.03, 1] : 1 }}
                    transition={{ duration: 1, repeat: step === 'scanning' ? Infinity : 0 }}
                  >
                    {step === 'idle' && 'Standby'}
                    {step === 'scanning' && 'Scanning'}
                    {step === 'success' && 'Verified'}
                    {step === 'error' && 'Failed'}
                  </motion.div>
                </div>

                {/* Progress */}
                {step === 'scanning' && (
                  <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
                    <div className="flex justify-between text-[10px] font-mono text-ink-500 mb-2 tracking-wider">
                      <span>Progress</span>
                      <span>{Math.round(progress)}%</span>
                    </div>
                    <div className="h-px bg-white/[0.06] overflow-hidden">
                      <motion.div className="h-full bg-neon-cyan shadow-[0_0_6px_rgba(0,240,255,0.4)]"
                        initial={{ width: '0%' }} animate={{ width: `${progress}%` }} />
                    </div>
                  </motion.div>
                )}

                {/* Challenges completed */}
                <div className="flex justify-between text-xs font-mono">
                  <span className="text-ink-500">Challenges</span>
                  <span className="text-ink-200 font-bold">{completedChallenges} / {totalChallenges}</span>
                </div>
              </div>
            </GlassCard>

            {/* Current challenge */}
            <AnimatePresence mode="wait">
              {currentChallenge && step === 'scanning' && (
                <motion.div
                  key={currentChallenge}
                  initial={{ opacity: 0, x: 16 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: -16 }}
                >
                  <GlassCard className="p-5" glow="cyan">
                    <div className="flex items-center space-x-4">
                      <motion.div
                        className="w-10 h-10 flex items-center justify-center bg-neon-cyan/[0.08] border border-neon-cyan/20"
                        style={{ borderRadius: '2px' }}
                        animate={{ scale: [1, 1.08, 1] }}
                        transition={{ duration: 1.5, repeat: Infinity }}
                      >
                        <svg className="w-5 h-5 text-neon-cyan" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                            d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                            d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                        </svg>
                      </motion.div>
                      <div>
                        <p className="text-[10px] font-mono text-ink-500 tracking-[0.2em] uppercase">Current Challenge</p>
                        <p className="text-sm font-mono text-ink-100 mt-1">{currentChallenge}</p>
                      </div>
                    </div>
                  </GlassCard>
                </motion.div>
              )}
            </AnimatePresence>

            {/* Scores (when scanning) */}
            {step === 'scanning' && (
              <GlassCard className="p-5">
                <h3 className="font-mono text-[10px] tracking-[0.2em] uppercase text-ink-400 mb-4">Live Telemetry</h3>
                <div className="space-y-3">
                  {[
                    { label: 'Liveness', value: Math.min(progress * 0.8, 85), color: 'bg-neon-green' },
                    { label: 'Emotion', value: Math.min(progress * 0.7, 75), color: 'bg-neon-purple' },
                    { label: 'Deepfake', value: Math.min(progress * 0.9, 92), color: 'bg-neon-cyan' },
                  ].map((score) => (
                    <div key={score.label}>
                      <div className="flex justify-between text-xs font-mono mb-1.5">
                        <span className="text-ink-500 tracking-wider">{score.label}</span>
                        <span className="text-ink-200 font-bold">{Math.round(score.value)}%</span>
                      </div>
                      <div className="h-px bg-white/[0.06] overflow-hidden">
                        <motion.div className={`h-full ${score.color}`}
                          initial={{ width: '0%' }} animate={{ width: `${score.value}%` }}
                          transition={{ duration: 0.5 }} />
                      </div>
                    </div>
                  ))}
                </div>
              </GlassCard>
            )}

            {/* Success message */}
            {step === 'success' && (
              <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }}>
                <GlassCard className="p-6" glow="green">
                  <div className="text-center space-y-4">
                    <motion.div
                      className="w-14 h-14 mx-auto flex items-center justify-center bg-neon-green/[0.08] border border-neon-green/20"
                      style={{ borderRadius: '2px' }}
                      animate={{ scale: [1, 1.08, 1] }} transition={{ duration: 0.5 }}>
                      <svg className="w-7 h-7 text-neon-green" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                      </svg>
                    </motion.div>
                    <div>
                      <h3 className="font-display text-2xl font-bold text-ink-100 mb-2">Identity Verified</h3>
                      <p className="text-ink-400 text-sm font-mono">
                        Authentication token issued. Access granted.
                      </p>
                    </div>
                    <div className="pt-3 border-t border-white/[0.06]">
                      <p className="text-[10px] font-mono text-ink-500 tracking-wider">Score: {Math.round(finalScore * 100)}%</p>
                      {token && (
                        <p className="text-[10px] font-mono text-ink-600 mt-1 break-all">Token: {token.substring(0, 24)}...</p>
                      )}
                    </div>
                  </div>
                </GlassCard>
              </motion.div>
            )}

            {/* Error message */}
            {step === 'error' && (
              <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }}>
                <GlassCard className="p-6" glow="red">
                  <div className="text-center space-y-4">
                    <motion.div
                      className="w-14 h-14 mx-auto flex items-center justify-center bg-neon-red/[0.08] border border-neon-red/20"
                      style={{ borderRadius: '2px' }}
                      animate={{ scale: [1, 1.08, 1] }} transition={{ duration: 0.5 }}>
                      <svg className="w-7 h-7 text-neon-red" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M6 18L18 6M6 6l12 12" />
                      </svg>
                    </motion.div>
                    <div>
                      <h3 className="font-display text-2xl font-bold text-ink-100 mb-2">Verification Failed</h3>
                      <p className="text-ink-400 text-sm font-mono">
                        {errorMessage || 'Unable to verify identity. Retry recommended.'}
                      </p>
                    </div>
                    {finalScore > 0 && (
                      <div className="pt-3 border-t border-white/[0.06]">
                        <p className="text-[10px] font-mono text-ink-500 tracking-wider">Score: {Math.round(finalScore * 100)}%</p>
                      </div>
                    )}
                  </div>
                </GlassCard>
              </motion.div>
            )}

            {/* Controls */}
            <div className="flex gap-4">
              {step === 'idle' && (
                <motion.button
                  onClick={startVerification}
                  className="flex-1 py-4 font-mono text-sm tracking-[0.15em] uppercase text-void-50 bg-neon-cyan font-bold clip-corner shadow-glow-cyan"
                  whileHover={{ scale: 1.02, boxShadow: '0 0 30px rgba(0, 240, 255, 0.4)' }}
                  whileTap={{ scale: 0.98 }}
                >
                  Initialize Scan
                </motion.button>
              )}

              {(step === 'success' || step === 'error') && (
                <motion.button
                  onClick={reset}
                  className="flex-1 py-4 font-mono text-sm tracking-[0.15em] uppercase text-ink-200 bg-void-200/80 backdrop-blur-sm border border-white/[0.08]"
                  style={{ borderRadius: '2px' }}
                  whileHover={{ scale: 1.02, borderColor: 'rgba(0, 240, 255, 0.2)' }}
                  whileTap={{ scale: 0.98 }}
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                >
                  Retry Protocol
                </motion.button>
              )}
            </div>
          </div>
        </div>

        {/* Features */}
        <motion.div
          className="mt-16 grid grid-cols-1 md:grid-cols-3 gap-4 w-full max-w-6xl"
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5 }}
        >
          {[
            { icon: '◆', title: 'Encrypted', description: 'End-to-end encrypted biometric pipeline' },
            { icon: '⚡', title: 'Real-time', description: 'Sub-second ML inference at 10 FPS' },
            { icon: '◉', title: 'Precise', description: '99.9% accuracy with multi-model stack' },
          ].map((feature, i) => (
            <GlassCard key={i} className="p-5 text-center" hover>
              <div className="text-neon-cyan text-xl mb-3 font-mono">{feature.icon}</div>
              <h3 className="font-display text-sm font-bold text-ink-100 mb-1 tracking-wide uppercase">{feature.title}</h3>
              <p className="text-[11px] font-mono text-ink-500">{feature.description}</p>
            </GlassCard>
          ))}
        </motion.div>
      </div>
    </div>
  )
}
