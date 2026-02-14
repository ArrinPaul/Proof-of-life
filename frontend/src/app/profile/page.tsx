import { UserProfile } from '@clerk/nextjs'
import { auth } from '@clerk/nextjs'
import { redirect } from 'next/navigation'

export default async function ProfilePage() {
  const { userId } = auth()
  
  if (!userId) {
    redirect('/sign-in')
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50 p-4">
      <UserProfile 
        appearance={{
          elements: {
            rootBox: "mx-auto",
            card: "shadow-lg"
          }
        }}
      />
    </div>
  )
}
