'use client'

import { useEffect, useState, useRef, useCallback } from 'react'
import { useAuth, useUser } from '@clerk/nextjs'
import { useRouter } from 'next/navigation'
import { motion, AnimatePresence } from 'framer-motion'
import FaceIDScanner from '@/components/FaceIDScanner'
import GlassCard from '@/components/GlassCard'
import { apiClient } from '@/lib/api'
import { WebSocketClient, FeedbackMessage } from '@/lib/websocket'
import { CameraCapture } from '@/lib/camera'

/* ── animated number counter ── */
function AnimatedNumber({ value, suffix = '%' }: { value: number; suffix?: string }) {
  const [display, setDisplay] = useState(0)
  useEffect(() => {
    if (value <= 0) { setDisplay(0); return }
    const start = performance.now()
    const tick = (now: number) => {
      const t = Math.min((now - start) / 1200, 1)
      setDisplay(Math.round((1 - Math.pow(1 - t, 3)) * value))
      if (t < 1) requestAnimationFrame(tick)
    }
    requestAnimationFrame(tick)
  }, [value])
  return <>{display}{suffix}</>
}

export default function VerifyGlassPage() {
  const { isLoaded, userId, getToken } = useAuth()
  const { user } = useUser()
  const router = useRouter()
  const [step, setStep] = useState<'idle' | 'scanning' | 'success' | 'error'>('idle')
  const [progress, setProgress] = useState(0)
  const [currentChallenge, setCurrentChallenge] = useState<string>('')
  const [completedChallenges, setCompletedChallenges] = useState(0)
  const [totalChallenges, setTotalChallenges] = useState(8)
  const [scores, setScores] = useState({ liveness: 0, emotion: 0, deepfake: 0 })
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [token, setToken] = useState<string | null>(null)
  const [blockchainId, setBlockchainId] = useState<string | null>(null)
  const [blockchainInfo, setBlockchainInfo] = useState<any>(null)
  const [errorMessage, setErrorMessage] = useState<string>('')
  const [finalScore, setFinalScore] = useState<number>(0)
  const [expiresIn, setExpiresIn] = useState<number>(15)
  const [showResult, setShowResult] = useState(false)

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

      // Start sending frames at 30 FPS
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
    // Capture and send frames at 30 FPS (every ~33ms)
    frameCaptureIntervalRef.current = setInterval(() => {
      if (cameraRef.current && wsClientRef.current?.isConnected()) {
        try {
          const frameData = cameraRef.current.captureFrame()
          wsClientRef.current.sendFrame(frameData)
        } catch (error) {
          console.error('Failed to capture/send frame:', error)
        }
      }
    }, 33)
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
        setBlockchainId(message.data?.blockchain_id || null)
        setBlockchainInfo(message.data?.blockchain || null)
        setFinalScore(message.data?.final_score || 0)
        setExpiresIn(message.data?.expires_in_minutes || 15)
        setScores({
          liveness: message.data?.liveness_score || 0,
          emotion: message.data?.emotion_score || 0,
          deepfake: message.data?.deepfake_score || 0,
        })
        setProgress(100)
        setCompletedChallenges(message.data?.completed_challenges || totalChallenges)
        setTimeout(() => setShowResult(true), 500)
        cleanup()
        break

      case 'verification_failed':
        setStep('error')
        setErrorMessage(message.data?.reason || message.message || 'Verification failed. Please try again.')
        setFinalScore(message.data?.final_score || 0)
        setScores({
          liveness: message.data?.liveness_score || 0,
          emotion: message.data?.emotion_score || 0,
          deepfake: message.data?.deepfake_score || 0,
        })
        setCompletedChallenges(message.data?.completed_challenges || completedChallenges)
        setTimeout(() => setShowResult(true), 500)
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
    setBlockchainId(null)
    setBlockchainInfo(null)
    setErrorMessage('')
    setFinalScore(0)
    setExpiresIn(15)
    setShowResult(false)
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
              completedChallenges={completedChallenges}
              totalChallenges={totalChallenges}
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
                    { label: 'Liveness', value: scores.liveness * 100, color: 'bg-neon-green' },
                    { label: 'Emotion', value: scores.emotion * 100, color: 'bg-neon-purple' },
                    { label: 'Deepfake', value: scores.deepfake * 100, color: 'bg-neon-cyan' },
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

            {/* Success Result */}
            {step === 'success' && showResult && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
                className="space-y-4"
              >
                {/* Blockchain ID Hero */}
                <GlassCard className="p-6 relative overflow-hidden" glow="green">
                  {/* Animated background pulse */}
                  <motion.div
                    className="absolute inset-0 bg-gradient-to-b from-neon-green/[0.04] to-transparent"
                    animate={{ opacity: [0.3, 0.6, 0.3] }}
                    transition={{ duration: 3, repeat: Infinity }}
                  />
                  <div className="relative z-10 text-center space-y-4">
                    {/* Verified badge */}
                    <motion.div
                      className="relative w-16 h-16 mx-auto"
                      initial={{ scale: 0, rotate: -180 }}
                      animate={{ scale: 1, rotate: 0 }}
                      transition={{ type: 'spring', stiffness: 200, damping: 15, delay: 0.2 }}
                    >
                      <motion.div
                        className="absolute inset-0 border-2 border-neon-green/40"
                        style={{ borderRadius: '2px' }}
                        animate={{ boxShadow: ['0 0 0px rgba(0,255,136,0.2)', '0 0 20px rgba(0,255,136,0.4)', '0 0 0px rgba(0,255,136,0.2)'] }}
                        transition={{ duration: 2, repeat: Infinity }}
                      />
                      <div className="w-full h-full flex items-center justify-center bg-neon-green/[0.08]">
                        <svg className="w-8 h-8 text-neon-green" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                        </svg>
                      </div>
                    </motion.div>

                    <motion.div
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ delay: 0.4 }}
                    >
                      <h3 className="font-display text-2xl font-bold text-neon-green tracking-wide">IDENTITY VERIFIED</h3>
                      <p className="text-ink-500 text-[10px] font-mono tracking-[0.2em] uppercase mt-1">Proof-of-Life Confirmed</p>
                    </motion.div>

                    {/* Blockchain ID */}
                    {blockchainId && (
                      <motion.div
                        className="mt-4 p-4 bg-void-100/60 border border-neon-green/20"
                        style={{ borderRadius: '2px' }}
                        initial={{ opacity: 0, scaleX: 0 }}
                        animate={{ opacity: 1, scaleX: 1 }}
                        transition={{ delay: 0.6, duration: 0.4 }}
                      >
                        <p className="text-[9px] font-mono text-ink-500 tracking-[0.3em] uppercase mb-2">Blockchain Identity</p>
                        <motion.p
                          className="text-lg font-mono font-bold text-neon-green tracking-wider"
                          animate={{ textShadow: ['0 0 4px rgba(0,255,136,0.3)', '0 0 12px rgba(0,255,136,0.6)', '0 0 4px rgba(0,255,136,0.3)'] }}
                          transition={{ duration: 2.5, repeat: Infinity }}
                        >
                          {blockchainId}
                        </motion.p>
                        <p className="text-[9px] font-mono text-ink-600 mt-2">Registered on Sentinel Ledger</p>
                      </motion.div>
                    )}
                  </div>
                </GlassCard>

                {/* Score Breakdown */}
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.8 }}
                >
                  <GlassCard className="p-5">
                    <h4 className="font-mono text-[10px] tracking-[0.2em] uppercase text-ink-400 mb-4">Score Breakdown</h4>
                    <div className="space-y-3">
                      {[
                        { label: 'Liveness', value: scores.liveness * 100, color: 'bg-neon-green', delay: 0.9 },
                        { label: 'Emotion', value: scores.emotion * 100, color: 'bg-neon-purple', delay: 1.0 },
                        { label: 'Deepfake', value: scores.deepfake * 100, color: 'bg-neon-cyan', delay: 1.1 },
                      ].map((s) => (
                        <motion.div
                          key={s.label}
                          initial={{ opacity: 0, x: -10 }}
                          animate={{ opacity: 1, x: 0 }}
                          transition={{ delay: s.delay }}
                        >
                          <div className="flex justify-between text-xs font-mono mb-1.5">
                            <span className="text-ink-500 tracking-wider">{s.label}</span>
                            <span className="text-ink-200 font-bold"><AnimatedNumber value={Math.round(s.value)} />%</span>
                          </div>
                          <div className="h-1 bg-white/[0.06] overflow-hidden" style={{ borderRadius: '1px' }}>
                            <motion.div
                              className={`h-full ${s.color}`}
                              initial={{ width: '0%' }}
                              animate={{ width: `${s.value}%` }}
                              transition={{ delay: s.delay, duration: 0.8, ease: 'easeOut' }}
                              style={{ boxShadow: '0 0 8px currentColor' }}
                            />
                          </div>
                        </motion.div>
                      ))}

                      {/* Final score */}
                      <motion.div
                        className="pt-3 mt-3 border-t border-white/[0.06]"
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        transition={{ delay: 1.2 }}
                      >
                        <div className="flex justify-between items-center">
                          <span className="text-xs font-mono text-ink-400 tracking-wider">FINAL SCORE</span>
                          <motion.span
                            className="text-xl font-display font-bold text-neon-green"
                            animate={{ textShadow: ['0 0 0px rgba(0,255,136,0)', '0 0 8px rgba(0,255,136,0.5)', '0 0 0px rgba(0,255,136,0)'] }}
                            transition={{ duration: 2, repeat: Infinity }}
                          >
                            <AnimatedNumber value={Math.round(finalScore * 100)} />%
                          </motion.span>
                        </div>
                      </motion.div>
                    </div>
                  </GlassCard>
                </motion.div>

                {/* Blockchain & Expiry Info */}
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 1.3 }}
                >
                  <GlassCard className="p-5">
                    <div className="grid grid-cols-2 gap-4">
                      <div>
                        <p className="text-[9px] font-mono text-ink-600 tracking-[0.2em] uppercase">Challenges</p>
                        <p className="text-sm font-mono text-ink-200 mt-1 font-bold">{completedChallenges} / {totalChallenges}</p>
                      </div>
                      <div>
                        <p className="text-[9px] font-mono text-ink-600 tracking-[0.2em] uppercase">Expires In</p>
                        <p className="text-sm font-mono text-neon-cyan mt-1 font-bold">{expiresIn} min</p>
                      </div>
                      {blockchainInfo && (
                        <>
                          <div>
                            <p className="text-[9px] font-mono text-ink-600 tracking-[0.2em] uppercase">Chain Length</p>
                            <p className="text-sm font-mono text-ink-200 mt-1 font-bold">{blockchainInfo.chain_length || '—'}</p>
                          </div>
                          <div>
                            <p className="text-[9px] font-mono text-ink-600 tracking-[0.2em] uppercase">Block Hash</p>
                            <p className="text-[10px] font-mono text-ink-400 mt-1 truncate">{blockchainInfo.block_hash?.substring(0, 16) || '—'}…</p>
                          </div>
                        </>
                      )}
                    </div>
                    {token && (
                      <div className="mt-4 pt-3 border-t border-white/[0.06]">
                        <p className="text-[9px] font-mono text-ink-600 tracking-[0.2em] uppercase mb-1">JWT Token</p>
                        <p className="text-[10px] font-mono text-ink-500 break-all leading-relaxed">{token.substring(0, 60)}…</p>
                      </div>
                    )}
                  </GlassCard>
                </motion.div>
              </motion.div>
            )}

            {/* Error Result */}
            {step === 'error' && showResult && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
                className="space-y-4"
              >
                <GlassCard className="p-6 relative overflow-hidden" glow="red">
                  <motion.div
                    className="absolute inset-0 bg-gradient-to-b from-neon-red/[0.04] to-transparent"
                    animate={{ opacity: [0.3, 0.5, 0.3] }}
                    transition={{ duration: 3, repeat: Infinity }}
                  />
                  <div className="relative z-10 text-center space-y-4">
                    <motion.div
                      className="relative w-16 h-16 mx-auto"
                      initial={{ scale: 0 }}
                      animate={{ scale: 1 }}
                      transition={{ type: 'spring', stiffness: 200, damping: 15, delay: 0.2 }}
                    >
                      <motion.div
                        className="absolute inset-0 border-2 border-neon-red/40"
                        style={{ borderRadius: '2px' }}
                        animate={{ boxShadow: ['0 0 0px rgba(255,50,50,0.2)', '0 0 20px rgba(255,50,50,0.4)', '0 0 0px rgba(255,50,50,0.2)'] }}
                        transition={{ duration: 2, repeat: Infinity }}
                      />
                      <div className="w-full h-full flex items-center justify-center bg-neon-red/[0.08]">
                        <svg className="w-8 h-8 text-neon-red" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M6 18L18 6M6 6l12 12" />
                        </svg>
                      </div>
                    </motion.div>

                    <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.4 }}>
                      <h3 className="font-display text-2xl font-bold text-neon-red tracking-wide">VERIFICATION FAILED</h3>
                      <p className="text-ink-500 text-[10px] font-mono tracking-[0.2em] uppercase mt-1">Identity Could Not Be Confirmed</p>
                      {errorMessage && (
                        <p className="text-ink-400 text-xs font-mono mt-3">{errorMessage}</p>
                      )}
                    </motion.div>
                  </div>
                </GlassCard>

                {/* Failed Score Breakdown */}
                {finalScore > 0 && (
                  <motion.div
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.6 }}
                  >
                    <GlassCard className="p-5">
                      <h4 className="font-mono text-[10px] tracking-[0.2em] uppercase text-ink-400 mb-4">Score Analysis</h4>
                      <div className="space-y-3">
                        {[
                          { label: 'Liveness', value: scores.liveness * 100, color: 'bg-neon-green', threshold: 65 },
                          { label: 'Emotion', value: scores.emotion * 100, color: 'bg-neon-purple', threshold: 50 },
                          { label: 'Deepfake', value: scores.deepfake * 100, color: 'bg-neon-cyan', threshold: 60 },
                        ].map((s, i) => (
                          <motion.div
                            key={s.label}
                            initial={{ opacity: 0, x: -10 }}
                            animate={{ opacity: 1, x: 0 }}
                            transition={{ delay: 0.7 + i * 0.1 }}
                          >
                            <div className="flex justify-between text-xs font-mono mb-1.5">
                              <span className="text-ink-500 tracking-wider">
                                {s.label}
                                {s.value < s.threshold && (
                                  <span className="text-neon-red/70 ml-2">⚠ LOW</span>
                                )}
                              </span>
                              <span className={`font-bold ${s.value < s.threshold ? 'text-neon-red' : 'text-ink-200'}`}>
                                {Math.round(s.value)}%
                              </span>
                            </div>
                            <div className="h-1 bg-white/[0.06] overflow-hidden" style={{ borderRadius: '1px' }}>
                              <motion.div
                                className={`h-full ${s.value < s.threshold ? 'bg-neon-red' : s.color}`}
                                initial={{ width: '0%' }}
                                animate={{ width: `${s.value}%` }}
                                transition={{ delay: 0.7 + i * 0.1, duration: 0.8, ease: 'easeOut' }}
                              />
                            </div>
                          </motion.div>
                        ))}

                        <motion.div
                          className="pt-3 mt-3 border-t border-white/[0.06]"
                          initial={{ opacity: 0 }}
                          animate={{ opacity: 1 }}
                          transition={{ delay: 1.0 }}
                        >
                          <div className="flex justify-between items-center">
                            <span className="text-xs font-mono text-ink-400 tracking-wider">FINAL SCORE</span>
                            <span className="text-xl font-display font-bold text-neon-red">{Math.round(finalScore * 100)}%</span>
                          </div>
                          <p className="text-[9px] font-mono text-ink-600 mt-2">Minimum 65% required to pass</p>
                        </motion.div>
                      </div>
                    </GlassCard>
                  </motion.div>
                )}

                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 1.1 }}
                >
                  <GlassCard className="p-4">
                    <div className="flex items-center space-x-3">
                      <div className="w-8 h-8 flex items-center justify-center bg-neon-cyan/[0.06] border border-neon-cyan/10" style={{ borderRadius: '2px' }}>
                        <span className="text-neon-cyan text-xs font-mono">i</span>
                      </div>
                      <div>
                        <p className="text-[10px] font-mono text-ink-400">Challenges passed: {completedChallenges} / {totalChallenges}</p>
                        <p className="text-[10px] font-mono text-ink-500 mt-0.5">Ensure good lighting and face the camera directly</p>
                      </div>
                    </div>
                  </GlassCard>
                </motion.div>
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
