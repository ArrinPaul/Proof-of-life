import type { Metadata } from 'next'
import { ClerkProvider } from '@clerk/nextjs'
import './globals.css'

export const metadata: Metadata = {
  title: 'SENTINEL — Proof of Life',
  description: 'Neural biometric authentication with ML-powered liveness detection',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <ClerkProvider
      appearance={{
        variables: {
          colorPrimary: '#00f0ff',
          colorBackground: '#0e1117',
          colorInputBackground: '#161b26',
          colorInputText: '#e8ecf4',
          colorText: '#e8ecf4',
          colorTextSecondary: '#8896b0',
          borderRadius: '8px',
          fontFamily: 'Outfit, sans-serif',
        },
        elements: {
          card: 'bg-[#0e1117] border border-white/10 shadow-[0_0_20px_rgba(0,240,255,0.08)]',
          headerTitle: 'text-[#e8ecf4]',
          headerSubtitle: 'text-[#8896b0]',
          formButtonPrimary: 'bg-[#00f0ff] text-[#08090d] hover:bg-[#00d4e0]',
          footerActionLink: 'text-[#00f0ff] hover:text-[#00d4e0]',
          formFieldInput: 'bg-[#161b26] border-white/10 text-[#e8ecf4]',
          formFieldLabel: 'text-[#8896b0]',
          identityPreview: 'bg-[#161b26] border-white/10',
          userButtonPopoverCard: 'bg-[#0e1117] border border-white/10',
          userButtonPopoverActionButton: 'text-[#e8ecf4] hover:bg-white/5',
        },
      }}
    >
      <html lang="en" className="dark">
        <body className="bg-void-50 text-ink-100 font-body antialiased">{children}</body>
      </html>
    </ClerkProvider>
  )
}
