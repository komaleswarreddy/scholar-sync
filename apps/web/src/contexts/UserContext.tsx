'use client';

import { createContext, useContext, ReactNode, useCallback, useEffect, useRef, useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useQueryClient } from '@tanstack/react-query';
import { apiClient } from '@/lib/api-client';
import {
  clearPlatformSession,
  getPlatformToken,
  getStoredPlatformUser,
  getStoredProfileSyncedAt,
  PLATFORM_SESSION_CHANGED,
  PlatformUser,
  SIGN_OUT_QUERY,
  setStoredPlatformUser,
} from '@/lib/platform-auth';
import { profileDisplayName } from '@/lib/profile-utils';
import { usePlatformSession } from '@/hooks/usePlatformSession';
import { prefetchStudentPortalData } from '@/hooks/usePrefetchStudentData';

interface UserContextType {
  userId: string | null;
  username: string | null;
  fullName: string | null;
  email: string | null;
  role: string | null;
  avatarUrl: string | null;
  user: PlatformUser | null;
  isSignedIn: boolean;
  getToken: () => Promise<string | null>;
  signOut: () => Promise<void>;
  loading: boolean;
  authReady: boolean;
  refreshUser: (opts?: { force?: boolean }) => Promise<void>;
}

const UserContext = createContext<UserContextType | undefined>(undefined);

const PROFILE_REFRESH_MIN_MS = 30_000;

function buildFullName(user: PlatformUser | null): string | null {
  if (!user) return null;
  const name = profileDisplayName(user);
  return name === 'Student' ? user.username ?? null : name;
}

function usersEqual(a: PlatformUser | null, b: PlatformUser | null): boolean {
  if (a === b) return true;
  if (!a || !b) return false;
  return (
    a.id === b.id &&
    a.username === b.username &&
    a.email === b.email &&
    a.role === b.role &&
    a.first_name === b.first_name &&
    a.last_name === b.last_name &&
    a.mobile === b.mobile &&
    a.institute === b.institute &&
    a.class_level === b.class_level &&
    a.expertise_tier === b.expertise_tier &&
    Boolean(a.is_bootstrap_admin) === Boolean(b.is_bootstrap_admin) &&
    Boolean(a.is_active) === Boolean(b.is_active)
  );
}

export function UserProvider({ children }: { children: ReactNode }) {
  const router = useRouter();
  const queryClient = useQueryClient();
  const session = usePlatformSession();
  const { token, user: sessionUser, signedIn } = session;
  const [profileLoading, setProfileLoading] = useState(false);
  const lastProfileFetchRef = useRef(0);
  const syncedTokenRef = useRef<string | null>(null);
  const hydratedTokenRef = useRef<string | null>(null);
  const refreshInFlightRef = useRef(false);

  const getToken = useCallback(async () => getPlatformToken(), []);

  /** Client-side sign-out — clears local state and does an SPA route change
   * instead of a full page reload, which was the dominant source of perceived
   * logout latency (whole bundle re-download + re-parse + repaint). */
  const signOut = useCallback(async () => {
    apiClient.clearAuthSession();
    clearPlatformSession();
    try {
      sessionStorage.removeItem('admin_portal_token');
    } catch {
      /* ignore */
    }
    queryClient.clear();
    router.push(`/sign-in?${SIGN_OUT_QUERY}=1`);
  }, [router, queryClient]);

  const syncApiToken = useCallback(
    (nextToken: string | null) => {
      if (!nextToken) return;
      if (syncedTokenRef.current === nextToken) return;
      syncedTokenRef.current = nextToken;
      apiClient.setTokenGetter(async () => nextToken);
      apiClient.primeAuthToken(nextToken);
      apiClient.setLogoutHandler(signOut);
    },
    [signOut],
  );

  const refreshUser = useCallback(
    async (opts?: { force?: boolean }) => {
      const activeToken = getPlatformToken();
      if (!activeToken) return;
      if (refreshInFlightRef.current) return;

      syncApiToken(activeToken);
      const now = Date.now();
      if (!opts?.force && now - lastProfileFetchRef.current < PROFILE_REFRESH_MIN_MS) {
        return;
      }

      refreshInFlightRef.current = true;
      setProfileLoading(true);
      try {
        const me = await apiClient.getCurrentUser();
        const prev = getStoredPlatformUser();
        lastProfileFetchRef.current = Date.now();
        if (!usersEqual(prev, me)) {
          setStoredPlatformUser(me);
          window.dispatchEvent(new Event(PLATFORM_SESSION_CHANGED));
        }
      } catch {
        const cached = getStoredPlatformUser();
        if (!cached) {
          clearPlatformSession();
        }
      } finally {
        refreshInFlightRef.current = false;
        setProfileLoading(false);
      }
    },
    [syncApiToken],
  );

  useEffect(() => {
    if (!signedIn || !token) {
      syncedTokenRef.current = null;
      hydratedTokenRef.current = null;
      apiClient.setTokenGetter(async () => null);
      return;
    }

    syncApiToken(token);

    const isNewSession = hydratedTokenRef.current !== token;
    if (isNewSession) {
      hydratedTokenRef.current = token;
      void prefetchStudentPortalData(queryClient);

      // If login just established this session, it already fetched a fresh
      // user object — seed the throttle from that timestamp instead of firing
      // a redundant /auth/me call on the very next render.
      const syncedAt = getStoredProfileSyncedAt();
      if (syncedAt) {
        lastProfileFetchRef.current = syncedAt;
      }
    }

    const cached = getStoredPlatformUser();
    const now = Date.now();
    const needsFetch = !cached || now - lastProfileFetchRef.current >= PROFILE_REFRESH_MIN_MS;

    if (needsFetch) {
      void refreshUser({ force: !cached });
    }
  }, [signedIn, token, syncApiToken, refreshUser, queryClient]);

  const value: UserContextType = useMemo(
    () => ({
      userId: sessionUser?.id ?? null,
      username: sessionUser?.username ?? null,
      fullName: buildFullName(sessionUser),
      email: sessionUser?.email ?? null,
      role: sessionUser?.role ?? null,
      avatarUrl: null,
      user: sessionUser,
      isSignedIn: signedIn,
      getToken,
      signOut,
      loading: signedIn && profileLoading && !sessionUser,
      authReady: signedIn,
      refreshUser,
    }),
    [sessionUser, signedIn, getToken, signOut, profileLoading, refreshUser],
  );

  return <UserContext.Provider value={value}>{children}</UserContext.Provider>;
}

export function useUserContext() {
  const context = useContext(UserContext);
  if (!context) throw new Error('useUserContext must be used within UserProvider');
  return context;
}
