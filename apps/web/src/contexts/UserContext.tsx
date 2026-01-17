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
  // Check if Clerk is configured
  const isClerkConfigured = typeof window !== 'undefined' && 
    process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY && 
    !process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY.includes('...');
  
  // Use Clerk hooks - must be called unconditionally
  // If ClerkProvider isn't present, hooks will still work but return defaults
  const { user, isSignedIn, isLoaded: userLoaded } = useUser();
  const { signOut: clerkSignOut, getToken: clerkGetToken, isLoaded: authLoaded } = useAuth();
  
  const [loading, setLoading] = useState(true);

  // Safe wrapper for getToken
  const getToken = useCallback(async () => {
    try {
      console.log('[🔐 AUTH DEBUG] Fetching token from Clerk...');
      if (!clerkGetToken) {
        console.log('[🔐 AUTH DEBUG] ⚠️ clerkGetToken is not available');
        return null;
      }
      const token = await clerkGetToken({ template: 'default' });
      
      if (token) {
        // Decode token to show user_id (for debugging only)
        try {
          const payload = JSON.parse(atob(token.split('.')[1]));
          const userId = payload.sub;
          console.log('[🔐 AUTH DEBUG] ✅ Token fetched successfully');
          console.log('[🔐 AUTH DEBUG]   User ID from token:', userId);
          console.log('[🔐 AUTH DEBUG]   Token preview:', token.substring(0, 20) + '...' + token.substring(token.length - 20));
        } catch (e) {
          console.log('[🔐 AUTH DEBUG] ✅ Token fetched (could not decode for preview)');
        }
      } else {
        console.log('[🔐 AUTH DEBUG] ⚠️ Token is null');
      }
      
      return token ?? null;
    } catch (err) {
      console.error('[🔐 AUTH DEBUG] ❌ Error fetching token:', err);
      return null;
    }
  }, [clerkGetToken]);

  // Logout handler for ApiClient
  const handleLogout = useCallback(async () => {
    if (clerkSignOut) {
      await clerkSignOut();
    }
  }, [clerkSignOut]);

  // Wait for Clerk to finish loading before setting loading to false
  useEffect(() => {
    const isClerkLoaded = userLoaded && authLoaded;
    console.log('[🔐 AUTH DEBUG] Clerk loading state:', { 
      userLoaded, 
      authLoaded, 
      isClerkLoaded, 
      isSignedIn, 
      isClerkConfigured,
      hasClerkKey: !!process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY
    });
    
    if (!isClerkConfigured) {
      console.warn('[🔐 AUTH DEBUG] ⚠️ Clerk is not configured. Skipping authentication setup.');
      setLoading(false);
      return;
    }
    
    if (isClerkLoaded) {
      console.log('[🔐 AUTH DEBUG] Registering token getter with API client');
      apiClient.setTokenGetter(getToken);
      apiClient.setLogoutHandler(handleLogout);
      setLoading(false);
      console.log('[🔐 AUTH DEBUG] ✅ Token getter registered. User signed in:', isSignedIn);
    } else {
      console.log('[🔐 AUTH DEBUG] ⏳ Waiting for Clerk to load...');
      // Set a timeout to prevent infinite loading if Clerk never loads
      const timeout = setTimeout(() => {
        console.warn('[🔐 AUTH DEBUG] ⚠️ Clerk took too long to load (10s timeout), setting loading to false anyway');
        // Still register the token getter even if Clerk is slow
        apiClient.setTokenGetter(getToken);
        apiClient.setLogoutHandler(handleLogout);
        setLoading(false);
      }, 10000); // 10 second timeout
      
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
