/**
 * KPI Metric Card Component
 * 
 * Reusable card component for displaying key performance indicators.
 */

'use client';

import { LucideIcon, TrendingUp, TrendingDown, Minus } from 'lucide-react';

export interface KPICardProps {
  title: string;
  value: string | number;
  trend?: {
    value: number;
    label?: string;
  };
  icon: LucideIcon;
  subtext?: string;
  className?: string;
  onClick?: () => void;
}

export function KPICard({
  title,
  value,
  trend,
  icon: Icon,
  subtext,
  className = '',
  onClick,
}: KPICardProps) {
  const formatValue = (val: string | number): string => {
    if (typeof val === 'number') {
      return new Intl.NumberFormat('en-US').format(val);
    }
    return val;
  };

  const getTrendIcon = () => {
    if (!trend) return null;
    if (trend.value > 0) {
      return <TrendingUp className="w-4 h-4 text-accent-green" />;
    } else if (trend.value < 0) {
      return <TrendingDown className="w-4 h-4 text-red-500" />;
    } else {
      return <Minus className="w-4 h-4 text-text-tertiary" />;
    }
  };

  const getTrendColor = () => {
    if (!trend) return '';
    if (trend.value > 0) {
      return 'text-accent-green';
    } else if (trend.value < 0) {
      return 'text-red-500';
    } else {
      return 'text-text-tertiary';
    }
  };

  return (
    <div 
      className={`bg-surface rounded-xl p-5 border border-border-default hover:border-accent-blue/30 transition-all duration-200 ${onClick ? 'cursor-pointer' : ''} ${className}`}
      onClick={onClick}
    >
      {/* Header with Icon and Title */}
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-accent-blue/10 flex items-center justify-center flex-shrink-0">
            <Icon className="w-5 h-5 text-accent-blue" />
          </div>
          <div>
            <h3 className="text-sm font-medium text-text-secondary">{title}</h3>
            {subtext && (
              <p className="text-xs text-text-tertiary mt-0.5">{subtext}</p>
            )}
          </div>
        </div>
      </div>

      {/* Value */}
      <div className="mb-2">
        <p className="text-3xl font-bold text-text-primary">
          {formatValue(value)}
        </p>
      </div>

      {/* Trend Indicator */}
      {trend && (
        <div className="flex items-center gap-1.5">
          {getTrendIcon()}
          <span className={`text-sm font-medium ${getTrendColor()}`}>
            {Math.abs(trend.value)}%
          </span>
          {trend.label && (
            <span className="text-xs text-text-tertiary">{trend.label}</span>
          )}
        </div>
      )}
    </div>
  );
}
