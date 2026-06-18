'use client';

import { useAuth } from '@clerk/nextjs';

/** True when Clerk has finished loading and the user is signed in. */
export function useClerkQueryEnabled(): boolean {
  const { isLoaded, isSignedIn } = useAuth();
  return isLoaded && !!isSignedIn;
}
