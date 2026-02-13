/**
 * MetricCard Component
 * 
 * Reusable card component for displaying KPI metrics in the analytics dashboard.
 */

'use client';

import { ReactNode } from 'react';

interface MetricCardProps {
  title: string;
  value: string | number | null;
  icon?: ReactNode;
  isLoading?: boolean;
  error?: boolean;
  subtitle?: string;
  onClick?: () => void;
  details?: ReactNode;
}

export function MetricCard({ 
  title, 
  value, 
  icon, 
  isLoading = false, 
  error = false,
  subtitle,
  onClick,
  details
}: MetricCardProps) {
  return (
    <div 
      className={`bg-surface rounded-2xl border border-border-default p-6 transition-colors shadow-sm hover:shadow-md ${
        onClick ? 'cursor-pointer hover:border-border-active active:scale-[0.98]' : 'hover:border-border-active'
      }`}
      onClick={onClick}
    >
      <div className="flex items-start justify-between mb-4">
        <div className="flex-1">
          <h3 className="text-sm font-medium text-text-secondary mb-1">{title}</h3>
          {isLoading ? (
            <div className="h-8 w-24 bg-surface-hover rounded animate-pulse" />
          ) : error ? (
            <p className="text-lg font-semibold text-text-tertiary">Data unavailable</p>
          ) : (
            <p className="text-2xl font-bold text-text-primary">
              {value !== null && value !== undefined ? value : '—'}
            </p>
          )}
          {subtitle && !isLoading && !error && (
            <p className="text-xs text-text-tertiary mt-1">{subtitle}</p>
          )}
        </div>
        {icon && (
          <div className="text-text-secondary flex-shrink-0 ml-4">
            {icon}
          </div>
        )}
      </div>
      {details && (
        <div className="mt-4 pt-4 border-t border-border-default">
          {details}
        </div>
      )}
    </div>
  );
}
