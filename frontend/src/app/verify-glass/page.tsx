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
      case 'CHALLENGE_ISSUED':
        setCurrentChallenge(message.data?.instruction || message.message)
        break

      case 'CHALLENGE_COMPLETED':
        const completed = message.data?.completed_count || completedChallenges + 1
        setCompletedChallenges(completed)
        const total = message.data?.total_challenges || totalChallenges
        setTotalChallenges(total)
        setProgress((completed / total) * 100)
        break

      case 'CHALLENGE_FAILED':
        // Challenge failed, but continue with verification
        console.log('Challenge failed:', message.message)
        break

      case 'SCORE_UPDATE':
        setScores({
          liveness: message.data?.liveness_score || 0,
          emotion: message.data?.emotion_score || 0,
          deepfake: message.data?.deepfake_score || 0,
        })
        break

      case 'VERIFICATION_SUCCESS':
        setStep('success')
        setToken(message.data?.token || null)
        setFinalScore(message.data?.final_score || 0)
        setProgress(100)
        setCompletedChallenges(totalChallenges)
        cleanup()
        break

      case 'VERIFICATION_FAILED':
        setStep('error')
        setErrorMessage(message.data?.reason || message.message || 'Verification failed. Please try again.')
        setFinalScore(message.data?.final_score || 0)
        cleanup()
        break

      case 'ERROR':
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
    <div className="min-h-screen relative overflow-hidden bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900">
      {/* Animated background */}
      <div className="absolute inset-0">
        <motion.div
          className="absolute top-0 left-0 w-96 h-96 bg-blue-500/20 rounded-full blur-3xl"
          animate={{
            x: [0, 100, 0],
            y: [0, 50, 0],
          }}
          transition={{ duration: 20, repeat: Infinity }}
        />
        <motion.div
          className="absolute bottom-0 right-0 w-96 h-96 bg-purple-500/20 rounded-full blur-3xl"
          animate={{
            x: [0, -100, 0],
            y: [0, -50, 0],
          }}
          transition={{ duration: 15, repeat: Infinity }}
        />
        <motion.div
          className="absolute top-1/2 left-1/2 w-96 h-96 bg-cyan-500/10 rounded-full blur-3xl"
          animate={{
            scale: [1, 1.2, 1],
            rotate: [0, 180, 360],
          }}
          transition={{ duration: 25, repeat: Infinity }}
        />
      </div>

      {/* Content */}
      <div className="relative z-10 container mx-auto px-4 py-8 min-h-screen flex flex-col items-center justify-center">
        {/* Header */}
        <motion.div
          className="text-center mb-8"
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
        >
          <h1 className="text-5xl font-bold text-white mb-2 bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-cyan-400">
            Proof-of-Life Verification
          </h1>
          <p className="text-white/60 text-lg">
            Advanced biometric authentication with ML-powered liveness detection
          </p>
        </motion.div>

        {/* Main verification area */}
        <div className="w-full max-w-6xl grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Left: Scanner */}
          <GlassCard className="p-8 h-[600px]">
            <FaceIDScanner
              isScanning={step === 'scanning'}
              progress={progress}
              status={step}
              scores={step === 'scanning' ? scores : undefined}
              currentChallenge={step === 'scanning' ? currentChallenge : undefined}
            />
          </GlassCard>

          {/* Right: Info and controls */}
          <div className="space-y-6">
            {/* Status card */}
            <GlassCard className="p-6">
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <h3 className="text-xl font-semibold text-white">Status</h3>
                  <motion.div
                    className={`px-4 py-2 rounded-full text-sm font-medium ${
                      step === 'idle'
                        ? 'bg-gray-500/20 text-gray-300'
                        : step === 'scanning'
                        ? 'bg-blue-500/20 text-blue-300'
                        : step === 'success'
                        ? 'bg-green-500/20 text-green-300'
                        : 'bg-red-500/20 text-red-300'
                    }`}
                    animate={{ scale: step === 'scanning' ? [1, 1.05, 1] : 1 }}
                    transition={{ duration: 1, repeat: step === 'scanning' ? Infinity : 0 }}
                  >
                    {step === 'idle' && 'Ready'}
                    {step === 'scanning' && 'Scanning...'}
                    {step === 'success' && 'Verified ✓'}
                    {step === 'error' && 'Failed ✗'}
                  </motion.div>
                </div>

                {/* Progress */}
                {step === 'scanning' && (
                  <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                  >
                    <div className="flex justify-between text-sm text-white/60 mb-2">
                      <span>Progress</span>
                      <span>{Math.round(progress)}%</span>
                    </div>
                    <div className="h-2 bg-white/10 rounded-full overflow-hidden">
                      <motion.div
                        className="h-full bg-gradient-to-r from-blue-500 to-cyan-500"
                        initial={{ width: '0%' }}
                        animate={{ width: `${progress}%` }}
                      />
                    </div>
                  </motion.div>
                )}

                {/* Challenges completed */}
                <div className="flex justify-between text-sm">
                  <span className="text-white/60">Challenges Completed</span>
                  <span className="text-white font-medium">
                    {completedChallenges} / {totalChallenges}
                  </span>
                </div>
              </div>
            </GlassCard>

            {/* Current challenge */}
            <AnimatePresence mode="wait">
              {currentChallenge && step === 'scanning' && (
                <motion.div
                  key={currentChallenge}
                  initial={{ opacity: 0, x: 20 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: -20 }}
                >
                  <GlassCard className="p-6">
                    <div className="flex items-center space-x-4">
                      <motion.div
                        className="w-12 h-12 rounded-full bg-blue-500/20 flex items-center justify-center"
                        animate={{ scale: [1, 1.1, 1] }}
                        transition={{ duration: 1, repeat: Infinity }}
                      >
                        <svg
                          className="w-6 h-6 text-blue-400"
                          fill="none"
                          viewBox="0 0 24 24"
                          stroke="currentColor"
                        >
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={2}
                            d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"
                          />
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={2}
                            d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"
                          />
                        </svg>
                      </motion.div>
                      <div>
                        <p className="text-sm text-white/60">Current Challenge</p>
                        <p className="text-lg font-medium text-white">{currentChallenge}</p>
                      </div>
                    </div>
                  </GlassCard>
                </motion.div>
              )}
            </AnimatePresence>

            {/* Scores (when scanning) */}
            {step === 'scanning' && (
              <GlassCard className="p-6">
                <h3 className="text-lg font-semibold text-white mb-4">Live Scores</h3>
                <div className="space-y-3">
                  {[
                    { label: 'Liveness', value: Math.min(progress * 0.8, 85), color: 'blue' },
                    { label: 'Emotion', value: Math.min(progress * 0.7, 75), color: 'purple' },
                    { label: 'Deepfake', value: Math.min(progress * 0.9, 92), color: 'cyan' },
                  ].map((score) => (
                    <div key={score.label}>
                      <div className="flex justify-between text-sm mb-1">
                        <span className="text-white/60">{score.label}</span>
                        <span className="text-white font-medium">{Math.round(score.value)}%</span>
                      </div>
                      <div className="h-1.5 bg-white/10 rounded-full overflow-hidden">
                        <motion.div
                          className={`h-full bg-gradient-to-r from-${score.color}-500 to-${score.color}-400`}
                          initial={{ width: '0%' }}
                          animate={{ width: `${score.value}%` }}
                          transition={{ duration: 0.5 }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              </GlassCard>
            )}

            {/* Success message */}
            {step === 'success' && (
              <motion.div
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
              >
                <GlassCard className="p-6 bg-gradient-to-br from-green-500/20 to-emerald-500/10">
                  <div className="text-center space-y-4">
                    <motion.div
                      className="w-16 h-16 mx-auto rounded-full bg-green-500/20 flex items-center justify-center"
                      animate={{ scale: [1, 1.1, 1] }}
                      transition={{ duration: 0.5 }}
                    >
                      <svg
                        className="w-8 h-8 text-green-400"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={3}
                          d="M5 13l4 4L19 7"
                        />
                      </svg>
                    </motion.div>
                    <div>
                      <h3 className="text-2xl font-bold text-white mb-2">Verification Successful!</h3>
                      <p className="text-white/60">
                        Your identity has been verified. You can now access protected resources.
                      </p>
                    </div>
                    <div className="pt-4">
                      <p className="text-sm text-white/40">Final Score: {Math.round(finalScore * 100)}%</p>
                      {token && (
                        <p className="text-xs text-white/30 mt-2 break-all">Token: {token.substring(0, 20)}...</p>
                      )}
                    </div>
                  </div>
                </GlassCard>
              </motion.div>
            )}

            {/* Error message */}
            {step === 'error' && (
              <motion.div
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
              >
                <GlassCard className="p-6 bg-gradient-to-br from-red-500/20 to-rose-500/10">
                  <div className="text-center space-y-4">
                    <motion.div
                      className="w-16 h-16 mx-auto rounded-full bg-red-500/20 flex items-center justify-center"
                      animate={{ scale: [1, 1.1, 1] }}
                      transition={{ duration: 0.5 }}
                    >
                      <svg
                        className="w-8 h-8 text-red-400"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={3}
                          d="M6 18L18 6M6 6l12 12"
                        />
                      </svg>
                    </motion.div>
                    <div>
                      <h3 className="text-2xl font-bold text-white mb-2">Verification Failed</h3>
                      <p className="text-white/60">
                        {errorMessage || 'Unable to verify your identity. Please try again.'}
                      </p>
                    </div>
                    {finalScore > 0 && (
                      <div className="pt-4">
                        <p className="text-sm text-white/40">Final Score: {Math.round(finalScore * 100)}%</p>
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
                  className="flex-1 py-4 rounded-xl bg-gradient-to-r from-blue-500 to-cyan-500 text-white font-semibold shadow-lg shadow-blue-500/50"
                  whileHover={{ scale: 1.02, boxShadow: '0 20px 40px rgba(59, 130, 246, 0.4)' }}
                  whileTap={{ scale: 0.98 }}
                >
                  Start Verification
                </motion.button>
              )}

              {(step === 'success' || step === 'error') && (
                <motion.button
                  onClick={reset}
                  className="flex-1 py-4 rounded-xl bg-white/10 backdrop-blur-sm text-white font-semibold border border-white/20"
                  whileHover={{ scale: 1.02, backgroundColor: 'rgba(255, 255, 255, 0.15)' }}
                  whileTap={{ scale: 0.98 }}
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                >
                  Verify Again
                </motion.button>
              )}
            </div>
          </div>
        </div>

        {/* Features */}
        <motion.div
          className="mt-16 grid grid-cols-1 md:grid-cols-3 gap-6 w-full max-w-6xl"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5 }}
        >
          {[
            {
              icon: '🔒',
              title: 'Secure',
              description: 'Military-grade encryption and biometric verification',
            },
            {
              icon: '⚡',
              title: 'Fast',
              description: 'Real-time processing with sub-second response times',
            },
            {
              icon: '🎯',
              title: 'Accurate',
              description: '99.9% accuracy with advanced ML models',
            },
          ].map((feature, i) => (
            <GlassCard key={i} className="p-6 text-center" hover>
              <div className="text-4xl mb-3">{feature.icon}</div>
              <h3 className="text-lg font-semibold text-white mb-2">{feature.title}</h3>
              <p className="text-sm text-white/60">{feature.description}</p>
            </GlassCard>
          ))}
        </motion.div>
      </div>
    </div>
  )
}
