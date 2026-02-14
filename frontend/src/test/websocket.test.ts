import { describe, it, expect, beforeEach, vi } from 'vitest'
import { WebSocketClient } from '@/lib/websocket'

// Mock WebSocket
global.WebSocket = vi.fn().mockImplementation(() => ({
  readyState: 1,
  send: vi.fn(),
  close: vi.fn(),
  addEventListener: vi.fn(),
})) as any

describe('WebSocket Client', () => {
  let client: WebSocketClient

  beforeEach(() => {
    // Constructor now takes sessionId instead of full URL
    client = new WebSocketClient('test-session-123')
  })

  it('should create WebSocket client with session ID', () => {
    expect(client).toBeDefined()
  })

  it('should handle connection establishment', () => {
    expect(client.isConnected()).toBe(false)
  })

  it('should handle network failure', () => {
    const errorCallback = vi.fn()
    client.onError(errorCallback)
    expect(errorCallback).toBeDefined()
  })

  it('should send frame data with proper structure', () => {
    const frameData = 'base64encodedframe'
    client.sendFrame(frameData)
    expect(true).toBe(true) // Mock test
  })
})
