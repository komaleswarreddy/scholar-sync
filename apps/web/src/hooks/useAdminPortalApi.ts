'use client';

import { useEffect, useState } from 'react';
import { apiClient } from '@/lib/api-client';
import { hasAdminSession } from '@/lib/admin-auth';

/** Ensures apiClient uses the admin portal JWT on ops dashboard pages. */
export function useAdminPortalApi() {
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (hasAdminSession()) {
      apiClient.setAdminPortalMode(true);
      setReady(true);
    }
  }, []);

  return { ready };
}
