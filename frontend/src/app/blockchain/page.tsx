'use client'

import { useEffect, useState, useCallback } from 'react'
import Link from 'next/link'
import { motion, AnimatePresence } from 'framer-motion'

interface BlockData {
  index: number
  timestamp: number
  block_id: string
  previous_hash: string
  data: Record<string, any>
  nonce: string
  block_hash: string
  signature: string
}

interface ChainStats {
  total_blocks: number
  verification_blocks: number
  token_blocks: number
  verifications_passed: number
  verifications_failed: number
  pass_rate: number
  chain_hash: string | null
  genesis_timestamp: number | null
  latest_timestamp: number | null
}

interface IntegrityResult {
  valid: boolean
  block_count: number
  errors: string[]
  chain_hash: string | null
  verified_at: string
}

export default function BlockchainExplorer() {
  const [blocks, setBlocks] = useState<BlockData[]>([])
  const [stats, setStats] = useState<ChainStats | null>(null)
  const [integrity, setIntegrity] = useState<IntegrityResult | null>(null)
  const [selectedBlock, setSelectedBlock] = useState<BlockData | null>(null)
  const [loading, setLoading] = useState(true)
  const [verifying, setVerifying] = useState(false)
  const [publicKey, setPublicKey] = useState<string>('')

  const apiUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

  const fetchData = useCallback(async () => {
    try {
      const [statsRes, chainRes] = await Promise.all([
        fetch(`${apiUrl}/api/blockchain/stats`),
        fetch(`${apiUrl}/api/blockchain/chain?limit=100`),
      ])
      const statsData = await statsRes.json()
      const chainData = await chainRes.json()
      setStats(statsData)
      setBlocks(chainData.blocks || [])
    } catch (err) {
      console.error('Failed to fetch blockchain data:', err)
    } finally {
      setLoading(false)
    }
  }, [apiUrl])

  useEffect(() => {
    fetchData()
    // Auto-refresh every 10s
    const interval = setInterval(fetchData, 10000)
    return () => clearInterval(interval)
  }, [fetchData])

  const verifyChain = async () => {
    setVerifying(true)
    try {
      const res = await fetch(`${apiUrl}/api/blockchain/verify`)
      const data = await res.json()
      setIntegrity(data)
    } catch (err) {
      console.error('Failed to verify chain:', err)
    } finally {
      setVerifying(false)
    }
  }

  const fetchPublicKey = async () => {
    try {
      const res = await fetch(`${apiUrl}/api/blockchain/public-key`)
      const data = await res.json()
      setPublicKey(data.public_key)
    } catch (err) {
      console.error('Failed to fetch public key:', err)
    }
  }

  const formatTime = (ts: number) => {
    return new Date(ts * 1000).toLocaleString()
  }

  const truncateHash = (hash: string, len = 12) => {
    if (!hash) return '—'
    return hash.slice(0, len) + '...' + hash.slice(-6)
  }

  const blockTypeColor = (type: string) => {
    switch (type) {
      case 'genesis': return 'text-neon-purple'
      case 'verification_result': return 'text-neon-cyan'
      case 'token_issuance': return 'text-neon-amber'
      default: return 'text-ink-200'
    }
  }

  const blockTypeBorder = (type: string) => {
    switch (type) {
      case 'genesis': return 'border-neon-purple/30'
      case 'verification_result': return 'border-neon-cyan/20'
      case 'token_issuance': return 'border-neon-amber/20'
      default: return 'border-white/[0.06]'
    }
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-grid flex items-center justify-center">
        <div className="text-center">
          <div className="w-12 h-12 border-2 border-neon-cyan/30 border-t-neon-cyan rounded-full animate-spin mx-auto mb-4" />
          <p className="text-ink-200 font-mono text-sm tracking-wider uppercase">Loading Ledger...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-grid relative">
      {/* Background effects */}
      <div className="absolute inset-0 pointer-events-none">
        <div className="absolute top-0 left-1/3 w-[600px] h-[600px] bg-neon-purple/[0.03] rounded-full blur-[120px]" />
        <div className="absolute bottom-0 right-1/4 w-[500px] h-[500px] bg-neon-cyan/[0.04] rounded-full blur-[100px]" />
      </div>

      <div className="relative z-10 max-w-7xl mx-auto px-6 py-8">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <Link href="/" className="text-ink-200 hover:text-neon-cyan transition-colors text-xs font-mono tracking-wider uppercase mb-2 inline-block">
              &larr; Back to Sentinel
            </Link>
            <h1 className="font-display font-800 text-3xl sm:text-4xl text-ink-100 tracking-tight">
              Verification Ledger
            </h1>
            <p className="text-ink-200 text-sm mt-1 font-mono">
              Decentralized blockchain audit trail — tamper-proof & independently verifiable
            </p>
          </div>
          <div className="flex gap-3">
            <button
              onClick={verifyChain}
              disabled={verifying}
              className="px-5 py-2.5 clip-corner bg-neon-green/10 border border-neon-green/30 text-neon-green font-mono text-xs tracking-wider uppercase hover:bg-neon-green/20 transition-colors disabled:opacity-50"
            >
              {verifying ? 'Verifying...' : 'Verify Chain'}
            </button>
            <button
              onClick={fetchPublicKey}
              className="px-5 py-2.5 clip-corner bg-neon-purple/10 border border-neon-purple/30 text-neon-purple font-mono text-xs tracking-wider uppercase hover:bg-neon-purple/20 transition-colors"
            >
              Public Key
            </button>
          </div>
        </div>

        {/* Integrity Result Banner */}
        <AnimatePresence>
          {integrity && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className={`mb-6 p-4 border ${integrity.valid ? 'border-neon-green/30 bg-neon-green/[0.05]' : 'border-neon-red/30 bg-neon-red/[0.05]'}`}
              style={{ borderRadius: '2px' }}
            >
              <div className="flex items-center gap-3">
                <span className={`text-2xl ${integrity.valid ? 'text-neon-green' : 'text-neon-red'}`}>
                  {integrity.valid ? '✓' : '✗'}
                </span>
                <div>
                  <p className={`font-mono text-sm font-semibold ${integrity.valid ? 'text-neon-green' : 'text-neon-red'}`}>
                    {integrity.valid ? 'CHAIN INTEGRITY VERIFIED' : 'CHAIN INTEGRITY COMPROMISED'}
                  </p>
                  <p className="text-ink-200 text-xs font-mono mt-0.5">
                    {integrity.block_count} blocks verified • {integrity.verified_at}
                  </p>
                  {integrity.errors.length > 0 && (
                    <ul className="mt-2 space-y-1">
                      {integrity.errors.map((err, i) => (
                        <li key={i} className="text-neon-red text-xs font-mono">• {err}</li>
                      ))}
                    </ul>
                  )}
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Public Key Modal */}
        <AnimatePresence>
          {publicKey && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -10 }}
              className="mb-6 p-4 border border-neon-purple/20 bg-void-200/80 backdrop-blur-sm"
              style={{ borderRadius: '2px' }}
            >
              <div className="flex items-center justify-between mb-2">
                <span className="font-mono text-xs tracking-wider uppercase text-neon-purple">RSA Public Key (for independent verification)</span>
                <button onClick={() => setPublicKey('')} className="text-ink-200 hover:text-ink-100 text-xs">Close</button>
              </div>
              <pre className="text-[10px] text-ink-200 font-mono overflow-x-auto whitespace-pre-wrap break-all bg-void-50/50 p-3 border border-white/[0.04]" style={{ borderRadius: '2px' }}>
                {publicKey}
              </pre>
              <p className="text-ink-200/60 text-[10px] font-mono mt-2">
                Anyone can use this key to verify block signatures — no server trust required.
              </p>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Stats Grid */}
        {stats && (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-8">
            {[
              { label: 'Total Blocks', value: stats.total_blocks, color: 'text-ink-100' },
              { label: 'Verifications', value: stats.verification_blocks, color: 'text-neon-cyan' },
              { label: 'Passed', value: stats.verifications_passed, color: 'text-neon-green' },
              { label: 'Pass Rate', value: `${(stats.pass_rate * 100).toFixed(1)}%`, color: 'text-neon-amber' },
            ].map((stat) => (
              <div
                key={stat.label}
                className="bg-void-100/80 backdrop-blur-sm border border-white/[0.06] p-4"
                style={{ borderRadius: '2px' }}
              >
                <p className="text-[10px] font-mono tracking-[0.2em] uppercase text-ink-200 mb-1">{stat.label}</p>
                <p className={`text-2xl font-display font-800 ${stat.color}`}>{stat.value}</p>
              </div>
            ))}
          </div>
        )}

        {/* Chain Hash */}
        {stats?.chain_hash && (
          <div className="mb-6 bg-void-100/60 backdrop-blur-sm border border-white/[0.06] px-4 py-3 flex items-center gap-3" style={{ borderRadius: '2px' }}>
            <span className="text-[10px] font-mono tracking-[0.2em] uppercase text-ink-200 shrink-0">Chain Head</span>
            <code className="text-neon-cyan font-mono text-xs break-all">{stats.chain_hash}</code>
          </div>
        )}

        {/* Block List */}
        <div className="space-y-3">
          <h2 className="font-mono text-[10px] tracking-[0.2em] uppercase text-ink-200 mb-4">Block Explorer</h2>
          
          {blocks.length === 0 ? (
            <div className="text-center py-12 text-ink-200 font-mono text-sm">
              No blocks recorded yet. Complete a verification to add to the ledger.
            </div>
          ) : (
            blocks.map((block) => (
              <motion.div
                key={block.block_id}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                className={`bg-void-100/80 backdrop-blur-sm border ${blockTypeBorder(block.data.type)} p-4 cursor-pointer hover:bg-void-200/80 transition-colors`}
                style={{ borderRadius: '2px' }}
                onClick={() => setSelectedBlock(selectedBlock?.block_id === block.block_id ? null : block)}
              >
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <span className="font-mono text-lg font-bold text-ink-100">#{block.index}</span>
                    <span className={`font-mono text-[10px] tracking-wider uppercase ${blockTypeColor(block.data.type)}`}>
                      {block.data.type?.replace('_', ' ') || 'unknown'}
                    </span>
                    {block.data.passed !== undefined && (
                      <span className={`font-mono text-[10px] px-2 py-0.5 ${block.data.passed ? 'bg-neon-green/10 text-neon-green border border-neon-green/20' : 'bg-neon-red/10 text-neon-red border border-neon-red/20'}`}
                        style={{ borderRadius: '2px' }}>
                        {block.data.passed ? 'PASS' : 'FAIL'}
                      </span>
                    )}
                  </div>
                  <div className="text-right">
                    <p className="text-ink-200 text-xs font-mono">{formatTime(block.timestamp)}</p>
                    <p className="text-ink-200/50 text-[10px] font-mono mt-0.5">
                      {truncateHash(block.block_hash)}
                    </p>
                  </div>
                </div>

                {/* Expanded block detail */}
                <AnimatePresence>
                  {selectedBlock?.block_id === block.block_id && (
                    <motion.div
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: 'auto', opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      className="overflow-hidden"
                    >
                      <div className="mt-4 pt-4 border-t border-white/[0.06] space-y-3">
                        {/* Hash Chain Visualization */}
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                          <div>
                            <p className="text-[10px] font-mono tracking-wider uppercase text-ink-200 mb-1">Block Hash</p>
                            <code className="text-neon-cyan text-[11px] font-mono break-all">{block.block_hash}</code>
                          </div>
                          <div>
                            <p className="text-[10px] font-mono tracking-wider uppercase text-ink-200 mb-1">Previous Hash</p>
                            <code className="text-neon-purple text-[11px] font-mono break-all">{block.previous_hash}</code>
                          </div>
                        </div>

                        {/* Block Data */}
                        {block.data.scores && (
                          <div>
                            <p className="text-[10px] font-mono tracking-wider uppercase text-ink-200 mb-2">Verification Scores</p>
                            <div className="grid grid-cols-4 gap-2">
                              {Object.entries(block.data.scores).map(([key, val]) => (
                                <div key={key} className="bg-void-50/50 border border-white/[0.04] p-2" style={{ borderRadius: '2px' }}>
                                  <p className="text-[9px] font-mono uppercase text-ink-200">{key}</p>
                                  <p className={`text-sm font-mono font-bold ${Number(val) >= 0.7 ? 'text-neon-green' : 'text-neon-red'}`}>
                                    {(Number(val) * 100).toFixed(1)}%
                                  </p>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}

                        {block.data.session_id && (
                          <div>
                            <p className="text-[10px] font-mono tracking-wider uppercase text-ink-200 mb-1">Session</p>
                            <code className="text-ink-100 text-[11px] font-mono">{block.data.session_id}</code>
                          </div>
                        )}

                        {block.data.user_id && (
                          <div>
                            <p className="text-[10px] font-mono tracking-wider uppercase text-ink-200 mb-1">User</p>
                            <code className="text-ink-100 text-[11px] font-mono">{block.data.user_id}</code>
                          </div>
                        )}

                        {/* Signature */}
                        <div>
                          <p className="text-[10px] font-mono tracking-wider uppercase text-ink-200 mb-1">RSA Signature</p>
                          <code className="text-neon-amber/60 text-[10px] font-mono break-all line-clamp-2">{block.signature}</code>
                        </div>

                        <div className="text-[10px] font-mono text-ink-200/40">
                          Nonce: {block.nonce} &nbsp;•&nbsp; Block ID: {block.block_id}
                        </div>
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </motion.div>
            ))
          )}
        </div>

        {/* Footer */}
        <div className="mt-12 text-center">
          <p className="text-ink-200/40 font-mono text-[10px] tracking-wider">
            Each block is SHA-256 hashed and RSA-PSS signed • Chain is independently verifiable • No central trust required
          </p>
        </div>
      </div>
    </div>
  )
}
