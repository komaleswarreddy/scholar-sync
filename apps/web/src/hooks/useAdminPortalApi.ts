'use client';

import { useEffect, useState } from 'react';
import { apiClient } from '@/lib/api-client';
import { getPlatformToken, hasPlatformSession } from '@/lib/platform-auth';

/** Ensures apiClient uses the platform JWT on ops dashboard pages. */
export function useAdminPortalApi() {
  const [ready, setReady] = useState(() =>
    typeof window !== 'undefined' && hasPlatformSession()
  );

  useEffect(() => {
    if (hasPlatformSession()) {
      apiClient.setTokenGetter(async () => getPlatformToken());
      setReady(true);
    }
  }, []);

  return { ready };
}
