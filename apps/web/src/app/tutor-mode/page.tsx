'use client';

import { Header } from '@/components/layout/Header';
import { ChatInterface } from '@/components/chat/ChatInterface';
import { SourceProvider } from '@/contexts/SourceContext';
import { UserProvider } from '@/contexts/UserContext';

export default function TutorModePage() {
  return (
    <UserProvider>
      <SourceProvider>
        <div className="h-screen w-screen flex flex-col overflow-hidden bg-background">
          <Header />
          <div className="flex-1 p-4 overflow-hidden">
            <main className="h-full bg-surface rounded-3xl overflow-hidden border border-border-default min-w-0">
              <ChatInterface mode="tutor" />
            </main>
          </div>
        </div>
      </SourceProvider>
    </UserProvider>
  );
}
