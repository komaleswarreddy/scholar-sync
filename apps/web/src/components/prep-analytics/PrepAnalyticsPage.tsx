'use client';

import { useState } from 'react';
import { ChevronDown, TrendingUp } from 'lucide-react';
import { HomeMobileNav } from '@/components/home/HomeMobileNav';
import { AiDisclaimerFooter } from '@/components/common/AiDisclaimerFooter';
import { ANALYTICS_FILTERS, ANALYTICS_KPIS } from '@/lib/analytics-prep-mock-data';
import { CitationLoyaltyBanner } from './CitationLoyaltyBanner';
import { KnowledgeGapSection } from './KnowledgeGapSection';
import { MasteryDecaySection } from './MasteryDecaySection';
import { RagInteractionSection } from './RagInteractionSection';
import { RecommendedSessionsSection } from './RecommendedSessionsSection';
import { ScoreTrendSection } from './ScoreTrendSection';
import { StrongWeakSection } from './StrongWeakSection';
import { StudioEngagementSection } from './StudioEngagementSection';
import { SyllabusCoverageSection } from './SyllabusCoverageSection';
import { VerificationLearnModal } from './VerificationLearnModal';

export function PrepAnalyticsPage() {
  const [subjectFilter, setSubjectFilter] = useState('All Subjects');
  const [periodFilter, setPeriodFilter] = useState('Last 30 days');
  const [verificationOpen, setVerificationOpen] = useState(false);

  return (
    <div className="prep-analytics-page max-w-7xl mx-auto px-4 md:px-8 pt-8 md:pt-10 pb-6">
      <HomeMobileNav />

          <header className="mb-6">
            <p className="text-[11px] font-semibold tracking-[0.14em] uppercase text-[var(--color-brand-text)] mb-2">
              ANALYTICS
            </p>
            <h1 className="text-[28px] sm:text-[32px] font-bold text-[var(--color-home-text)] tracking-tight leading-tight">
              Your preparation, mapped to the syllabus
            </h1>
            <p className="text-[15px] text-[var(--color-home-text-muted)] mt-2 max-w-2xl">
              Mastery, coverage, gaps, and study habits — built from your notebooks, tests, and
              tutor sessions.
            </p>
            <div className="flex flex-wrap gap-3 mt-4">
              <FilterSelect
                value={subjectFilter}
                options={ANALYTICS_FILTERS.subjects}
                onChange={setSubjectFilter}
              />
              <FilterSelect
                value={periodFilter}
                options={ANALYTICS_FILTERS.periods}
                onChange={setPeriodFilter}
              />
            </div>
          </header>

          <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4 mb-6">
            {ANALYTICS_KPIS.map((kpi) => (
              <div key={kpi.id} className="prep-card">
                <p className="text-[12px] font-semibold text-[var(--color-home-text-muted)]">
                  {kpi.label}
                </p>
                <p
                  className={`text-[28px] font-bold mt-1 ${
                    kpi.tone === 'warning' ? 'text-[#EA580C]' : 'text-[var(--color-home-text)]'
                  }`}
                >
                  {kpi.value}
                </p>
                {'delta' in kpi && kpi.delta && (
                  <p className="text-[12px] text-[var(--color-brand-text)] font-medium flex items-center gap-1 mt-1">
                    <TrendingUp className="w-3.5 h-3.5" />
                    {kpi.delta}
                  </p>
                )}
                {'sub' in kpi && kpi.sub && (
                  <p className="text-[12px] text-[var(--color-home-text-muted)] mt-1">{kpi.sub}</p>
                )}
                {'progress' in kpi && kpi.progress !== undefined && (
                  <div className="prep-progress-bar mt-2">
                    <div className="prep-progress-fill" style={{ width: `${kpi.progress}%` }} />
                  </div>
                )}
                {'sparkline' in kpi && kpi.sparkline && (
                  <div className="flex items-end gap-0.5 h-8 mt-2">
                    {kpi.sparkline.map((v, i) => (
                      <span
                        key={i}
                        className="flex-1 bg-[var(--color-brand-text)] rounded-sm opacity-70"
                        style={{ height: `${(v / 80) * 100}%` }}
                      />
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>

          <div className="prep-analytics-split-row mb-6">
            <ScoreTrendSection />
            <RecommendedSessionsSection />
          </div>

          <StrongWeakSection />

          <SyllabusCoverageSection />
          <KnowledgeGapSection />
          <MasteryDecaySection />

          <div className="prep-study-behavior-row mb-6">
            <RagInteractionSection />
            <StudioEngagementSection />
          </div>

          <CitationLoyaltyBanner onLearnMore={() => setVerificationOpen(true)} />
      <AiDisclaimerFooter />
      <VerificationLearnModal open={verificationOpen} onClose={() => setVerificationOpen(false)} />
    </div>
  );
}

function FilterSelect({
  value,
  options,
  onChange,
}: {
  value: string;
  options: readonly string[];
  onChange: (v: string) => void;
}) {
  return (
    <div className="relative">
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="library-sort-btn appearance-none pr-9 pl-4 py-2 text-[13px] font-medium cursor-pointer"
      >
        {options.map((o) => (
          <option key={o} value={o}>
            {o}
          </option>
        ))}
      </select>
      <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 pointer-events-none text-[var(--color-home-label)]" />
    </div>
  );
}
