'use client';

import { useSessionQueryEnabled } from '@/hooks/usePlatformSession';

/** True when platform JWT is available — enables authenticated API queries. */
export function useAuthQueryEnabled(): boolean {
  return useSessionQueryEnabled();
}

/** @deprecated Use useAuthQueryEnabled */
export function useClerkQueryEnabled(): boolean {
  return useAuthQueryEnabled();
}
