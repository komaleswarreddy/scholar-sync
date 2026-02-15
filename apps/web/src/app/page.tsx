'use client'; // Make this a client component

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useUser } from '@clerk/nextjs';

export default function HomePage() {
  const router = useRouter();
  const { isSignedIn, isLoaded, user } = useUser();
  const [redirected, setRedirected] = useState(false);

  useEffect(() => {
    if (!isLoaded) return; // Wait for Clerk to load
    
    if (isSignedIn && user && !redirected) {
      // Get user email from Clerk - try multiple ways
      const email = (
        user.primaryEmailAddress?.emailAddress ||
        user.emailAddresses?.[0]?.emailAddress ||
        user.emailAddresses?.[0]?.email_address
      )?.toLowerCase()?.trim();
      
      // Check if email matches known admin email
      const ADMIN_EMAILS = ['harikapallapothu09@gmail.com'];
      
      if (email && ADMIN_EMAILS.includes(email)) {
        // Use window.location for a hard redirect to ensure it happens
        setRedirected(true);
        window.location.href = '/analytics';
        return;
      }
      
      // Not admin - redirect to dashboard
      setRedirected(true);
      router.replace('/dashboard');
    } else if (isLoaded && !isSignedIn) {
      router.push('/sign-in');
    }
  }, [isLoaded, isSignedIn, user, router, redirected]);

  return <p>Redirecting...</p>;
}
