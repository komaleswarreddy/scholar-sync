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
      console.log('[🔐 AUTH DEBUG] Fetching token from Clerk...');
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
    await clerkSignOut();
  }, [clerkSignOut]);

  // Wire logoutFunc for ApiClient
  // Only re-register if getToken or handleLogout functions change, not on isSignedIn changes
  useEffect(() => {
    console.log('[🔐 AUTH DEBUG] Registering token getter with API client');
    apiClient.setTokenGetter(getToken);
    apiClient.setLogoutHandler(handleLogout);
    setLoading(false);
    console.log('[🔐 AUTH DEBUG] ✅ Token getter registered. User signed in:', isSignedIn);
  }, [getToken, handleLogout]); // Removed isSignedIn to prevent unnecessary re-registrations

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
