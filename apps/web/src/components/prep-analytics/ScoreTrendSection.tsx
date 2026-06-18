'use client';

import { useMemo, useState } from 'react';
import { SCORE_TREND } from '@/lib/analytics-prep-mock-data';

type TrendFilter = 'all' | 'physics' | 'chemistry' | 'maths';

const CHART_W = 640;
const CHART_H = 360;
const PAD = { top: 16, right: 16, bottom: 32, left: 40 };

function buildPath(values: (number | null)[], datesLen: number): string | null {
  const innerW = CHART_W - PAD.left - PAD.right;
  const innerH = CHART_H - PAD.top - PAD.bottom;
  const points: string[] = [];
  values.forEach((v, i) => {
    if (v == null) return;
    const x = PAD.left + (i / (datesLen - 1)) * innerW;
    const y = PAD.top + innerH - (v / 100) * innerH;
    points.push(`${points.length === 0 ? 'M' : 'L'} ${x.toFixed(1)} ${y.toFixed(1)}`);
  });
  return points.length ? points.join(' ') : null;
}

export function ScoreTrendSection() {
  const [filter, setFilter] = useState<TrendFilter>('all');
  const dates = SCORE_TREND.dates;

  const series = useMemo(
    () => [
      {
        id: 'physics' as const,
        color: '#2D4A3E',
        values: SCORE_TREND.physics,
        visible: filter === 'all' || filter === 'physics',
      },
      {
        id: 'chemistry' as const,
        color: '#E68A00',
        values: SCORE_TREND.chemistry,
        visible: filter === 'all' || filter === 'chemistry',
      },
      {
        id: 'maths' as const,
        color: '#28A745',
        values: SCORE_TREND.maths,
        visible: filter === 'all' || filter === 'maths',
      },
    ],
    [filter]
  );

  const yTicks = [0, 25, 50, 75, 100];
  const innerW = CHART_W - PAD.left - PAD.right;
  const innerH = CHART_H - PAD.top - PAD.bottom;

  return (
    <div className="prep-card prep-score-trend h-full flex flex-col">
      <div className="prep-score-trend-header mb-3">
        <div>
          <p className="prep-section-eyebrow">QUIZ PROGRESS & PERFORMANCE</p>
          <h2 className="prep-section-title">Score trend · per subject</h2>
        </div>
        <div className="prep-score-trend-pills flex flex-wrap gap-2">
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
      </div>

      <div className="prep-line-chart-wrap flex-1 min-h-0 flex flex-col">
        <svg
          viewBox={`0 0 ${CHART_W} ${CHART_H}`}
          className="prep-score-trend-chart"
          preserveAspectRatio="xMidYMid meet"
          role="img"
          aria-label="Score trend line chart"
        >
          {yTicks.map((tick) => {
            const y = PAD.top + innerH - (tick / 100) * innerH;
            return (
              <g key={tick}>
                <line
                  x1={PAD.left}
                  y1={y}
                  x2={CHART_W - PAD.right}
                  y2={y}
                  stroke="#E8EBE9"
                  strokeWidth={1}
                />
                <text x={4} y={y + 4} fontSize={10} fill="#9CA3AF">
                  {tick}%
                </text>
              </g>
            );
          })}
          {dates.map((d, i) => {
            const x = PAD.left + (i / (dates.length - 1)) * innerW;
            return (
              <text
                key={d}
                x={x}
                y={CHART_H - 6}
                fontSize={10}
                fill="#9CA3AF"
                textAnchor="middle"
              >
                {d}
              </text>
            );
          })}
          {series.map(
            (s) =>
              s.visible && (
                <g key={s.id}>
                  {buildPath(s.values, dates.length) && (
                    <path
                      d={buildPath(s.values, dates.length)!}
                      fill="none"
                      stroke={s.color}
                      strokeWidth={2.5}
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  )}
                  {s.values.map((v, i) => {
                    if (v == null) return null;
                    const x = PAD.left + (i / (dates.length - 1)) * innerW;
                    const y = PAD.top + innerH - (v / 100) * innerH;
                    return (
                      <circle key={i} cx={x} cy={y} r={4} fill={s.color} stroke="#fff" strokeWidth={1.5} />
                    );
                  })}
                </g>
              )
          )}
        </svg>
        <div className="prep-score-trend-legend">
          {SCORE_TREND.summaries.map((s) => (
            <span
              key={s.id}
              className={`prep-score-trend-legend-item ${filter !== 'all' && filter !== s.id ? 'prep-score-trend-legend-item--dim' : ''}`}
            >
              <span className="prep-score-trend-legend-dot" style={{ backgroundColor: s.color }} />
              {s.label.charAt(0) + s.label.slice(1).toLowerCase()} {s.avg}%
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}
