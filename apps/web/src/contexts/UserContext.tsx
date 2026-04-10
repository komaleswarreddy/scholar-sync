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
  // Must match server and client (never gate on `window` — that breaks hydration).
  const clerkKey = process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY;
  const isClerkConfigured = Boolean(
    clerkKey && !clerkKey.includes('...')
  );
  
  // Use Clerk hooks - must be called unconditionally
  // If ClerkProvider isn't present, hooks will still work but return defaults
  const { user, isSignedIn, isLoaded: userLoaded } = useUser();
  const { signOut: clerkSignOut, getToken: clerkGetToken, isLoaded: authLoaded } = useAuth();
  
  const [loading, setLoading] = useState(true);

  // Safe wrapper for getToken
  const getToken = useCallback(async () => {
    try {
      if (!clerkGetToken) {
        return null;
      }
      // Avoid triggering Clerk session calls when signed out or not ready yet.
      // This prevents repeated /v1/client/sessions/* requests during initial load.
      if (!isClerkConfigured || !userLoaded || !authLoaded || !isSignedIn) {
        return null;
      }
      // Use the session JWT (no JWT template required in Clerk).
      const token = await clerkGetToken();
      return token ?? null;
    } catch (err) {
      console.error('[AUTH] Error fetching token:', err);
      return null;
    }
  }, [authLoaded, clerkGetToken, isClerkConfigured, isSignedIn, userLoaded]);

  // Logout handler for ApiClient
  const handleLogout = useCallback(async () => {
    if (clerkSignOut) {
      await clerkSignOut();
    }
  }, [clerkSignOut]);

  // Wait for Clerk to finish loading before setting loading to false
  useEffect(() => {
    const isClerkLoaded = userLoaded && authLoaded;
    
    if (!isClerkConfigured) {
      setLoading(false);
      return;
    }
    
    if (isClerkLoaded) {
      // Only attach token getter when signed in; otherwise API calls should be anonymous
      // and must not trigger Clerk session network calls.
      apiClient.setTokenGetter(isSignedIn ? getToken : async () => null);
      apiClient.setLogoutHandler(handleLogout);
      setLoading(false);
    } else {
      // Set a timeout to prevent infinite loading if Clerk never loads
      const timeout = setTimeout(() => {
        apiClient.setTokenGetter(isSignedIn ? getToken : async () => null);
        apiClient.setLogoutHandler(handleLogout);
        setLoading(false);
      }, 10000);
      
      return () => clearTimeout(timeout);
    }
  }, [getToken, handleLogout, userLoaded, authLoaded, isSignedIn, isClerkConfigured]);

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
