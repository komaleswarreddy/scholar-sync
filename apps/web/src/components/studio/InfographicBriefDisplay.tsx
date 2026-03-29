'use client';

import { useMemo, useRef, useCallback, useState } from 'react';
import { Download, Loader2, Image as ImageIcon } from 'lucide-react';
import { toPng } from 'html-to-image';
import { InfographicRenderer, type InfographicData } from './InfographicRenderer';

interface InfographicBriefDisplayProps {
  briefData: string | object;
}

function parseInfographicPayload(briefData: string | object): {
  infographicData: InfographicData | null;
  summaryBullets: string[];
} {
  try {
    if (typeof briefData === 'object' && briefData !== null) {
      const parsed = briefData as Record<string, unknown>;

      const raw = parsed.infographic_data;
      let infographicData: InfographicData | null = null;
      if (raw && typeof raw === 'object' && (raw as Record<string, unknown>).title) {
        infographicData = raw as InfographicData;
      }

      let summaryBullets: string[] = [];
      const rawBullets = parsed.summary_bullets;
      if (Array.isArray(rawBullets)) {
        summaryBullets = rawBullets.map((b) => String(b).trim()).filter(Boolean).slice(0, 4);
      }
      if (summaryBullets.length === 0 && typeof parsed.content === 'string') {
        summaryBullets = parsed.content
          .split('\n')
          .map((l) => l.replace(/^\s*[-*]\s*/, '').trim())
          .filter(Boolean)
          .slice(0, 4);
      }

      return { infographicData, summaryBullets };
    }
  } catch { /* ignore */ }
  return { infographicData: null, summaryBullets: [] };
}

export function InfographicBriefDisplay({ briefData }: InfographicBriefDisplayProps) {
  const { infographicData, summaryBullets } = useMemo(
    () => parseInfographicPayload(briefData),
    [briefData],
  );

  const rendererRef = useRef<HTMLDivElement>(null);
  const [downloading, setDownloading] = useState(false);

  const handleDownloadPng = useCallback(async () => {
    if (!rendererRef.current) return;
    setDownloading(true);
    try {
      const dataUrl = await toPng(rendererRef.current, {
        cacheBust: true,
        pixelRatio: 2,
        backgroundColor: '#ffffff',
      });
      const link = document.createElement('a');
      link.download = `infographic-${Date.now()}.png`;
      link.href = dataUrl;
      link.click();
    } catch (err) {
      console.error('Failed to export infographic:', err);
    } finally {
      setDownloading(false);
    }
  }, []);

  if (!infographicData) {
    return (
      <div className="p-6">
        <div className="text-center py-8">
          <ImageIcon className="w-10 h-10 text-text-tertiary mx-auto mb-3" />
          <p className="text-sm text-text-secondary">
            Could not render infographic. Please try generating again.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="p-4 space-y-4">
      {/* Toolbar */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 rounded-lg bg-accent-purple/10 flex items-center justify-center">
            <ImageIcon className="w-4 h-4 text-accent-purple" />
          </div>
          <h3 className="text-base font-bold text-text-primary">Study Infographic</h3>
        </div>
        <button
          onClick={handleDownloadPng}
          disabled={downloading}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg
                     bg-accent-blue/10 text-accent-blue hover:bg-accent-blue/20
                     disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {downloading ? (
            <Loader2 className="w-3.5 h-3.5 animate-spin" />
          ) : (
            <Download className="w-3.5 h-3.5" />
          )}
          {downloading ? 'Exporting…' : 'Download PNG'}
        </button>
      </div>

      {/* Rendered infographic */}
      <div className="flex justify-center">
        <InfographicRenderer ref={rendererRef} data={infographicData} />
      </div>

      {/* At-a-glance bullets */}
      {summaryBullets.length > 0 && (
        <div className="bg-surface-subtle rounded-xl border border-border-default p-4">
          <h4 className="text-xs font-semibold text-text-tertiary uppercase tracking-wide mb-2">
            At a glance
          </h4>
          <ul className="list-disc list-outside text-sm text-text-primary space-y-1.5 pl-4 marker:text-text-tertiary">
            {summaryBullets.map((line, i) => (
              <li key={i} className="leading-snug">{line}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
