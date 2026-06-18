'use client';

import { FileText, Shield, AlertTriangle } from 'lucide-react';
import { HOME_OVERVIEW_METRICS } from '@/lib/home-mock-data';

type Metric = (typeof HOME_OVERVIEW_METRICS)[number];

const statIcons = {
  document: FileText,
  shield: Shield,
  warning: AlertTriangle,
} as const;

const iconStyles = {
  document: {
    wrap: 'bg-[#E8F0FE]',
    icon: 'text-[#1A73E8]',
  },
  shield: {
    wrap: 'bg-[#E8F2EE]',
    icon: 'text-[#0D3D2E]',
  },
  warning: {
    wrap: 'bg-[#FFF4EC]',
    icon: 'text-[#EA580C]',
  },
} as const;

const footerToneClass = {
  green: 'text-[#0D3D2E] font-medium',
  orange: 'text-[#EA580C] font-medium',
  muted: 'text-[#6B7280]',
} as const;

export function OverviewMetricCard({ metric }: { metric: Metric }) {
  if (metric.type === 'ring') {
    const pct = metric.value;
    const circumference = 2 * Math.PI * 28;
    const offset = circumference - (pct / 100) * circumference;

    return (
      <div className="home-overview-card">
        <div className="flex items-center gap-3 flex-1 min-w-0">
          <div className="relative w-[64px] h-[64px] flex-shrink-0">
            <svg className="w-[64px] h-[64px] -rotate-90" viewBox="0 0 64 64">
              <circle cx="32" cy="32" r="28" fill="none" stroke="#E8EBE9" strokeWidth="5" />
              <circle
                cx="32"
                cy="32"
                r="28"
                fill="none"
                stroke="#0D3D2E"
                strokeWidth="5"
                strokeDasharray={circumference}
                strokeDashoffset={offset}
                strokeLinecap="round"
              />
            </svg>
            <span className="absolute inset-0 flex items-center justify-center text-[13px] font-bold text-[#0D3D2E]">
              {pct}%
            </span>
          </div>
          <div className="min-w-0 flex-1">
            <p className="text-[14px] font-bold text-[#1A1F1C] leading-tight">{metric.label}</p>
            <p className="text-[12px] text-[#6B7280] mt-0.5 leading-snug">{metric.subtitle}</p>
            <p className={`text-[11px] mt-1.5 ${footerToneClass[metric.footerTone]}`}>
              {metric.footer}
            </p>
          </div>
        </div>
      </div>
    );
  }

  const Icon = statIcons[metric.icon];
  const style = iconStyles[metric.icon];
  const footerClass =
    metric.footerTone === 'green'
      ? footerToneClass.green
      : metric.footerTone === 'orange'
        ? footerToneClass.orange
        : footerToneClass.muted;

  return (
    <div className="home-overview-card">
      <div className="flex items-center gap-3 flex-1 min-w-0">
        <div
          className={`w-[44px] h-[44px] rounded-full flex items-center justify-center flex-shrink-0 ${style.wrap}`}
        >
          <Icon className={`w-[18px] h-[18px] ${style.icon}`} strokeWidth={1.75} />
        </div>
        <div className="min-w-0 flex-1">
          <p className="text-[22px] font-bold text-[#1A1F1C] leading-none tracking-tight">
            {metric.value}
          </p>
          <p className="text-[14px] font-bold text-[#1A1F1C] mt-1 leading-tight">{metric.label}</p>
          <p className={`text-[11px] mt-1 ${footerClass}`}>{metric.detail}</p>
        </div>
      </div>
    </div>
  );
}
