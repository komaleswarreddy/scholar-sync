'use client';

import { createContext, useContext, ReactNode, useCallback, useState, useEffect } from 'react';
import { useUser, useAuth } from '@clerk/nextjs';
import { apiClient } from '@/lib/api-client';

interface UserContextType {
  userId: string | null;
  fullName: string | null;
  email: string | null;
  avatarUrl: string | null;
  isSignedIn: boolean;
  getToken: () => Promise<string | null>;
  signOut: () => Promise<void>;
  loading: boolean;
}

const UserContext = createContext<UserContextType | undefined>(undefined);

export function UserProvider({ children }: { children: ReactNode }) {
  const { user, isSignedIn } = useUser();
  const { signOut: clerkSignOut, getToken: clerkGetToken } = useAuth();
  const [loading, setLoading] = useState(true);

  // Safe wrapper for getToken
  const getToken = useCallback(async () => {
    try {
      const token = await clerkGetToken({ template: 'default' });
      return token ?? null;
    } catch (err) {
      console.error('Error fetching token:', err);
      return null;
    }
  }, [clerkGetToken]);

  // Logout handler for ApiClient
  const handleLogout = useCallback(async () => {
    await clerkSignOut();
  }, [clerkSignOut]);

  // Wire logoutFunc for ApiClient
  useEffect(() => {
    apiClient.setTokenGetter(getToken);
    apiClient.setLogoutHandler(handleLogout);
    setLoading(false);
  }, [getToken, handleLogout]);

  const value: UserContextType = {
    userId: user?.id ?? null,
    fullName: user?.fullName ?? null,
    email: user?.primaryEmailAddress?.emailAddress ?? null,
    avatarUrl: user?.imageUrl ?? null,
    isSignedIn: !!isSignedIn,
    getToken,
    signOut: handleLogout,
    loading,
  };

  return <UserContext.Provider value={value}>{children}</UserContext.Provider>;
}

export function useUserContext() {
  const context = useContext(UserContext);
  if (!context) throw new Error('useUserContext must be used within UserProvider');
  return context;
}
