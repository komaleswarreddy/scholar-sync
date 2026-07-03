'use client';

import { createContext, useContext, ReactNode, useCallback, useState, useEffect, useRef } from 'react';
import { apiClient } from '@/lib/api-client';
import {
  clearPlatformSession,
  getPlatformToken,
  getStoredPlatformUser,
  hasPlatformSession,
  PLATFORM_SESSION_CHANGED,
  PlatformUser,
  signOutAndRedirect,
  setStoredPlatformUser,
} from '@/lib/platform-auth';
import { profileDisplayName } from '@/lib/profile-utils';

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
  refreshUser: () => Promise<void>;
}

const UserContext = createContext<UserContextType | undefined>(undefined);

function buildFullName(user: PlatformUser | null): string | null {
  if (!user) return null;
  const name = profileDisplayName(user);
  return name === 'Student' ? user.username ?? null : name;
}

export function UserProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<PlatformUser | null>(null);
  const [loading, setLoading] = useState(true);
  const hydratingRef = useRef(false);

  const getToken = useCallback(async () => getPlatformToken(), []);

  const signOut = useCallback(async () => {
    apiClient.clearAuthSession();
    signOutAndRedirect();
  }, []);

  const refreshUser = useCallback(async () => {
    const token = getPlatformToken();
    if (!token) {
      setUser(null);
      return;
    }
    try {
      const me = await apiClient.getMyProfile();
      setUser(me);
      setStoredPlatformUser(me);
    } catch {
      clearPlatformSession();
      setUser(null);
    }
  }, []);

  const hydrateUser = useCallback(async () => {
    if (hydratingRef.current) return;
    hydratingRef.current = true;

    const token = getPlatformToken();
    if (!token) {
      setUser(null);
      setLoading(false);
      hydratingRef.current = false;
      return;
    }

    apiClient.setTokenGetter(getToken);
    apiClient.setLogoutHandler(signOut);
    void apiClient.refreshToken(true);

    const cached = getStoredPlatformUser();
    if (cached) {
      setUser(cached);
      setLoading(false);
    }

    try {
      const me = await apiClient.getMyProfile();
      setUser(me);
      setStoredPlatformUser(me);
    } catch {
      if (!cached) {
        clearPlatformSession();
        setUser(null);
      }
    } finally {
      setLoading(false);
      hydratingRef.current = false;
    }
  }, [getToken, signOut]);

  useEffect(() => {
    if (!hasPlatformSession()) {
      setUser(null);
      setLoading(false);
      apiClient.setTokenGetter(async () => null);
      return;
    }

    void hydrateUser();

    const onSessionChanged = () => {
      void hydrateUser();
    };
    window.addEventListener(PLATFORM_SESSION_CHANGED, onSessionChanged);
    return () => window.removeEventListener(PLATFORM_SESSION_CHANGED, onSessionChanged);
  }, [hydrateUser]);

  const signedIn = hasPlatformSession();

  const value: UserContextType = {
    userId: user?.id ?? null,
    username: user?.username ?? null,
    fullName: buildFullName(user),
    email: user?.email ?? null,
    role: user?.role ?? null,
    avatarUrl: null,
    user,
    isSignedIn: signedIn,
    getToken,
    signOut,
    loading: signedIn && loading && !user,
    authReady: !signedIn || Boolean(user),
    refreshUser,
  };

  return <UserContext.Provider value={value}>{children}</UserContext.Provider>;
}

export function useUserContext() {
  const context = useContext(UserContext);
  if (!context) throw new Error('useUserContext must be used within UserProvider');
  return context;
}
