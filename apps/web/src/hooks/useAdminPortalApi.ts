'use client';

import { useEffect } from 'react';
import { apiClient } from '@/lib/api-client';
import { getPlatformToken } from '@/lib/platform-auth';
import { useSessionQueryEnabled } from '@/hooks/usePlatformSession';

/** Ensures apiClient uses the platform JWT — ready as soon as session token exists. */
export function useAdminPortalApi() {
  const ready = useSessionQueryEnabled();

  useEffect(() => {
    if (!ready) return;
    const token = getPlatformToken();
    if (!token) return;
    apiClient.setTokenGetter(async () => getPlatformToken());
    apiClient.primeAuthToken(token);
  }, [ready]);

  return { ready };
}
