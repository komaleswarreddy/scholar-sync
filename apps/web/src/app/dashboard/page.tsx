/**
 * Dashboard Page
 * 
 * Main chat interface with source-grounded RAG.
 */

'use client';

import { useEffect, useState } from 'react';
import { useUser } from '@clerk/nextjs';
import { ChatInterface } from '@/components/chat/ChatInterface';

export default function DashboardPage() {
  const { isSignedIn, isLoaded, user } = useUser();
  const [shouldRedirect, setShouldRedirect] = useState<boolean | null>(null);
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
  }, []);

  useEffect(() => {
    if (!isLoaded) return;
    
    if (isSignedIn && user) {
      // Get user email from Clerk - try multiple ways
      const email = (
        user.primaryEmailAddress?.emailAddress ||
        user.emailAddresses?.[0]?.emailAddress ||
        
        ''
      )?.toLowerCase()?.trim();
      
      // Check if email matches known admin email
      const ADMIN_EMAILS = ['scombinator26@gmail.com'];
      
      if (email && ADMIN_EMAILS.includes(email)) {
        // Use window.location for a hard redirect to ensure it happens
        setShouldRedirect(true);
        window.location.href = '/analytics';
        return;
      }
      
      setShouldRedirect(false);
    } else if (isLoaded && !isSignedIn) {
      setShouldRedirect(false);
    }
  }, [isLoaded, isSignedIn, user]);

  if (!mounted) {
    return (
      <div className="h-screen flex items-center justify-center">
        <p className="text-text-secondary">Loading...</p>
      </div>
    );
  }

  // Show loading while checking or redirecting
  if (shouldRedirect === true || (isLoaded && isSignedIn && user && shouldRedirect === null)) {
    return (
      <div className="h-screen flex items-center justify-center">
        <p className="text-text-secondary">Redirecting...</p>
      </div>
    );
  }

  return <ChatInterface mode="dashboard" />;
}
