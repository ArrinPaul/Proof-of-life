/**
 * WebSocket client for real-time communication with backend
 * Handles bidirectional real-time communication for proof-of-life verification
 */

export interface FeedbackMessage {
  type: string
  message: string
  data?: any
}

export class WebSocketClient {
  private ws: WebSocket | null = null
  private sessionId: string
  private wsBaseUrl: string
  private onMessageCallback?: (message: FeedbackMessage) => void
  private onErrorCallback?: (error: Event) => void
  private onCloseCallback?: (event: CloseEvent) => void
  private reconnectAttempted: boolean = false

  constructor(sessionId: string) {
    this.sessionId = sessionId
    // Read WebSocket base URL from environment variable
    this.wsBaseUrl = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000'
  }

  /**
   * Establish WebSocket connection to backend
   * Constructs URL from NEXT_PUBLIC_WS_URL and session_id
   */
  connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      try {
        // Construct WebSocket URL: ws://localhost:8000/ws/verify/{session_id}
        const url = `${this.wsBaseUrl}/ws/verify/${this.sessionId}`
        this.ws = new WebSocket(url)

        this.ws.onopen = () => {
          console.log('WebSocket connected to:', url)
          resolve()
        }

        this.ws.onmessage = (event) => {
          try {
            // Parse incoming messages as JSON
            const message: FeedbackMessage = JSON.parse(event.data)
            this.onMessageCallback?.(message)
          } catch (error) {
            console.error('Failed to parse WebSocket message:', error)
          }
        }

        this.ws.onerror = (error) => {
          console.error('WebSocket error:', error)
          this.onErrorCallback?.(error)
        }

        this.ws.onclose = (event) => {
          console.log('WebSocket closed with code:', event.code)
          
          // Implement single reconnection attempt on unexpected disconnect
          if (!event.wasClean && !this.reconnectAttempted && event.code !== 1000) {
            console.log('Attempting to reconnect...')
            this.reconnectAttempted = true
            setTimeout(() => {
              this.connect().catch((error) => {
                console.error('Reconnection failed:', error)
                this.onCloseCallback?.(event)
              })
            }, 2000)
          } else {
            this.onCloseCallback?.(event)
          }
        }
      } catch (error) {
        reject(error)
      }
    })
  }

  /**
   * Send video frame to backend
   * Sends message as JSON string with type "video_frame" and frame data
   */
  sendFrame(frameData: string): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      const message = {
        type: 'video_frame',
        frame: frameData,
        timestamp: Date.now()
      }
      this.ws.send(JSON.stringify(message))
    } else {
      console.error('WebSocket is not connected, cannot send frame')
    }
  }

  /**
   * Send generic message to backend
   */
  send(data: any): void {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data))
    } else {
      console.error('WebSocket is not connected')
    }
  }

  /**
   * Disconnect and close WebSocket connection
   */
  disconnect(): void {
    if (this.ws) {
      this.ws.close(1000, 'Client disconnect')
      this.ws = null
    }
  }

  /**
   * Register message event handler
   */
  onMessage(callback: (message: FeedbackMessage) => void): void {
    this.onMessageCallback = callback
  }

  /**
   * Register error event handler
   */
  onError(callback: (error: Event) => void): void {
    this.onErrorCallback = callback
  }

  /**
   * Register close event handler
   */
  onClose(callback: (event: CloseEvent) => void): void {
    this.onCloseCallback = callback
  }

  /**
   * Check if WebSocket is currently connected
   */
  isConnected(): boolean {
    return this.ws !== null && this.ws.readyState === WebSocket.OPEN
  }
}
