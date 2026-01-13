'use client';

import { Header } from '@/components/layout/Header';
import { SourceList } from '@/components/sources/SourceList';
import { StudioSuite } from '@/components/studio/StudioSuite';
import { NotesSection } from '@/components/notes/NotesSection';
import { SourceProvider } from '@/contexts/SourceContext';
import { UserProvider, useUserContext } from '@/contexts/UserContext';

export function DashboardWrapper({ children }: { children: React.ReactNode }) {
  const Wrapper = () => {
    const { isSignedIn, loading } = useUserContext();

    if (loading) return <p>Loading...</p>;
    if (!isSignedIn) return <p>Redirecting to login...</p>;

    return (
      <div className="h-screen w-screen flex flex-col overflow-hidden" style={{ backgroundColor: '#131314' }}>
        <Header />
        <div className="flex-1 flex gap-4 p-4 overflow-hidden">
          <aside className="w-[25%] bg-surface rounded-3xl flex flex-col overflow-hidden border border-border-default">
            <SourceList />
          </aside>
          <main className="flex-1 flex flex-col bg-surface rounded-3xl overflow-hidden border border-border-default min-w-0">
            {children}
          </main>
          <aside className="w-[25%] bg-surface rounded-3xl flex flex-col overflow-hidden border border-border-default">
            <div className="flex-1 border-b border-border-default min-h-0">
              <StudioSuite />
            </div>
            <div className="flex-1 min-h-0">
              <NotesSection />
            </div>
          </aside>
        </div>
      </div>
    );
  };

  return (
    <UserProvider>
      <SourceProvider>
        <Wrapper />
      </SourceProvider>
    </UserProvider>
  );
}
