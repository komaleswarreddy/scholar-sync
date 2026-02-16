/**
 * Guardrails Page
 * 
 * Admin page for managing guardrails and safety measures.
 */

'use client';

import { useEffect, useState } from 'react';
import { useAuth } from '@clerk/nextjs';
import { apiClient } from '@/lib/api-client';
import { Loader2, Shield, AlertTriangle, CheckCircle2 } from 'lucide-react';

export default function GuardrailsPage() {
  const { getToken } = useAuth();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [metrics, setMetrics] = useState<any>(null);

  useEffect(() => {
    const fetchData = async () => {
      if (!getToken) return;
      
      setLoading(true);
      setError(null);
      
      try {
        apiClient.setTokenGetter(getToken);
        const data = await apiClient.getAggregateMetrics(30);
        setMetrics(data);
      } catch (err: any) {
        console.error('[Guardrails] Failed to fetch data:', err);
        setError(err?.message || 'Failed to load guardrails data');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [getToken]);

  const formatNumber = (num: number | null | undefined) => {
    if (num === null || num === undefined) return '—';
    return new Intl.NumberFormat('en-US').format(num);
  };

  const formatPercentage = (num: number | null | undefined) => {
    if (num === null || num === undefined) return '—';
    return `${num.toFixed(2)}%`;
  };

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-8 h-8 animate-spin text-accent-blue mx-auto mb-4" />
          <p className="text-text-secondary">Loading guardrails data...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="h-full">
        <div className="mb-6">
          <h1 className="text-2xl font-semibold text-text-primary">Guardrails</h1>
          <p className="text-sm text-text-secondary mt-1">
            Manage guardrails and safety measures
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
  const guardrails = metrics?.guardrails || {};
  const totalBlocks = guardrails.blocks || 0;
  const totalCalls = summary.llm_calls?.total || usage.total_calls || 0;
  const blockRate = totalCalls > 0 ? (totalBlocks / totalCalls) * 100 : 0;

  return (
    <div className="h-full">
      <div className="mb-6">
        <h1 className="text-2xl font-semibold text-text-primary">Guardrails</h1>
        <p className="text-sm text-text-secondary mt-1">
          Manage guardrails and safety measures
        </p>
      </div>

      {/* Statistics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
        <div className="bg-surface rounded-xl border border-border-default p-5">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-10 h-10 rounded-lg bg-red-500/10 flex items-center justify-center">
              <Shield className="w-5 h-5 text-red-500" />
            </div>
            <div>
              <h3 className="text-sm font-medium text-text-secondary">Total Blocks</h3>
            </div>
          </div>
          <p className="text-3xl font-bold text-text-primary">{formatNumber(totalBlocks)}</p>
          <p className="text-xs text-text-tertiary mt-1">Requests blocked by guardrails</p>
        </div>

        <div className="bg-surface rounded-xl border border-border-default p-5">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-10 h-10 rounded-lg bg-yellow-500/10 flex items-center justify-center">
              <AlertTriangle className="w-5 h-5 text-yellow-500" />
            </div>
            <div>
              <h3 className="text-sm font-medium text-text-secondary">Block Rate</h3>
            </div>
          </div>
          <p className="text-3xl font-bold text-text-primary">{formatPercentage(blockRate)}</p>
          <p className="text-xs text-text-tertiary mt-1">Percentage of requests blocked</p>
        </div>

        <div className="bg-surface rounded-xl border border-border-default p-5">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-10 h-10 rounded-lg bg-green-500/10 flex items-center justify-center">
              <CheckCircle2 className="w-5 h-5 text-green-500" />
            </div>
            <div>
              <h3 className="text-sm font-medium text-text-secondary">Total Requests</h3>
            </div>
          </div>
          <p className="text-3xl font-bold text-text-primary">{formatNumber(totalCalls)}</p>
          <p className="text-xs text-text-tertiary mt-1">All API requests</p>
        </div>
      </div>

      {/* Guardrails Information */}
      <div className="bg-surface rounded-2xl border border-border-default p-6">
        <h2 className="text-lg font-semibold text-text-primary mb-4">Guardrails Overview</h2>
        <div className="space-y-4">
          <div className="bg-surface-hover rounded-lg p-4 border border-border-default">
            <h3 className="text-sm font-semibold text-text-primary mb-2">Cost Guardrails</h3>
            <p className="text-sm text-text-secondary">
              Monitor and control costs by setting limits on token usage and API calls per user or tenant.
            </p>
          </div>
          <div className="bg-surface-hover rounded-lg p-4 border border-border-default">
            <h3 className="text-sm font-semibold text-text-primary mb-2">Rate Limiting</h3>
            <p className="text-sm text-text-secondary">
              Prevent abuse by limiting the number of requests per user within a time window.
            </p>
          </div>
          <div className="bg-surface-hover rounded-lg p-4 border border-border-default">
            <h3 className="text-sm font-semibold text-text-primary mb-2">Content Filtering</h3>
            <p className="text-sm text-text-secondary">
              Block inappropriate or harmful content from being processed or returned.
            </p>
          </div>
        </div>
      </div>

      {/* Statistics Table */}
      <div className="bg-surface rounded-2xl border border-border-default p-6 mt-6">
        <h2 className="text-lg font-semibold text-text-primary mb-4">Guardrails Statistics</h2>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-surface-hover border-b border-border-default">
              <tr>
                <th className="px-4 py-3 text-left text-sm font-semibold text-text-primary">Metric</th>
                <th className="px-4 py-3 text-left text-sm font-semibold text-text-primary">Value</th>
                <th className="px-4 py-3 text-left text-sm font-semibold text-text-primary">Description</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border-default">
              <tr>
                <td className="px-4 py-3 text-text-primary font-medium">Total Blocks</td>
                <td className="px-4 py-3 text-text-primary">{formatNumber(totalBlocks)}</td>
                <td className="px-4 py-3 text-text-secondary">Total number of requests blocked by guardrails</td>
              </tr>
              <tr>
                <td className="px-4 py-3 text-text-primary font-medium">Block Rate</td>
                <td className="px-4 py-3 text-text-primary">{formatPercentage(blockRate)}</td>
                <td className="px-4 py-3 text-text-secondary">Percentage of requests that were blocked</td>
              </tr>
              <tr>
                <td className="px-4 py-3 text-text-primary font-medium">Total Requests</td>
                <td className="px-4 py-3 text-text-primary">{formatNumber(totalCalls)}</td>
                <td className="px-4 py-3 text-text-secondary">Total number of API requests processed</td>
              </tr>
              <tr>
                <td className="px-4 py-3 text-text-primary font-medium">Allowed Requests</td>
                <td className="px-4 py-3 text-text-primary">{formatNumber(totalCalls - totalBlocks)}</td>
                <td className="px-4 py-3 text-text-secondary">Requests that passed guardrail checks</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      {/* Guardrail User Blocks Table */}
      <div className="bg-surface rounded-2xl border border-border-default p-6 mt-6">
        <h2 className="text-lg font-semibold text-text-primary mb-4">Users with High Block Count</h2>
        <p className="text-sm text-text-secondary mb-4">
          Users with more than 3 guardrail blocks (user name, ID, and session ID)
        </p>
        <div className="bg-surface-hover rounded-xl border border-border-default overflow-hidden">
          <table className="w-full">
            <thead className="bg-surface border-b border-border-default">
              <tr>
                <th className="px-4 py-3 text-left text-sm font-semibold text-text-primary">User Name</th>
                <th className="px-4 py-3 text-left text-sm font-semibold text-text-primary">User ID</th>
                <th className="px-4 py-3 text-left text-sm font-semibold text-text-primary">Session ID</th>
                <th className="px-4 py-3 text-left text-sm font-semibold text-text-primary">Block Count</th>
                <th className="px-4 py-3 text-left text-sm font-semibold text-text-primary">Block Reason</th>
                <th className="px-4 py-3 text-right text-sm font-semibold text-text-primary">Last Updated</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border-default">
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center text-text-tertiary">
                  No guardrail user block data available yet. Data will appear here when users exceed 3 blocks.
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
