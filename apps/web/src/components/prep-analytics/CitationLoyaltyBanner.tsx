'use client';

import { CITATION_LOYALTY } from '@/lib/analytics-prep-mock-data';

type CitationLoyaltyBannerProps = {
  onLearnMore: () => void;
};

export function CitationLoyaltyBanner({ onLearnMore }: CitationLoyaltyBannerProps) {
  const pct = CITATION_LOYALTY.overall;

  return (
    <div className="prep-card prep-citation-banner mb-6">
      <div className="flex flex-col md:flex-row md:items-center gap-6">
        <div
          className="prep-citation-ring flex-shrink-0"
          style={{
            background: `conic-gradient(#374151 ${pct}%, #E5E7EB 0)`,
          }}
        >
          <span className="prep-citation-ring-value">{pct}%</span>
        </div>
        <div className="flex-1 min-w-0">
          <p className="prep-section-eyebrow mb-1">SOURCE CITATION LOYALTY</p>
          <h2 className="text-[18px] font-bold text-[var(--color-home-text)] leading-snug">
            {CITATION_LOYALTY.headline}
          </h2>
          <p className="text-[13px] text-[var(--color-home-text-muted)] mt-1">
            {CITATION_LOYALTY.subtext}
          </p>
          <button type="button" onClick={onLearnMore} className="prep-link mt-3 text-left">
            Learn how verification improves learning →
          </button>
        </div>
        <div className="flex gap-6 md:gap-8 flex-shrink-0">
          {CITATION_LOYALTY.bySubject.map((s) => (
            <div key={s.label} className="text-center">
              <p
                className={`text-[22px] font-bold ${
                  s.tone === 'warning'
                    ? 'text-[#EA580C]'
                    : s.tone === 'good'
                      ? 'text-[#0F7A52]'
                      : 'text-[var(--color-home-text-muted)]'
                }`}
              >
                {s.pct}%
              </p>
              <p className="text-[10px] font-semibold tracking-wide text-[var(--color-home-label)] mt-0.5">
                {s.label}
              </p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
