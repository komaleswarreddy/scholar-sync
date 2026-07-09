'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { usePortalConfig } from '@/hooks/usePortalConfig';

/** Redirects to /home if the admin has turned this tab off, so direct-URL access is also blocked. */
export function usePortalTabGuard(tab: string) {
  const { isTabEnabled } = usePortalConfig();
  const router = useRouter();
  const enabled = isTabEnabled(tab);

  useEffect(() => {
    if (!enabled) router.replace('/home');
  }, [enabled, router]);

  return enabled;
}
