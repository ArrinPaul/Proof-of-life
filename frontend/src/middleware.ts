import { authMiddleware } from '@clerk/nextjs'

export default authMiddleware({
  publicRoutes: ['/', '/sign-in(.*)', '/sign-up(.*)', '/verify(.*)', '/verify-glass(.*)'],
  ignoredRoutes: ['/api/webhook']
})

export const config = {
  matcher: ['/((?!.+\\.[\\w]+$|_next).*)', '/', '/(api|trpc)(.*)'],
}
