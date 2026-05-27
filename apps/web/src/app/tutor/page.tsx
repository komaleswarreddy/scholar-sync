'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useUser } from '@clerk/nextjs';
import { Header } from '@/components/layout/Header';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { track } from '@/lib/telemetry';
import { GraduationCap, ArrowRight, Lightbulb, ListChecks, NotebookPen } from 'lucide-react';

const SUGGESTIONS = [
  { title: 'Explain a concept', icon: Lightbulb, prompt: 'Explain this concept step by step:' },
  { title: 'Test me', icon: ListChecks, prompt: 'Quiz me on:' },
  { title: 'Summarize a topic', icon: NotebookPen, prompt: 'Summarize this topic in simple terms:' },
];

export default function TutorPage() {
  const router = useRouter();
  const { isLoaded, isSignedIn } = useUser();

  useEffect(() => {
    track('tutor.viewed');
  }, []);

  const startTutor = (prefill?: string) => {
    track('tutor.start_clicked', prefill ? { prefill } : undefined);
    if (typeof window !== 'undefined' && prefill) {
      try {
        window.localStorage.setItem('tutorPrefillV1', prefill);
      } catch {
        // ignore
      }
    }
    router.push('/tutor-mode');
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
        <div className="max-w-4xl mx-auto px-6 py-10">
          <div className="flex items-start justify-between gap-6 mb-8">
            <div>
              <div className="flex items-center gap-2">
                <GraduationCap className="w-5 h-5 text-text-secondary" />
                <h2 className="text-2xl font-semibold text-text-primary">Your Tutor</h2>
              </div>
              <p className="text-text-secondary mt-2">
                Ask questions, get explanations, and practice with quick quizzes.
              </p>
            </div>
            <Button variant="primary" onClick={() => startTutor()} className="flex items-center gap-2">
              Start tutoring
              <ArrowRight className="w-4 h-4" />
            </Button>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {SUGGESTIONS.map((s) => {
              const Icon = s.icon;
              return (
                <Card key={s.title} hover onClick={() => startTutor(s.prompt)} className="p-5">
                  <div className="w-10 h-10 rounded-2xl bg-surface-hover flex items-center justify-center mb-3">
                    <Icon className="w-5 h-5 text-text-secondary" />
                  </div>
                  <p className="text-base font-semibold text-text-primary">{s.title}</p>
                  <p className="text-sm text-text-tertiary mt-2 line-clamp-2">{s.prompt}</p>
                </Card>
              );
            })}
          </div>

          <div className="mt-8">
            <Card className="p-6">
              <p className="text-text-secondary">
                Tip: Tutor Mode uses the same sources you’ve selected in your workspace.
              </p>
              <div className="mt-4 flex flex-wrap gap-2">
                <Button variant="secondary" onClick={() => router.push('/dashboard')}>
                  Open workspace
                </Button>
                <Button variant="ghost" onClick={() => router.push('/notes')}>
                  Browse notes
                </Button>
              </div>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
}

