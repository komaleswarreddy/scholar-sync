'use client';

import { BookOpen } from 'lucide-react';
import { STUDIO_ENGAGEMENT } from '@/lib/analytics-prep-mock-data';

const SEGMENT_ORDER = ['physics', 'chemistry', 'maths'] as const;

export function StudioEngagementSection() {
  const { maxUses, subjectColors, tools, legend } = STUDIO_ENGAGEMENT;

  return (
    <div className="prep-card prep-studio-engagement h-full flex flex-col">
      <div className="prep-study-card-header">
        <div>
          <p className="prep-section-eyebrow">STUDIO ENGAGEMENT</p>
          <h2 className="prep-section-title">Which study tools you reach for</h2>
        </div>
        <p className="prep-study-card-meta">
          <BookOpen className="w-3.5 h-3.5" strokeWidth={2} aria-hidden />
          per subject
        </p>
      </div>

      <ul className="prep-studio-tools flex-1 mt-4">
        {tools.map((tool) => (
          <li key={tool.name} className="prep-studio-tool-row">
            <div className="prep-studio-tool-labels">
              <span className="prep-studio-tool-name">{tool.name}</span>
              <span className="prep-studio-tool-uses">{tool.uses} uses</span>
            </div>
            <div className="prep-studio-bar-track">
              <div
                className="prep-studio-bar-fill"
                style={{ width: `${(tool.uses / maxUses) * 100}%` }}
              >
                {SEGMENT_ORDER.map((key) => (
                  <span
                    key={key}
                    className="prep-studio-bar-segment"
                    style={{
                      width: `${(tool.segments[key] / tool.uses) * 100}%`,
                      backgroundColor: subjectColors[key],
                    }}
                  />
                ))}
              </div>
            </div>
          </li>
        ))}
      </ul>

      <div className="prep-studio-legend">
        {legend.map((item) => (
          <span key={item.key} className="prep-studio-legend-item">
            <span
              className="prep-studio-legend-dot"
              style={{ backgroundColor: subjectColors[item.key] }}
            />
            {item.label}
          </span>
        ))}
      </div>
    </div>
  );
}
