import type { HomeSummary } from '@/hooks/useHomeSummary';
import { HOME_OVERVIEW_METRICS } from '@/lib/home-mock-data';

export type HomeOverviewMetric = (typeof HOME_OVERVIEW_METRICS)[number];

export function mapHomeOverviewMetrics(summary: HomeSummary): HomeOverviewMetric[] {
  const m = summary.overview_metrics;
  return [
    {
      id: 'syllabus',
      type: 'ring' as const,
      label: 'Syllabus completion',
      value: m.syllabus_percent,
      subtitle: 'Across your notebooks',
      footer: `${m.syllabus_percent}% average mastery`,
      footerTone: 'green' as const,
    },
    {
      id: 'tests',
      type: 'stat' as const,
      label: 'Tests analyzed',
      value: String(m.tests_completed),
      detail: 'Across all subjects',
      icon: 'document' as const,
      footerTone: 'muted' as const,
    },
    {
      id: 'strong',
      type: 'stat' as const,
      label: 'Strong concepts',
      value: String(m.strong_concepts),
      detail: 'Keep building!',
      icon: 'shield' as const,
      footerTone: 'green' as const,
    },
    {
      id: 'attention',
      type: 'stat' as const,
      label: 'Need attention',
      value: String(m.needs_attention),
      detail: 'Focus and improve',
      icon: 'warning' as const,
      footerTone: 'orange' as const,
    },
  ];
}

export function subjectToIcon(subject: string): 'physics' | 'chemistry' | 'math' | 'biology' {
  const s = subject.toLowerCase();
  if (s.includes('chem')) return 'chemistry';
  if (s.includes('math')) return 'math';
  if (s.includes('bio')) return 'biology';
  return 'physics';
}
