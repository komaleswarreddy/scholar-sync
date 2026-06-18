'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useUser } from '@clerk/nextjs';

export default function HomePage() {
  const router = useRouter();
  const { isSignedIn, isLoaded } = useUser();
  const [redirected, setRedirected] = useState(false);

  useEffect(() => {
    if (!isLoaded) return;

    if (isSignedIn && !redirected) {
      setRedirected(true);
      router.replace('/home');
    } else if (isLoaded && !isSignedIn) {
      router.push('/sign-in');
    }
  }, [isLoaded, isSignedIn, router, redirected]);

  return <p>Redirecting...</p>;
}
