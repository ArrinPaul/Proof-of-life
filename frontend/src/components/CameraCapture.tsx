'use client'

import { useEffect, useRef, useState } from 'react'

interface CameraCaptureProps {
  onFrame?: (frameData: string) => void
  fps?: number
  isActive?: boolean
}

export default function CameraCapture({ 
  onFrame, 
  fps = 10,
  isActive = true 
}: CameraCaptureProps) {
  const videoRef = useRef<HTMLVideoElement>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const intervalRef = useRef<NodeJS.Timeout | null>(null)
  
  const [error, setError] = useState<string | null>(null)
  const [permissionGranted, setPermissionGranted] = useState(false)

  useEffect(() => {
    let mounted = true

    const startCamera = async () => {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          video: {
            width: { ideal: 640 },
            height: { ideal: 480 },
            facingMode: 'user'
          },
          audio: false
        })

        if (!mounted) {
          stream.getTracks().forEach(track => track.stop())
          return
        }

        streamRef.current = stream
        
        if (videoRef.current) {
          videoRef.current.srcObject = stream
          setPermissionGranted(true)
          setError(null)
        }
      } catch (err) {
        if (!mounted) return
        
        console.error('Camera access error:', err)
        setError('Camera access denied. Please grant camera permissions to continue.')
        setPermissionGranted(false)
      }
    }

    startCamera()

    return () => {
      mounted = false
      if (streamRef.current) {
        streamRef.current.getTracks().forEach(track => track.stop())
      }
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
      }
    }
  }, [])

  useEffect(() => {
    if (!isActive || !permissionGranted || !onFrame) {
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
        intervalRef.current = null
      }
      return
    }

    const captureFrame = () => {
      if (!videoRef.current || !canvasRef.current) return

      const video = videoRef.current
      const canvas = canvasRef.current
      const ctx = canvas.getContext('2d')

      if (!ctx || video.readyState !== video.HAVE_ENOUGH_DATA) return

      canvas.width = video.videoWidth
      canvas.height = video.videoHeight
      ctx.drawImage(video, 0, 0)

      const frameData = canvas.toDataURL('image/jpeg', 0.8)
      onFrame(frameData.split(',')[1]) // Send base64 without prefix
    }

    intervalRef.current = setInterval(captureFrame, 1000 / fps)

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
      }
    }
  }, [isActive, permissionGranted, onFrame, fps])

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center p-8 bg-neon-red/[0.06] border border-neon-red/20" style={{ borderRadius: '2px' }}>
        <svg className="w-14 h-14 text-neon-red mb-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
        </svg>
        <p className="text-neon-red text-center font-mono text-sm">{error}</p>
        <p className="text-ink-500 font-mono text-xs text-center mt-2">
          Check browser settings and reload
        </p>
      </div>
    )
  }

  return (
    <div className="relative">
      <video
        ref={videoRef}
        autoPlay
        playsInline
        muted
        className="w-full border border-white/[0.06]"
        style={{ borderRadius: '2px' }}
      />
      <canvas ref={canvasRef} className="hidden" />
      {!permissionGranted && (
        <div className="absolute inset-0 flex items-center justify-center bg-void-50/90 backdrop-blur-sm" style={{ borderRadius: '2px' }}>
          <div className="text-center">
            <div className="w-10 h-10 border border-neon-cyan/40 border-t-neon-cyan animate-spin mx-auto mb-4" style={{ borderRadius: '50%' }}></div>
            <p className="font-mono text-xs text-ink-400 tracking-widest uppercase">Requesting camera access</p>
          </div>
        </div>
      )}
    </div>
  )
}
