'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { hasPlatformSession, isSchoolAdmin, getStoredPlatformUser, getPlatformToken } from '@/lib/platform-auth';

export default function HomePage() {
  const router = useRouter();
  const [redirected, setRedirected] = useState(false);

  useEffect(() => {
    if (redirected) return;
    if (!hasPlatformSession()) {
      router.push('/sign-in');
      return;
    }
    const user = getStoredPlatformUser();
    const token = getPlatformToken();
    setRedirected(true);
    if (isSchoolAdmin(user, token)) {
      router.replace('/admin/users');
    } else {
      router.replace('/home');
    }
  }, [router, redirected]);

  return <p>Redirecting...</p>;
}
