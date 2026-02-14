import { auth } from '@clerk/nextjs'
import { redirect } from 'next/navigation'
import Link from 'next/link'

export default async function Home() {
  const { userId } = auth()
  
  if (userId) {
    redirect('/verify')
  }

  return (
    <main className="relative min-h-screen flex flex-col items-center justify-center overflow-hidden bg-grid">
      {/* Radial glow backdrop */}
      <div className="absolute inset-0 pointer-events-none">
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[800px] bg-neon-cyan/[0.04] rounded-full blur-[120px]" />
        <div className="absolute top-0 right-0 w-[400px] h-[400px] bg-neon-purple/[0.06] rounded-full blur-[100px]" />
        <div className="absolute bottom-0 left-0 w-[300px] h-[300px] bg-neon-amber/[0.04] rounded-full blur-[80px]" />
      </div>

      {/* Content */}
      <div className="relative z-10 text-center max-w-3xl px-6">
        {/* Badge */}
        <div className="inline-flex items-center gap-2 px-4 py-1.5 mb-8 rounded-full border border-neon-cyan/20 bg-neon-cyan/[0.05] backdrop-blur-sm">
          <span className="w-2 h-2 rounded-full bg-neon-green animate-pulse" />
          <span className="text-xs font-mono tracking-widest uppercase text-neon-cyan/80">System Online</span>
        </div>

        {/* Hero heading */}
        <h1 className="font-display font-800 text-6xl sm:text-7xl lg:text-8xl tracking-tight mb-6 leading-[0.9]">
          <span className="block text-ink-100">SENTINEL</span>
          <span className="block text-glow-cyan text-neon-cyan mt-2 text-3xl sm:text-4xl lg:text-5xl font-mono font-300 tracking-[0.2em] uppercase">
            Proof of Life
          </span>
        </h1>

        {/* Description */}
        <p className="text-lg sm:text-xl text-ink-200 max-w-xl mx-auto mb-12 leading-relaxed">
          Neural biometric authentication with real-time liveness detection, 
          deepfake analysis, and cryptographic identity verification.
        </p>

        {/* CTA Buttons */}
        <div className="flex flex-col sm:flex-row gap-4 justify-center items-center">
          <Link
            href="/sign-in"
            className="group relative px-8 py-4 clip-corner bg-neon-cyan text-void-50 font-semibold text-lg tracking-wide
                       hover:shadow-glow-cyan-lg transition-all duration-300 w-full sm:w-auto text-center"
          >
            <span className="relative z-10 flex items-center justify-center gap-2">
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
              Initialize Auth
            </span>
          </Link>
          <Link
            href="/sign-up"
            className="px-8 py-4 clip-corner border border-ink-300/30 text-ink-200 font-medium text-lg tracking-wide
                       hover:border-neon-cyan/40 hover:text-neon-cyan hover:bg-neon-cyan/[0.03] transition-all duration-300 w-full sm:w-auto text-center"
          >
            Register Identity
          </Link>
          <Link
            href="/blockchain"
            className="px-8 py-4 clip-corner border border-neon-purple/30 text-neon-purple font-medium text-lg tracking-wide
                       hover:border-neon-purple/50 hover:bg-neon-purple/[0.05] transition-all duration-300 w-full sm:w-auto text-center"
          >
            <span className="flex items-center justify-center gap-2">
              <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z" />
              </svg>
              Verification Ledger
            </span>
          </Link>
        </div>
      </div>

      {/* Bottom indicators */}
      <div className="absolute bottom-8 left-0 right-0 flex justify-center gap-12 text-xs font-mono text-ink-300/60 tracking-widest uppercase">
        <div className="flex items-center gap-2">
          <div className="w-1.5 h-1.5 rounded-full bg-neon-green/60" />
          <span>ML Pipeline</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-1.5 h-1.5 rounded-full bg-neon-cyan/60" />
          <span>WebSocket</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-1.5 h-1.5 rounded-full bg-neon-amber/60" />
          <span>JWT Tokens</span>
        </div>
        <div className="flex items-center gap-2">
          <div className="w-1.5 h-1.5 rounded-full bg-neon-purple/60" />
          <span>Blockchain Ledger</span>
        </div>
      </div>
    </main>
  )
}
