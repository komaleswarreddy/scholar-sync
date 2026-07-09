'use client';

import { useEffect, useState, useSyncExternalStore } from 'react';
import {
  getPlatformToken,
  PLATFORM_SESSION_CHANGED,
  type PlatformUser,
} from '@/lib/platform-auth';

export type PlatformSessionSnapshot = {
  token: string | null;
  user: PlatformUser | null;
  signedIn: boolean;
  /**
   * False until the client has mounted and read the real sessionStorage state.
   * `getServerSnapshot()` always reports `signedIn: false` (sessionStorage isn't available
   * during SSR/pre-hydration), so before `isHydrated` flips true, `signedIn: false` means
   * "not yet determined" rather than "confirmed signed out". Callers that gate rendering on
   * auth (e.g. redirecting unauthenticated users) must wait for `isHydrated` before treating
   * `signedIn === false` as definitive — otherwise every hard refresh briefly renders the
   * signed-out state.
   */
  isHydrated: boolean;
};

/** Raw sessionStorage-derived state, without the hydration flag (tracked separately below). */
type RawSessionSnapshot = Omit<PlatformSessionSnapshot, 'isHydrated'>;

const EMPTY_SNAPSHOT: RawSessionSnapshot = {
  token: null,
  user: null,
  signedIn: false,
};

/** Must return the same reference when data is unchanged (useSyncExternalStore requirement). */
let cachedSnapshot: RawSessionSnapshot = EMPTY_SNAPSHOT;
let cachedKey = '';

function getSnapshot(): RawSessionSnapshot {
  if (typeof window === 'undefined') return EMPTY_SNAPSHOT;

  const token = getPlatformToken();
  let userRaw = '';
  try {
    userRaw = sessionStorage.getItem('platform_user') ?? '';
  } catch {
    userRaw = '';
  }
  const signedIn = Boolean(token);
  const key = `${token ?? ''}\0${userRaw}\0${signedIn ? '1' : '0'}`;

  if (key === cachedKey) {
    return cachedSnapshot;
  }

  let user: PlatformUser | null = null;
  if (userRaw) {
    try {
      user = JSON.parse(userRaw) as PlatformUser;
    } catch {
      user = null;
    }
  }

  cachedKey = key;
  cachedSnapshot = { token, user, signedIn };
  return cachedSnapshot;
}

function getServerSnapshot(): RawSessionSnapshot {
  return EMPTY_SNAPSHOT;
}

function subscribe(onChange: () => void): () => void {
  const handler = () => onChange();
  window.addEventListener(PLATFORM_SESSION_CHANGED, handler);
  return () => window.removeEventListener(PLATFORM_SESSION_CHANGED, handler);
}

/**
 * Reactive sessionStorage session — re-renders immediately on login/logout.
 *
 * `isHydrated` flips to true on the first client render after mount/hydration completes.
 * Until then, `signedIn` reflects the SSR placeholder (always `false`) and must not be read
 * as a confirmed "signed out" result — see the `isHydrated` doc comment above.
 */
export function usePlatformSession(): PlatformSessionSnapshot {
  const snapshot = useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot);
  const [isHydrated, setIsHydrated] = useState(false);

  useEffect(() => {
    setIsHydrated(true);
  }, []);

  return { ...snapshot, isHydrated };
}

/** True when JWT is present — enough to run authenticated API queries. */
export function useSessionQueryEnabled(): boolean {
  return usePlatformSession().signedIn;
}
