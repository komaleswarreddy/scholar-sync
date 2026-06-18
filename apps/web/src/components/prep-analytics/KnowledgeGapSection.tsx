'use client';

import { useRouter } from 'next/navigation';
import { AlertTriangle } from 'lucide-react';
import { ACTION_REQUIRED_GAPS, GAP_SCATTER_POINTS } from '@/lib/analytics-prep-mock-data';

const W = 1000;
const H = 436;
const PL = 0;
const PR = 0;
const PT = 28;
const PB = 24;
const INNER_W = W - PL - PR;
const INNER_H = H - PT - PB;
const MID_X = PL + INNER_W / 2;
const MID_Y = PT + INNER_H / 2;
const DOT_R = 4;

function toSvg(xPct: number, yPct: number) {
  return {
    cx: PL + (xPct / 100) * INNER_W,
    cy: PT + (yPct / 100) * INNER_H,
  };
}

function dotFill(tone: 'orange' | 'green'): string {
  return tone === 'green' ? '#1F5B50' : '#D97706';
}

export function KnowledgeGapSection() {
  const router = useRouter();

  return (
    <div className="prep-card prep-gap-section mb-6">
      <p className="prep-section-eyebrow">KNOWLEDGE GAP ISOLATION</p>
      <h2 className="prep-section-title">
        High questions, low scores — the illusion of competence
      </h2>
      <p className="text-[13px] text-[var(--color-home-text-muted)] mt-2 max-w-3xl leading-relaxed">
        Each dot is a chapter. X = how often you queried the tutor. Y = your latest quiz score.
        The top-left quadrant is where you read a lot but don&apos;t retain.
      </p>

      <div className="prep-action-required mt-4 mb-4">
        <p className="prep-action-required-title">
          <AlertTriangle className="w-4 h-4 shrink-0" aria-hidden />
          ACTION REQUIRED · {ACTION_REQUIRED_GAPS.length} CHAPTERS
        </p>
        <div className="prep-action-cards-grid mt-4">
          {ACTION_REQUIRED_GAPS.map((item) => (
            <div key={item.id} className="prep-action-card">
              <div className="min-w-0 flex-1 pr-2">
                <p className="text-[13px] font-bold text-[var(--color-home-text)] leading-snug">
                  {item.topic}
                </p>
                <p className="text-[11px] text-[var(--color-home-text-muted)] mt-0.5">
                  {item.subject} · {item.queries}q · {item.score}%
                </p>
              </div>
              <button
                type="button"
                onClick={() => router.push(item.focusHref)}
                className="prep-action-focus"
              >
                Start recall ↗
              </button>
            </div>
          ))}
        </div>
      </div>

      <GapScatterPlot onDotClick={(href) => router.push(href)} />
    </div>
  );
}

function ScatterDot({
  p,
  onDotClick,
}: {
  p: (typeof GAP_SCATTER_POINTS)[number];
  onDotClick: (href: string) => void;
}) {
  const { cx, cy } = toSvg(p.x, p.y);
  const fill = dotFill(p.tone);

  if (!p.focusHref) {
    return <circle cx={cx} cy={cy} r={DOT_R} fill={fill} aria-hidden />;
  }

  return (
    <circle
      cx={cx}
      cy={cy}
      r={DOT_R}
      fill={fill}
      className="prep-scatter-dot"
      onClick={() => onDotClick(p.focusHref!)}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') onDotClick(p.focusHref!);
      }}
      aria-label={p.topic}
    />
  );
}

function GapScatterPlot({ onDotClick }: { onDotClick: (href: string) => void }) {
  const halfW = INNER_W / 2;
  const halfH = INNER_H / 2;

  return (
    <div className="prep-scatter">
      <svg
        viewBox={`0 0 ${W} ${H}`}
        preserveAspectRatio="xMidYMid meet"
        className="prep-scatter-svg"
        role="img"
        aria-label="Knowledge gap quadrant chart"
      >
        <rect x={PL} y={PT} width={halfW} height={halfH} fill="rgba(245, 158, 11, 0.03)" />
        <rect x={MID_X} y={MID_Y} width={halfW} height={halfH} fill="rgba(34, 197, 94, 0.03)" />

        <line
          x1={MID_X}
          y1={PT}
          x2={MID_X}
          y2={PT + INNER_H}
          stroke="#E5E7EB"
          strokeWidth={1}
          strokeDasharray="4 4"
        />
        <line
          x1={PL}
          y1={MID_Y}
          x2={PL + INNER_W}
          y2={MID_Y}
          stroke="#E5E7EB"
          strokeWidth={1}
          strokeDasharray="4 4"
        />

        <text x={PL + 4} y={PT + 12} className="prep-scatter-svg-label prep-scatter-svg-label--illusion">
          ILLUSION OF COMPETENCE
        </text>
        <text
          x={PL + INNER_W - 4}
          y={PT + 12}
          textAnchor="end"
          className="prep-scatter-svg-label prep-scatter-svg-label--muted"
        >
          ENGAGED &amp; MASTERING
        </text>
        <text x={PL + 4} y={PT + INNER_H - 4} className="prep-scatter-svg-label prep-scatter-svg-label--muted">
          LOW TOUCH · LOW SCORE
        </text>
        <text
          x={PL + INNER_W - 4}
          y={PT + INNER_H - 4}
          textAnchor="end"
          className="prep-scatter-svg-label prep-scatter-svg-label--strong"
        >
          STRONG &amp; QUIET
        </text>

        {GAP_SCATTER_POINTS.map((p) => (
          <ScatterDot key={p.id} p={p} onDotClick={onDotClick} />
        ))}

        <text x={PL + 2} y={H - 6} className="prep-scatter-svg-axis">
          ← fewer queries
        </text>
        <text x={PL + INNER_W - 2} y={H - 6} textAnchor="end" className="prep-scatter-svg-axis">
          RAG queries →
        </text>
      </svg>
    </div>
  );
}
