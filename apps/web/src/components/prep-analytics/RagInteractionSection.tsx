'use client';

import { useState } from 'react';
import { Activity } from 'lucide-react';
import { RAG_INTERACTION } from '@/lib/analytics-prep-mock-data';

type RagFilter = 'all' | 'physics' | 'chemistry' | 'maths';

const BAR_COLOR = '#5F867E';
const MAX_DAY_COUNT = Math.max(...RAG_INTERACTION.questionsByDay.map((d) => d.count));
const MAX_CHAPTER_COUNT = Math.max(...RAG_INTERACTION.topChapters.map((c) => c.count));

export function RagInteractionSection() {
  const [filter, setFilter] = useState<RagFilter>('all');

  return (
    <div className="prep-card prep-rag-volume h-full flex flex-col">
      <div className="prep-study-card-header">
        <div>
          <p className="prep-section-eyebrow">RAG INTERACTION VOLUME</p>
          <h2 className="prep-section-title">Where your questions are going</h2>
        </div>
        <p className="prep-study-card-meta">
          <Activity className="w-3.5 h-3.5" strokeWidth={2} aria-hidden />
          {RAG_INTERACTION.queriesThisWeek} queries this week
        </p>
      </div>

      <div className="prep-rag-pills flex flex-wrap gap-2 mt-3">
        {(
          [
            ['all', 'ALL'],
            ['physics', 'PHYSICS'],
            ['chemistry', 'CHEMISTRY'],
            ['maths', 'MATHEMATICS'],
          ] as const
        ).map(([id, label]) => (
          <button
            key={id}
            type="button"
            onClick={() => setFilter(id)}
            className={`prep-trend-pill ${filter === id ? 'prep-trend-pill--active' : ''}`}
          >
            {label}
          </button>
        ))}
      </div>

      <div className="prep-rag-weekly-chart" aria-hidden>
        {RAG_INTERACTION.questionsByDay.map((d) => (
          <div key={d.day} className="prep-rag-weekly-col">
            <div className="prep-rag-weekly-bar-track">
              <div
                className="prep-rag-weekly-bar"
                style={{
                  height: `${(d.count / MAX_DAY_COUNT) * 100}%`,
                  backgroundColor: BAR_COLOR,
                }}
              />
            </div>
            <span className="prep-rag-weekly-label">{d.day}</span>
          </div>
        ))}
      </div>

      <p className="prep-study-subsection-label mt-5">TOP CHAPTERS BY QUERIES</p>
      <ul className="prep-rag-chapters">
        {RAG_INTERACTION.topChapters.map((chapter) => (
          <li key={chapter.name} className="prep-rag-chapter-row">
            <span className="prep-rag-chapter-name">{chapter.name}</span>
            <div className="prep-rag-chapter-bar-wrap">
              <div className="prep-rag-chapter-bar-track">
                <div
                  className="prep-rag-chapter-bar-fill"
                  style={{
                    width: `${(chapter.count / MAX_CHAPTER_COUNT) * 100}%`,
                    backgroundColor: BAR_COLOR,
                  }}
                />
              </div>
              <span className="prep-rag-chapter-count">{chapter.count}</span>
            </div>
          </li>
        ))}
      </ul>
    </div>
  );
}
