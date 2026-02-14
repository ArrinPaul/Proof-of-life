'use client'

import { Challenge } from '@/types'
import { useEffect, useState } from 'react'

interface ChallengeDisplayProps {
  challenge: Challenge | null
  timeRemaining?: number
}

const challengeIcons: Record<string, string> = {
  nod_up: '⬆️',
  nod_down: '⬇️',
  turn_left: '⬅️',
  turn_right: '➡️',
  tilt_left: '↖️',
  tilt_right: '↗️',
  open_mouth: '😮',
  close_eyes: '😑',
  raise_eyebrows: '😲',
  blink: '😉',
  smile: '😊',
  frown: '☹️',
  surprised: '😲',
  neutral: '😐',
  angry: '😠'
}

export default function ChallengeDisplay({ 
  challenge, 
  timeRemaining = 10 
}: ChallengeDisplayProps) {
  const [progress, setProgress] = useState(100)

  useEffect(() => {
    if (!challenge) return
    
    const percentage = (timeRemaining / challenge.timeoutSeconds) * 100
    setProgress(percentage)
  }, [timeRemaining, challenge])

  if (!challenge) {
    return (
      <div className="bg-gray-100 rounded-lg p-8 text-center">
        <p className="text-gray-500">Waiting for challenge...</p>
      </div>
    )
  }

  const icon = challengeIcons[challenge.instruction.toLowerCase().replace(/\s+/g, '_')] || '👤'

  return (
    <div className="bg-white rounded-lg shadow-lg p-8 border-2 border-blue-500">
      <div className="text-center mb-6">
        <div className="text-6xl mb-4 animate-bounce">{icon}</div>
        <h2 className="text-2xl font-bold text-gray-900 mb-2">
          {challenge.instruction}
        </h2>
        <p className="text-gray-600">
          {challenge.type === 'gesture' ? 'Perform the gesture' : 'Show the expression'}
        </p>
      </div>

      <div className="relative w-full h-3 bg-gray-200 rounded-full overflow-hidden">
        <div 
          className={`absolute left-0 top-0 h-full transition-all duration-1000 ${
            progress > 50 ? 'bg-green-500' : progress > 25 ? 'bg-yellow-500' : 'bg-red-500'
          }`}
          style={{ width: `${progress}%` }}
        />
      </div>
      
      <div className="text-center mt-4">
        <span className="text-2xl font-bold text-gray-700">
          {Math.ceil(timeRemaining)}s
        </span>
      </div>
    </div>
  )
}
