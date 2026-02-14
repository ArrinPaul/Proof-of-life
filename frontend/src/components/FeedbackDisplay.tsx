'use client'

import { VerificationFeedback } from '@/types'

interface FeedbackDisplayProps {
  feedback: VerificationFeedback[]
  currentScore?: number
}

export default function FeedbackDisplay({ 
  feedback, 
  currentScore = 0 
}: FeedbackDisplayProps) {
  const latestFeedback = feedback[feedback.length - 1]

  const getFeedbackColor = (type: string) => {
    switch (type) {
      case 'challenge_completed':
      case 'verification_success':
        return 'bg-green-50 border-green-200 text-green-800'
      case 'challenge_failed':
      case 'verification_failed':
        return 'bg-red-50 border-red-200 text-red-800'
      case 'error':
        return 'bg-red-50 border-red-300 text-red-900'
      case 'score_update':
        return 'bg-blue-50 border-blue-200 text-blue-800'
      default:
        return 'bg-gray-50 border-gray-200 text-gray-800'
    }
  }

  const getFeedbackIcon = (type: string) => {
    switch (type) {
      case 'challenge_completed':
      case 'verification_success':
        return '✅'
      case 'challenge_failed':
      case 'verification_failed':
        return '❌'
      case 'error':
        return '⚠️'
      case 'score_update':
        return '📊'
      case 'challenge_issued':
        return '🎯'
      default:
        return 'ℹ️'
    }
  }

  return (
    <div className="space-y-4">
      {/* Score Display */}
      <div className="bg-white rounded-lg shadow p-6 border-2 border-gray-200">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-medium text-gray-600">Current Score</span>
          <span className="text-sm text-gray-500">Threshold: 0.70</span>
        </div>
        <div className="relative w-full h-4 bg-gray-200 rounded-full overflow-hidden">
          <div 
            className={`absolute left-0 top-0 h-full transition-all duration-500 ${
              currentScore >= 0.7 ? 'bg-green-500' : 'bg-blue-500'
            }`}
            style={{ width: `${currentScore * 100}%` }}
          />
        </div>
        <div className="text-right mt-1">
          <span className="text-2xl font-bold text-gray-900">
            {(currentScore * 100).toFixed(0)}%
          </span>
        </div>
      </div>

      {/* Latest Feedback */}
      {latestFeedback && (
        <div className={`rounded-lg p-4 border-2 ${getFeedbackColor(latestFeedback.type)}`}>
          <div className="flex items-start gap-3">
            <span className="text-2xl">{getFeedbackIcon(latestFeedback.type)}</span>
            <div className="flex-1">
              <p className="font-medium">{latestFeedback.message}</p>
              {latestFeedback.data?.score !== undefined && (
                <p className="text-sm mt-1">
                  Score: {(latestFeedback.data.score * 100).toFixed(0)}%
                </p>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Feedback History */}
      <div className="bg-white rounded-lg shadow p-4 max-h-48 overflow-y-auto">
        <h3 className="text-sm font-semibold text-gray-700 mb-3">Activity Log</h3>
        <div className="space-y-2">
          {feedback.slice().reverse().map((item, index) => (
            <div key={index} className="flex items-start gap-2 text-sm">
              <span>{getFeedbackIcon(item.type)}</span>
              <span className="text-gray-600">{item.message}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
