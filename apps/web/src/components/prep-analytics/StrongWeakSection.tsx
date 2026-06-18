'use client';

import { Target, TrendingUp } from 'lucide-react';
import { STRONG_TOPICS, WEAK_TOPICS } from '@/lib/analytics-prep-mock-data';

function TopicBars({
  items,
  barColor,
  metaColor,
}: {
  items: typeof STRONG_TOPICS;
  barColor: string;
  metaColor: string;
}) {
  return (
    <ul className="prep-strong-weak-list">
      {items.map((item, i) => (
        <li key={`${item.name}-${i}`} className="prep-strong-weak-item">
          <p className="prep-strong-weak-item-name">{item.name}</p>
          <p className="prep-strong-weak-item-meta" style={{ color: metaColor }}>
            {item.meta}
          </p>
          <div className="prep-strong-weak-item-row">
            <div className="prep-progress-bar prep-strong-weak-bar">
              <div
                className="prep-strong-weak-bar-fill"
                style={{ width: `${item.pct}%`, backgroundColor: barColor }}
              />
            </div>
            <span className="prep-strong-weak-item-pct">{item.pct}%</span>
          </div>
        </li>
      ))}
    </ul>
  );
}

export function StrongWeakSection() {
  return (
    <div className="prep-strong-weak-row mb-6">
      <div className="prep-card prep-strong-weak-card">
        <div className="prep-strong-weak-card-header">
          <p className="prep-strong-weak-header prep-strong-weak-header--strong">
            <TrendingUp className="w-4 h-4" strokeWidth={2.25} />
            STRONGEST
          </p>
          <p className="prep-strong-weak-subtitle">Topics where your mastery is highest</p>
        </div>
        <TopicBars items={STRONG_TOPICS} barColor="#0F7A52" metaColor="#0F7A52" />
      </div>

      <div className="prep-card prep-strong-weak-card">
        <div className="prep-strong-weak-card-header">
          <p className="prep-strong-weak-header prep-strong-weak-header--weak">
            <Target className="w-4 h-4" strokeWidth={2.25} />
            WEAK AREAS
          </p>
          <p className="prep-strong-weak-subtitle">Topics that need the most attention</p>
        </div>
        <TopicBars items={WEAK_TOPICS} barColor="#EA580C" metaColor="#EA580C" />
      </div>
    </div>
  );
}
