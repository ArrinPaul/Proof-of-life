'use client'

import { VerificationFeedback } from '@/types'
import { motion } from 'framer-motion'

interface FeedbackDisplayProps {
  feedback: VerificationFeedback[]
  currentScore?: number
  completedCount?: number
  totalChallenges?: number
}

export default function FeedbackDisplay({ 
  feedback, 
  currentScore = 0,
  completedCount = 0,
  totalChallenges = 0
}: FeedbackDisplayProps) {
  const latestFeedback = feedback[feedback.length - 1]

  const getFeedbackColor = (type: string) => {
    switch (type) {
      case 'challenge_completed':
      case 'verification_success':
        return 'bg-neon-green/[0.06] border-neon-green/20 text-neon-green'
      case 'challenge_failed':
      case 'verification_failed':
        return 'bg-neon-red/[0.06] border-neon-red/20 text-neon-red'
      case 'error':
        return 'bg-neon-red/[0.08] border-neon-red/30 text-neon-red'
      case 'score_update':
        return 'bg-neon-cyan/[0.06] border-neon-cyan/20 text-neon-cyan'
      default:
        return 'bg-white/[0.03] border-white/[0.06] text-ink-300'
    }
  }

  const getFeedbackIcon = (type: string) => {
    switch (type) {
      case 'challenge_completed':
      case 'verification_success':
        return '✓'
      case 'challenge_failed':
      case 'verification_failed':
        return '✗'
      case 'error':
        return '!'
      case 'score_update':
        return '◆'
      case 'challenge_issued':
        return '▶'
      default:
        return '·'
    }
  }

  return (
    <div className="space-y-4">
      {/* Challenge Progress */}
      {totalChallenges > 0 && (
        <div className="bg-void-200/80 border border-neon-cyan/20 p-5" style={{ borderRadius: '2px' }}>
          <div className="flex items-center justify-between mb-3">
            <span className="text-[10px] font-mono tracking-[0.2em] uppercase text-ink-400">Challenge Progress</span>
            <span className="font-mono text-lg font-bold text-neon-cyan">{completedCount}/{totalChallenges}</span>
          </div>
          <div className="flex gap-1.5">
            {Array.from({ length: totalChallenges }, (_, i) => (
              <div
                key={i}
                className={`h-2 flex-1 transition-all duration-300 ${
                  i < completedCount 
                    ? 'bg-neon-green shadow-[0_0_6px_rgba(0,255,136,0.4)]' 
                    : 'bg-white/[0.06]'
                }`}
                style={{ borderRadius: '1px' }}
              />
            ))}
          </div>
          <p className="text-[10px] font-mono text-ink-500 mt-2">
            {completedCount >= Math.ceil(totalChallenges / 2) 
              ? `✓ Minimum threshold reached (${Math.ceil(totalChallenges / 2)} required)`
              : `Need ${Math.ceil(totalChallenges / 2) - completedCount} more to pass`
            }
          </p>
        </div>
      )}

      {/* Score Display */}
      <div className="bg-void-200/80 border border-white/[0.06] p-5" style={{ borderRadius: '2px' }}>
        <div className="flex items-center justify-between mb-3">
          <span className="text-[10px] font-mono tracking-[0.2em] uppercase text-ink-400">Current Score</span>
          <span className="text-[10px] font-mono tracking-[0.15em] text-ink-500">Threshold: 0.70</span>
        </div>
        <div className="relative w-full h-px bg-white/[0.06] overflow-hidden mb-3">
          <motion.div 
            className={`absolute left-0 top-0 h-full transition-all duration-500 ${
              currentScore >= 0.7 ? 'bg-neon-green shadow-[0_0_8px_rgba(0,255,136,0.4)]' : 'bg-neon-cyan shadow-[0_0_8px_rgba(0,240,255,0.3)]'
            }`}
            style={{ width: `${currentScore * 100}%` }}
          />
        </div>
        <div className="text-right">
          <span className={`font-mono text-2xl font-bold ${
            currentScore >= 0.7 ? 'text-neon-green' : 'text-ink-200'
          }`}>
            {(currentScore * 100).toFixed(0)}%
          </span>
        </div>
      </div>

      {/* Latest Feedback */}
      {latestFeedback && (
        <motion.div
          className={`border p-4 ${getFeedbackColor(latestFeedback.type)}`}
          style={{ borderRadius: '2px' }}
          initial={{ opacity: 0, y: -8 }}
          animate={{ opacity: 1, y: 0 }}
          key={feedback.length}
        >
          <div className="flex items-start gap-3">
            <span className="font-mono text-sm font-bold mt-0.5">{getFeedbackIcon(latestFeedback.type)}</span>
            <div className="flex-1">
              <p className="font-mono text-sm">{latestFeedback.message}</p>
              {latestFeedback.data?.score !== undefined && (
                <p className="text-xs font-mono mt-1 opacity-70">
                  Score: {(latestFeedback.data.score * 100).toFixed(0)}%
                </p>
              )}
            </div>
          </div>
        </motion.div>
      )}

      {/* Feedback History */}
      <div className="bg-void-200/60 border border-white/[0.06] p-4 max-h-48 overflow-y-auto" style={{ borderRadius: '2px' }}>
        <h3 className="text-[10px] font-mono tracking-[0.2em] uppercase text-ink-500 mb-3">Activity Log</h3>
        <div className="space-y-1.5">
          {feedback.slice().reverse().map((item, index) => (
            <div key={index} className="flex items-start gap-2 text-xs font-mono">
              <span className="text-ink-500 mt-px">{getFeedbackIcon(item.type)}</span>
              <span className="text-ink-400">{item.message}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
