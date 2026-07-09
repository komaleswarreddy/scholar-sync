/**
 * Queries Page
 * 
 * Admin page for viewing and analyzing queries.
 */

'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useAdminPortalApi } from '@/hooks/useAdminPortalApi';
import { adminQueryKeys } from '@/hooks/usePrefetchAdminData';
import { apiClient } from '@/lib/api-client';
import { Search, Loader2, Database, Clock, TrendingUp, AlertCircle } from 'lucide-react';
import { Input } from '@/components/ui/Input';
import { AdminTableSkeleton } from '@/components/skeleton';

export default function QueriesPage() {
  const { ready } = useAdminPortalApi();
  const [searchQuery, setSearchQuery] = useState('');

  const { data: metrics, isPending: loading, error: queryError } = useQuery({
    queryKey: adminQueryKeys.aggregateMetrics(30),
    queryFn: () => apiClient.getAggregateMetrics(30),
    enabled: ready,
    staleTime: 2 * 60 * 1000,
  });

  const error = queryError ? ((queryError as any)?.message || 'Failed to load queries data') : null;

  const formatNumber = (num: number | null | undefined) => {
    if (num === null || num === undefined) return '—';
    return new Intl.NumberFormat('en-US').format(num);
  };

  const formatPercentage = (num: number | null | undefined) => {
    if (num === null || num === undefined) return '—';
    return `${num.toFixed(1)}%`;
  };

  if (loading && !metrics) return <AdminTableSkeleton />;

  if (error) {
    return (
      <div className="h-full">
        <div className="mb-6">
          <h1 className="text-2xl font-semibold text-text-primary">Queries</h1>
          <p className="text-sm text-text-secondary mt-1">
            View and analyze all queries in the system
          </p>
        </div>
        <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-6">
          <p className="text-red-500">{error}</p>
        </div>
      </div>
    );
  }

  const summary = metrics?.metrics || {};
  const usage = metrics?.usage || {};
  const llmCalls = summary.llm_calls || {};
  const totalCalls = llmCalls.total || usage.total_calls || 0;
  const successfulCalls = llmCalls.successful || usage.successful_calls || 0;
  const failedCalls = llmCalls.failed || usage.failed_calls || 0;
  const successRate = totalCalls > 0 ? (successfulCalls / totalCalls) * 100 : 0;
  const failureRate = totalCalls > 0 ? (failedCalls / totalCalls) * 100 : 0;

  return (
    <div className="h-full">
      <div className="mb-6">
        <h1 className="text-2xl font-semibold text-text-primary">Queries</h1>
        <p className="text-sm text-text-secondary mt-1">
          View and analyze all queries in the system
        </p>
      </div>

      {/* Statistics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <div className="bg-surface rounded-xl border border-border-default p-5">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-10 h-10 rounded-lg bg-accent-blue/10 flex items-center justify-center">
              <Database className="w-5 h-5 text-accent-blue" />
            </div>
            <div>
              <h3 className="text-sm font-medium text-text-secondary">Total Queries</h3>
            </div>
          </div>
          <p className="text-3xl font-bold text-text-primary">{formatNumber(totalCalls)}</p>
        </div>

        <div className="bg-surface rounded-xl border border-border-default p-5">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-10 h-10 rounded-lg bg-green-500/10 flex items-center justify-center">
              <TrendingUp className="w-5 h-5 text-green-500" />
            </div>
            <div>
              <h3 className="text-sm font-medium text-text-secondary">Successful</h3>
            </div>
          </div>
          <p className="text-3xl font-bold text-text-primary">{formatNumber(successfulCalls)}</p>
          <p className="text-xs text-text-tertiary mt-1">{formatPercentage(successRate)} success rate</p>
        </div>

        <div className="bg-surface rounded-xl border border-border-default p-5">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-10 h-10 rounded-lg bg-red-500/10 flex items-center justify-center">
              <AlertCircle className="w-5 h-5 text-red-500" />
            </div>
            <div>
              <h3 className="text-sm font-medium text-text-secondary">Failed</h3>
            </div>
          </div>
          <p className="text-3xl font-bold text-text-primary">{formatNumber(failedCalls)}</p>
          <p className="text-xs text-text-tertiary mt-1">{formatPercentage(failureRate)} failure rate</p>
        </div>

        <div className="bg-surface rounded-xl border border-border-default p-5">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-10 h-10 rounded-lg bg-yellow-500/10 flex items-center justify-center">
              <Clock className="w-5 h-5 text-yellow-500" />
            </div>
            <div>
              <h3 className="text-sm font-medium text-text-secondary">Avg Latency</h3>
            </div>
          </div>
          <p className="text-3xl font-bold text-text-primary">
            {summary.latency?.average ? `${summary.latency.average.toFixed(0)}ms` : '—'}
          </p>
        </div>

        <div className="bg-surface rounded-xl border border-border-default p-5">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-10 h-10 rounded-lg bg-orange-500/10 flex items-center justify-center">
              <AlertCircle className="w-5 h-5 text-orange-500" />
            </div>
            <div>
              <h3 className="text-sm font-medium text-text-secondary">No Answer</h3>
            </div>
          </div>
          <p className="text-3xl font-bold text-text-primary">
            {formatNumber(usage.no_answer_calls || 0)}
          </p>
          <p className="text-xs text-text-tertiary mt-1">
            {totalCalls > 0 
              ? formatPercentage((usage.no_answer_calls || 0) / totalCalls * 100)
              : '0%'} of queries
          </p>
        </div>
      </div>

      {/* Detailed Metrics Table */}
      <div className="bg-surface rounded-2xl border border-border-default p-6">
        <h2 className="text-lg font-semibold text-text-primary mb-4">Query Statistics</h2>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-surface-hover border-b border-border-default">
              <tr>
                <th className="px-4 py-3 text-left text-sm font-semibold text-text-primary">Metric</th>
                <th className="px-4 py-3 text-left text-sm font-semibold text-text-primary">Value</th>
                <th className="px-4 py-3 text-left text-sm font-semibold text-text-primary">Percentage</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border-default">
              <tr>
                <td className="px-4 py-3 text-text-primary font-medium">Total Queries</td>
                <td className="px-4 py-3 text-text-primary">{formatNumber(totalCalls)}</td>
                <td className="px-4 py-3 text-text-secondary">100%</td>
              </tr>
              <tr>
                <td className="px-4 py-3 text-text-primary font-medium">Successful Queries</td>
                <td className="px-4 py-3 text-text-primary">{formatNumber(successfulCalls)}</td>
                <td className="px-4 py-3 text-green-500">{formatPercentage(successRate)}</td>
              </tr>
              <tr>
                <td className="px-4 py-3 text-text-primary font-medium">Failed Queries</td>
                <td className="px-4 py-3 text-text-primary">{formatNumber(failedCalls)}</td>
                <td className="px-4 py-3 text-red-500">{formatPercentage(failureRate)}</td>
              </tr>
              <tr>
                <td className="px-4 py-3 text-text-primary font-medium">No Answer Cases</td>
                <td className="px-4 py-3 text-text-primary">{formatNumber(usage.no_answer_calls || 0)}</td>
                <td className="px-4 py-3 text-orange-500">
                  {totalCalls > 0 
                    ? formatPercentage((usage.no_answer_calls || 0) / totalCalls * 100)
                    : '0%'}
                </td>
              </tr>
              <tr>
                <td className="px-4 py-3 text-text-primary font-medium">Total Tokens</td>
                <td className="px-4 py-3 text-text-primary">{formatNumber(summary.tokens?.total || usage.total_tokens)}</td>
                <td className="px-4 py-3 text-text-secondary">—</td>
              </tr>
              <tr>
                <td className="px-4 py-3 text-text-primary font-medium">Average Tokens per Query</td>
                <td className="px-4 py-3 text-text-primary">
                  {totalCalls > 0 ? formatNumber(Math.round((summary.tokens?.total || usage.total_tokens || 0) / totalCalls)) : '—'}
                </td>
                <td className="px-4 py-3 text-text-secondary">—</td>
              </tr>
              <tr>
                <td className="px-4 py-3 text-text-primary font-medium">Total Cost</td>
                <td className="px-4 py-3 text-text-primary">
                  {summary.costs?.total || usage.total_cost 
                    ? `$${(summary.costs?.total || usage.total_cost).toFixed(4)}`
                    : '—'}
                </td>
                <td className="px-4 py-3 text-text-secondary">—</td>
              </tr>
              <tr>
                <td className="px-4 py-3 text-text-primary font-medium">Average Cost per Query</td>
                <td className="px-4 py-3 text-text-primary">
                  {totalCalls > 0 && (summary.costs?.total || usage.total_cost)
                    ? `$${((summary.costs?.total || usage.total_cost) / totalCalls).toFixed(6)}`
                    : '—'}
                </td>
                <td className="px-4 py-3 text-text-secondary">—</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}