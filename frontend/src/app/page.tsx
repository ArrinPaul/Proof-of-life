import { auth } from '@clerk/nextjs'
import { redirect } from 'next/navigation'
import Link from 'next/link'

export default async function Home() {
  const { userId } = auth()
  
  if (userId) {
    redirect('/verify')
  }

  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-24 bg-gradient-to-b from-blue-50 to-white">
      <div className="text-center max-w-2xl">
        <h1 className="text-5xl font-bold mb-6 text-gray-900">
          Proof of Life Authentication
        </h1>
        <p className="text-xl text-gray-600 mb-8">
          Multi-factor liveness verification system with AI-powered deepfake detection
        </p>
        <div className="flex gap-4 justify-center">
          <Link 
            href="/sign-in"
            className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition"
          >
            Sign In
          </Link>
          <Link 
            href="/sign-up"
            className="px-6 py-3 bg-gray-200 text-gray-800 rounded-lg hover:bg-gray-300 transition"
          >
            Sign Up
          </Link>
        </div>
      </div>
    </main>
  )
}
