'use client';

import { useEffect, useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useUser } from '@clerk/nextjs';
import {
  ArrowRight,
  BarChart3,
  BookOpen,
  FileText,
  GraduationCap,
  Sparkles,
} from 'lucide-react';
import { Header } from '@/components/layout/Header';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { useNotes } from '@/hooks/useNotes';
import { resolveContinueLearning } from '@/lib/continue-learning';
import { track } from '@/lib/telemetry';

type StudioRecent = {
  id: string;
  type: string;
  title: string;
  timestamp: Date;
};

function loadRecentStudios(limit: number): StudioRecent[] {
  if (typeof window === 'undefined') return [];
  try {
    const raw = window.localStorage.getItem('generatedStudioFeatures');
    if (!raw) return [];
    const parsed = JSON.parse(raw) as Array<any>;
    return parsed
      .map((f) => ({
        id: String(f.id),
        type: String(f.type ?? 'studio'),
        title: String(f.title ?? 'Studio output'),
        timestamp: new Date(f.timestamp ?? Date.now()),
      }))
      .filter((f) => Boolean(f.id))
      .sort((a, b) => b.timestamp.getTime() - a.timestamp.getTime())
      .slice(0, limit);
  } catch {
    return [];
  }
}

export default function HomeLandingPage() {
  const router = useRouter();
  const { isLoaded, isSignedIn, user } = useUser();
  const { data: notes = [], isLoading: notesLoading } = useNotes();
  const [studios, setStudios] = useState<StudioRecent[]>([]);

  useEffect(() => {
    track('home.viewed');
  }, []);

  useEffect(() => {
    setStudios(loadRecentStudios(4));
  }, []);

  const greeting = useMemo(() => {
    const name =
      user?.firstName ||
      user?.fullName ||
      user?.primaryEmailAddress?.emailAddress?.split('@')[0] ||
      '';
    return name ? `Welcome back, ${name}` : 'Welcome back';
  }, [user]);

  const handleContinueLearning = async () => {
    track('home.continue_learning_clicked');
    const res = await resolveContinueLearning();
    if (res.kind === 'dashboard_with_recent_chat') {
      router.push('/dashboard');
      return;
    }
    router.push('/dashboard');
  };

  const handleTutor = () => {
    track('home.tutor_clicked');
    router.push('/tutor');
  };

  const handleCreateNotes = () => {
    track('home.create_notes_clicked');
    router.push('/dashboard');
  };

  const handleAnalytics = () => {
    track('home.analytics_clicked');
    router.push('/analytics');
  };

  const viewAllStudios = () => {
    track('home.studios_view_all_clicked');
    router.push('/studios');
  };

  const viewAllNotes = () => {
    track('home.notes_view_all_clicked');
    router.push('/notes');
  };

  if (!isLoaded) {
    return (
      <div className="h-screen w-screen flex items-center justify-center bg-background">
        <p className="text-text-secondary">Loading...</p>
      </div>
    );
  }

  if (!isSignedIn) {
    router.push('/sign-in');
    return (
      <div className="h-screen w-screen flex items-center justify-center bg-background">
        <p className="text-text-secondary">Redirecting...</p>
      </div>
    );
  }

  return (
    <div className="h-screen w-screen flex flex-col overflow-hidden bg-background">
      <Header />
      <div className="flex-1 overflow-y-auto">
        <div className="max-w-6xl mx-auto px-6 py-8">
          {/* Welcome */}
          <div className="flex items-start justify-between gap-6 mb-8">
            <div>
              <h2 className="text-2xl font-semibold text-text-primary">{greeting}</h2>
              <p className="text-text-secondary mt-1">
                Pick up where you left off, or jump into something new.
              </p>
            </div>
            <Button variant="secondary" onClick={handleContinueLearning} className="flex items-center gap-2">
              Continue Learning
              <ArrowRight className="w-4 h-4" />
            </Button>
          </div>

          {/* Primary actions */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-10">
            <Card hover onClick={handleContinueLearning} className="p-5">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="text-sm text-text-secondary">Continue</p>
                  <p className="text-lg font-semibold text-text-primary mt-1">Continue Learning</p>
                  <p className="text-sm text-text-tertiary mt-2">
                    Jump back into your latest workspace.
                  </p>
                </div>
                <div className="w-10 h-10 rounded-2xl bg-surface-hover flex items-center justify-center">
                  <BookOpen className="w-5 h-5 text-text-secondary" />
                </div>
              </div>
            </Card>

            <Card hover onClick={handleTutor} className="p-5">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="text-sm text-text-secondary">Tutor</p>
                  <p className="text-lg font-semibold text-text-primary mt-1">Your Tutor</p>
                  <p className="text-sm text-text-tertiary mt-2">
                    Explain, quiz, summarize, revise.
                  </p>
                </div>
                <div className="w-10 h-10 rounded-2xl bg-surface-hover flex items-center justify-center">
                  <GraduationCap className="w-5 h-5 text-text-secondary" />
                </div>
              </div>
            </Card>

            <Card hover onClick={handleCreateNotes} className="p-5">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="text-sm text-text-secondary">Notes</p>
                  <p className="text-lg font-semibold text-text-primary mt-1">Create Notes</p>
                  <p className="text-sm text-text-tertiary mt-2">
                    Use the workspace to save key ideas.
                  </p>
                </div>
                <div className="w-10 h-10 rounded-2xl bg-surface-hover flex items-center justify-center">
                  <FileText className="w-5 h-5 text-text-secondary" />
                </div>
              </div>
            </Card>

            <Card hover onClick={handleAnalytics} className="p-5">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <p className="text-sm text-text-secondary">Insights</p>
                  <p className="text-lg font-semibold text-text-primary mt-1">Analytics</p>
                  <p className="text-sm text-text-tertiary mt-2">
                    Review usage and system health.
                  </p>
                </div>
                <div className="w-10 h-10 rounded-2xl bg-surface-hover flex items-center justify-center">
                  <BarChart3 className="w-5 h-5 text-text-secondary" />
                </div>
              </div>
            </Card>
          </div>

          {/* Recent Studios */}
          <div className="mb-10">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-text-secondary" />
                <h3 className="text-lg font-semibold text-text-primary">Recent Studios</h3>
              </div>
              <Button variant="ghost" size="sm" onClick={viewAllStudios} className="flex items-center gap-2">
                View all
                <ArrowRight className="w-4 h-4" />
              </Button>
            </div>

            {studios.length === 0 ? (
              <Card className="p-6">
                <p className="text-text-secondary">No studio outputs yet.</p>
                <p className="text-text-tertiary text-sm mt-1">
                  Generate flashcards, quizzes, mindmaps, or reports from your sources.
                </p>
                <div className="mt-4">
                  <Button variant="secondary" onClick={() => router.push('/studios')}>
                    Explore Studios
                  </Button>
                </div>
              </Card>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {studios.map((s) => (
                  <Card
                    key={s.id}
                    hover
                    onClick={viewAllStudios}
                    className="p-5"
                    title="Open Studios Hub"
                  >
                    <div className="flex items-start justify-between gap-4">
                      <div className="min-w-0">
                        <p className="text-xs text-text-tertiary">{s.type.replaceAll('_', ' ')}</p>
                        <p className="text-base font-medium text-text-primary mt-1 truncate">
                          {s.title}
                        </p>
                        <p className="text-sm text-text-secondary mt-2">
                          {s.timestamp.toLocaleString()}
                        </p>
                      </div>
                      <ArrowRight className="w-4 h-4 text-text-tertiary flex-shrink-0 mt-1" />
                    </div>
                  </Card>
                ))}
              </div>
            )}
          </div>

          {/* Your Notes */}
          <div className="mb-4">
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-2">
                <FileText className="w-4 h-4 text-text-secondary" />
                <h3 className="text-lg font-semibold text-text-primary">Your Notes</h3>
              </div>
              <Button variant="ghost" size="sm" onClick={viewAllNotes} className="flex items-center gap-2">
                View all
                <ArrowRight className="w-4 h-4" />
              </Button>
            </div>

            {notesLoading ? (
              <Card className="p-6">
                <p className="text-text-secondary">Loading notes…</p>
              </Card>
            ) : notes.length === 0 ? (
              <Card className="p-6">
                <p className="text-text-secondary">No notes yet.</p>
                <p className="text-text-tertiary text-sm mt-1">
                  Create notes from your workspace to save important ideas.
                </p>
                <div className="mt-4">
                  <Button variant="secondary" onClick={handleCreateNotes}>
                    Create your first note
                  </Button>
                </div>
              </Card>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {notes.slice(0, 4).map((n) => (
                  <Card key={n.id} hover onClick={viewAllNotes} className="p-5" title="Open Notes">
                    <p className="text-base font-medium text-text-primary truncate">{n.title}</p>
                    <p className="text-sm text-text-secondary mt-2 line-clamp-2">{n.content}</p>
                    <p className="text-xs text-text-tertiary mt-3">{new Date(n.updated_at).toLocaleString()}</p>
                  </Card>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

