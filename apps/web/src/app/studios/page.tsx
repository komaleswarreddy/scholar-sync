'use client';

import { useEffect, useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useUser } from '@clerk/nextjs';
import { Header } from '@/components/layout/Header';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { GenerationModal } from '@/components/studio/GenerationModal';
import { track } from '@/lib/telemetry';
import {
  ArrowRight,
  Layers,
  Network,
  FileQuestion,
  Image as ImageIcon,
  Presentation,
  FileText,
  Sparkles,
  Download,
  Trash2,
} from 'lucide-react';

type GeneratedFeature = {
  id: string;
  type: string;
  title: string;
  content: any;
  timestamp: Date;
};

function loadFeatures(): GeneratedFeature[] {
  if (typeof window === 'undefined') return [];
  try {
    const raw = window.localStorage.getItem('generatedStudioFeatures');
    if (!raw) return [];
    const parsed = JSON.parse(raw) as any[];
    return parsed
      .map((f) => ({
        id: String(f.id),
        type: String(f.type ?? 'studio'),
        title: String(f.title ?? 'Studio output'),
        content: f.content,
        timestamp: new Date(f.timestamp ?? Date.now()),
      }))
      .filter((f) => Boolean(f.id))
      .sort((a, b) => b.timestamp.getTime() - a.timestamp.getTime());
  } catch {
    return [];
  }
}

function saveFeatures(next: GeneratedFeature[]) {
  if (typeof window === 'undefined') return;
  try {
    window.localStorage.setItem('generatedStudioFeatures', JSON.stringify(next));
  } catch {
    // ignore
  }
}

const STUDIO_TILES = [
  { title: 'Flashcards', type: 'flashcards', icon: Layers },
  { title: 'Mindmaps', type: 'mind_map', icon: Network },
  { title: 'Quizzes', type: 'quiz', icon: FileQuestion },
  { title: 'Infographics', type: 'infographic', icon: ImageIcon },
  { title: 'Slide Decks', type: 'slide_deck', icon: Presentation },
  { title: 'Reports', type: 'report', icon: FileText },
] as const;

export default function StudiosHubPage() {
  const router = useRouter();
  const { isLoaded, isSignedIn } = useUser();
  const [features, setFeatures] = useState<GeneratedFeature[]>([]);
  const [selected, setSelected] = useState<GeneratedFeature | null>(null);

  useEffect(() => {
    track('studios.viewed');
  }, []);

  useEffect(() => {
    setFeatures(loadFeatures());
  }, []);

  const recent = useMemo(() => features.slice(0, 24), [features]);

  const openWorkspaceWithIntent = (type: string) => {
    try {
      window.localStorage.setItem('studioIntentV1', JSON.stringify({ type }));
    } catch {
      // ignore
    }
    router.push('/dashboard');
  };

  const handleDelete = (id: string) => {
    const next = features.filter((f) => f.id !== id);
    setFeatures(next);
    saveFeatures(next);
    if (selected?.id === id) setSelected(null);
  };

  const handleDownload = (feature: GeneratedFeature) => {
    try {
      const content = typeof feature.content === 'string' ? feature.content : JSON.stringify(feature.content, null, 2);
      const blob = new Blob([content], { type: 'text/plain' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${feature.title.toLowerCase().replace(/\s+/g, '-')}-${feature.id}.txt`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch {
      // ignore
    }
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
          <div className="flex items-start justify-between gap-6 mb-8">
            <div>
              <div className="flex items-center gap-2">
                <Sparkles className="w-5 h-5 text-text-secondary" />
                <h2 className="text-2xl font-semibold text-text-primary">Studios</h2>
              </div>
              <p className="text-text-secondary mt-2">
                Review recent outputs and generate new study artifacts from your sources.
              </p>
            </div>
            <Button variant="secondary" onClick={() => router.push('/dashboard')} className="flex items-center gap-2">
              Open workspace
              <ArrowRight className="w-4 h-4" />
            </Button>
          </div>

          {/* Create new */}
          <div className="mb-10">
            <h3 className="text-lg font-semibold text-text-primary mb-4">Create New</h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {STUDIO_TILES.map((t) => {
                const Icon = t.icon;
                return (
                  <Card
                    key={t.type}
                    hover
                    onClick={() => openWorkspaceWithIntent(t.type)}
                    className="p-5"
                    title="Opens workspace Studio"
                  >
                    <div className="flex items-start justify-between gap-4">
                      <div>
                        <p className="text-base font-semibold text-text-primary">{t.title}</p>
                        <p className="text-sm text-text-tertiary mt-2">
                          Generates from your selected sources (and chat when available).
                        </p>
                      </div>
                      <div className="w-10 h-10 rounded-2xl bg-surface-hover flex items-center justify-center">
                        <Icon className="w-5 h-5 text-text-secondary" />
                      </div>
                    </div>
                  </Card>
                );
              })}
            </div>
          </div>

          {/* Recents */}
          <div>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-text-primary">Recent</h3>
            </div>

            {recent.length === 0 ? (
              <Card className="p-6">
                <p className="text-text-secondary">No studio outputs yet.</p>
                <p className="text-text-tertiary text-sm mt-1">
                  Generate your first artifact from the workspace Studio panel.
                </p>
                <div className="mt-4">
                  <Button variant="secondary" onClick={() => router.push('/dashboard')}>
                    Go to workspace
                  </Button>
                </div>
              </Card>
            ) : (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {recent.map((f) => (
                  <Card
                    key={f.id}
                    hover
                    onClick={() => {
                      track('studios.feature_opened', { id: f.id, type: f.type });
                      setSelected(f);
                    }}
                    className="p-5"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div className="min-w-0">
                        <p className="text-xs text-text-tertiary">{f.type.replaceAll('_', ' ')}</p>
                        <p className="text-base font-semibold text-text-primary mt-1 truncate">{f.title}</p>
                        <p className="text-xs text-text-tertiary mt-3">{f.timestamp.toLocaleString()}</p>
                      </div>
                      <div className="flex items-center gap-1" onClick={(e) => e.stopPropagation()}>
                        <button
                          className="p-2 rounded-full hover:bg-surface-hover transition-colors"
                          onClick={() => handleDownload(f)}
                          title="Download"
                          aria-label="Download"
                        >
                          <Download className="w-4 h-4 text-text-tertiary" />
                        </button>
                        <button
                          className="p-2 rounded-full hover:bg-surface-hover transition-colors"
                          onClick={() => handleDelete(f.id)}
                          title="Delete"
                          aria-label="Delete"
                        >
                          <Trash2 className="w-4 h-4 text-text-tertiary" />
                        </button>
                      </div>
                    </div>
                  </Card>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {selected ? (
        <GenerationModal
          isOpen={true}
          onClose={() => setSelected(null)}
          title={selected.title}
          content={selected.content}
          contentType="text"
        />
      ) : null}
    </div>
  );
}

