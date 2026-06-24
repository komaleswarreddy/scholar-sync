'use client';

import { useEffect, useMemo } from 'react';
import { useRouter } from 'next/navigation';
import { Card } from '@/components/ui/Card';
import { Button } from '@/components/ui/Button';
import { StudioOutputsSkeleton } from '@/components/skeleton';
import { StudioPreviewProvider } from '@/contexts/StudioPreviewContext';
import { useAppToast } from '@/contexts/AppToastContext';
import { useDeleteStudioFeature, useStudioFeatures } from '@/hooks/useStudioFeatures';
import { useStudioFeaturePreview } from '@/hooks/useStudioFeaturePreview';
import { hasStudioContent } from '@/lib/studio-display';
import { track } from '@/lib/telemetry';
import {
  ArrowRight,
  Layers,
  Network,
  FileQuestion,
  Presentation,
  Sparkles,
  Download,
  Trash2,
} from 'lucide-react';

const STUDIO_TILES = [
  { title: 'Flashcards', type: 'flashcards', icon: Layers },
  { title: 'Mindmaps', type: 'mind_map', icon: Network },
  { title: 'Quizzes', type: 'quiz', icon: FileQuestion },
  { title: 'Slide Decks', type: 'slide_deck', icon: Presentation },
] as const;

function StudiosHubContent() {
  const router = useRouter();
  const { showToast } = useAppToast();
  const { data: features = [], isLoading } = useStudioFeatures({ limit: 24 });
  const deleteFeature = useDeleteStudioFeature();
  const { openPreview } = useStudioFeaturePreview();

  useEffect(() => {
    track('studios.viewed');
  }, []);

  const recent = useMemo(() => features, [features]);

  const openWorkspaceWithIntent = (type: string) => {
    try {
      window.localStorage.setItem('studioIntentV1', JSON.stringify({ type }));
    } catch {
      // ignore
    }
    router.push('/dashboard');
  };

  const handleOpen = (feature: (typeof features)[number]) => {
    if (!hasStudioContent(feature.content)) {
      showToast('This asset has no content to display');
      return;
    }
    track('studios.feature_opened', { id: feature.id, type: feature.type });
    openPreview({
      id: feature.id,
      type: feature.type,
      title: feature.title,
      content: feature.content,
    });
  };

  const handleDelete = (id: string) => {
    void deleteFeature.mutateAsync(id).catch(() => showToast('Could not delete asset'));
  };

  const handleDownload = (feature: (typeof features)[number]) => {
    try {
      const content =
        typeof feature.content === 'string' ? feature.content : JSON.stringify(feature.content, null, 2);
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
      showToast('Could not download asset');
    }
  };

  return (
    <>
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

        <div>
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-text-primary">Recent</h3>
          </div>

          {isLoading && recent.length === 0 ? (
            <StudioOutputsSkeleton />
          ) : recent.length === 0 ? (
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
                <Card key={f.id} hover onClick={() => handleOpen(f)} className="p-5">
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <p className="text-xs text-text-tertiary">{f.type.replaceAll('_', ' ')}</p>
                      <p className="text-base font-semibold text-text-primary mt-1 truncate">{f.title}</p>
                      <p className="text-xs text-text-tertiary mt-3">
                        {f.created_at ? new Date(f.created_at).toLocaleString() : '—'}
                      </p>
                    </div>
                    <div className="flex items-center gap-1" onClick={(e) => e.stopPropagation()}>
                      <button
                        className="p-2 rounded-full hover:bg-surface-hover transition-colors"
                        onClick={() => handleDownload(f)}
                        title="Download"
                        aria-label="Download"
                        type="button"
                      >
                        <Download className="w-4 h-4 text-text-tertiary" />
                      </button>
                      <button
                        className="p-2 rounded-full hover:bg-surface-hover transition-colors"
                        onClick={() => handleDelete(f.id)}
                        title="Delete"
                        aria-label="Delete"
                        type="button"
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
    </>
  );
}

export default function StudiosHubPage() {
  return (
    <StudioPreviewProvider>
      <div className="max-w-6xl mx-auto px-6 py-8">
        <StudiosHubContent />
      </div>
    </StudioPreviewProvider>
  );
}
