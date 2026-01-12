import { clerkMiddleware } from '@clerk/nextjs/server';

export default clerkMiddleware(); // must be default export

export const config = {
  // run middleware on all pages except Next.js internals
  matcher: ['/((?!_next/static|_next/image|favicon.ico).*)'],
};
