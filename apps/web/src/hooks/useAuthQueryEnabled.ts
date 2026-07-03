'use client';

import { useUserContext } from '@/contexts/UserContext';

/** True when platform auth has finished loading and the user is signed in. */
export function useAuthQueryEnabled(): boolean {
  const { authReady } = useUserContext();
  return authReady;
}

/** @deprecated Use useAuthQueryEnabled */
export function useClerkQueryEnabled(): boolean {
  return useAuthQueryEnabled();
}
