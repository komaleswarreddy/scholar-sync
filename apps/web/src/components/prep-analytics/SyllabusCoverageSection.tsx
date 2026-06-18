'use client';

import { useState } from 'react';
import Link from 'next/link';
import { ChevronDown, ChevronUp } from 'lucide-react';
import type { ConceptTier } from '@/lib/analytics-prep-mock-data';
import { SYLLABUS_SUBJECTS } from '@/lib/analytics-prep-mock-data';

function tierClass(tier: ConceptTier): string {
  switch (tier) {
    case 'mastered':
      return 'prep-concept-card prep-concept-card--mastered';
    case 'in_progress':
      return 'prep-concept-card prep-concept-card--in-progress';
    case 'weak':
      return 'prep-concept-card prep-concept-card--weak';
    default:
      return 'prep-concept-card prep-concept-card--untouched';
  }
}

export function SyllabusCoverageSection() {
  const [expanded, setExpanded] = useState<Record<string, boolean>>(() =>
    Object.fromEntries(SYLLABUS_SUBJECTS.map((s) => [s.subject, true]))
  );

  const toggleSubject = (subject: string) => {
    setExpanded((prev) => ({ ...prev, [subject]: !prev[subject] }));
  };

  return (
    <div className="prep-card prep-syllabus-section mb-6">
      <div className="prep-syllabus-header">
        <div>
          <p className="prep-section-eyebrow">SYLLABUS COVERAGE & CONCEPT MASTERY</p>
          <p className="prep-syllabus-subtitle">
            See what is mastered, in progress, weak or untouched across each subject.
          </p>
        </div>
        <div className="prep-syllabus-legend">
          <span className="prep-syllabus-legend-item">
            <span className="prep-syllabus-legend-dot prep-syllabus-legend-dot--mastered" />
            Mastered
          </span>
          <span className="prep-syllabus-legend-item">
            <span className="prep-syllabus-legend-dot prep-syllabus-legend-dot--in-progress" />
            In Progress
          </span>
          <span className="prep-syllabus-legend-item">
            <span className="prep-syllabus-legend-dot prep-syllabus-legend-dot--weak" />
            Weak
          </span>
          <span className="prep-syllabus-legend-item">
            <span className="prep-syllabus-legend-dot prep-syllabus-legend-dot--untouched" />
            Untouched
          </span>
        </div>
      </div>

      <div className="prep-syllabus-subjects">
        {SYLLABUS_SUBJECTS.map((sub) => {
          const isOpen = expanded[sub.subject] ?? true;
          return (
            <div key={sub.subject} className="prep-syllabus-subject">
              <div className="prep-syllabus-subject-row">
                <p className="prep-syllabus-subject-name">{sub.subject}</p>
                <div className="prep-syllabus-bar-wrap">
                  <p className="prep-syllabus-summary">{sub.summary}</p>
                  <div className="prep-syllabus-bar">
                    <span
                      style={{ width: `${sub.segments.mastered}%`, background: '#064E3B' }}
                    />
                    <span
                      style={{ width: `${sub.segments.inProgress}%`, background: '#6BB89A' }}
                    />
                    <span style={{ width: `${sub.segments.weak}%`, background: '#F59E0B' }} />
                    <span
                      style={{ width: `${sub.segments.untouched}%`, background: '#E5E7EB' }}
                    />
                  </div>
                </div>
                <button
                  type="button"
                  onClick={() => toggleSubject(sub.subject)}
                  className="prep-syllabus-toggle"
                  aria-expanded={isOpen}
                  aria-label={`${isOpen ? 'Collapse' : 'Expand'} ${sub.subject}`}
                >
                  {isOpen ? (
                    <ChevronUp className="w-4 h-4" strokeWidth={2} />
                  ) : (
                    <ChevronDown className="w-4 h-4" strokeWidth={2} />
                  )}
                </button>
              </div>

              {isOpen && (
                <div className="prep-syllabus-concepts-wrap">
                  <p className="prep-syllabus-key-label">Key concepts</p>
                  <div className="prep-syllabus-concepts">
                    {sub.concepts.map((c) => (
                      <div key={c.name} className={`${tierClass(c.tier)} flex-shrink-0`}>
                        <span className="prep-concept-card-name">{c.name}</span>
                        <span className="prep-concept-card-pct">
                          {c.pct != null ? `${c.pct}%` : '—'}
                        </span>
                      </div>
                    ))}
                    <div className="prep-concept-card prep-concept-card--more flex-shrink-0">
                      <span className="prep-concept-card-more">+{sub.moreCount} more</span>
                    </div>
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>

      <div className="prep-syllabus-footer">
        <Link href="/analytics" className="prep-syllabus-map-link">
          View detailed syllabus map →
        </Link>
      </div>
    </div>
  );
}
