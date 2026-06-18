'use client';

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useState } from 'react';
import { ThemeProvider } from '@/contexts/ThemeContext';
import { ChatProvider } from '@/contexts/ChatContext';
import { UserProvider } from '@/contexts/UserContext';
import { AppToastProvider } from '@/contexts/AppToastContext';
import { TutorClassProvider } from '@/contexts/TutorClassContext';

export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            refetchOnWindowFocus: false,
            retry: 1,
            staleTime: 5 * 60 * 1000, // 5 minutes
          },
        },
      })
  );

  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <UserProvider>
          <AppToastProvider>
            <TutorClassProvider>
              <ChatProvider>{children}</ChatProvider>
            </TutorClassProvider>
          </AppToastProvider>
        </UserProvider>
      </ThemeProvider>
    </QueryClientProvider>
  );
}




