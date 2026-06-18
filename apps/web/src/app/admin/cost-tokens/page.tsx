/**
 * Cost & Tokens Page
 * 
 * Admin page for viewing detailed cost and token usage analytics.
 */

'use client';

import { useEffect, useState } from 'react';
import { useAdminPortalApi } from '@/hooks/useAdminPortalApi';
import { apiClient } from '@/lib/api-client';
import { Loader2, DollarSign, TrendingUp, Database, Users, Zap } from 'lucide-react';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  Filler,
} from 'chart.js';
import { Line, Bar } from 'react-chartjs-2';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  BarElement,
  Title,
  Tooltip,
  Legend,
  Filler
);

export default function CostTokensPage() {
  const { ready } = useAdminPortalApi();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [costData, setCostData] = useState<any>(null);
  const [tokenData, setTokenData] = useState<any>(null);

  useEffect(() => {
    const fetchData = async () => {
      if (!ready) return;
      
      setLoading(true);
      setError(null);
      
      try {
        const [cost, tokens] = await Promise.all([
          apiClient.getCostTracking(30, true),
          apiClient.getTokenConsumption(30, 'feature'),
        ]);
        setCostData(cost);
        setTokenData(tokens);
      } catch (err: any) {
        console.error('[Cost] Failed to fetch data:', err);
        setError(err?.message || 'Failed to load cost data');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [ready]);

  const formatNumber = (num: number | null | undefined) => {
    if (num === null || num === undefined) return '—';
    return new Intl.NumberFormat('en-US').format(num);
  };

  const formatCurrency = (num: number | null | undefined) => {
    if (num === null || num === undefined) return '—';
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 4,
      maximumFractionDigits: 4,
    }).format(num);
  };

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-8 h-8 animate-spin text-accent-blue mx-auto mb-4" />
          <p className="text-text-secondary">Loading cost data...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="h-full">
        <div className="mb-6">
          <h1 className="text-2xl font-semibold text-text-primary">Cost & Tokens</h1>
          <p className="text-sm text-text-secondary mt-1">
            View detailed cost and token usage analytics
          </p>
        </div>
        <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-6">
          <p className="text-red-500">{error}</p>
        </div>
      </div>
    );
  }

  const costSummary = costData?.summary || {};
  const tokenSummary = tokenData?.summary || {};
  const dailyCostBreakdown = costData?.daily_breakdown || [];
  const userCostBreakdown = costData?.user_breakdown || [];
  const modelCostBreakdown = costData?.model_breakdown || [];
  const tokenBreakdown = tokenData?.breakdown || [];
  const dailyTokenBreakdown = tokenData?.daily_breakdown || [];

  // Cost Chart Data
  const costChartData = {
    labels: dailyCostBreakdown.map((item: any) => {
      const date = new Date(item.date);
      return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    }),
    datasets: [
      {
        label: 'Daily Cost',
        data: dailyCostBreakdown.map((item: any) => item.cost || 0),
        borderColor: '#34A853',
        backgroundColor: 'rgba(52, 168, 83, 0.1)',
        fill: true,
        tension: 0.4,
      },
    ],
  };

  // Token Chart Data
  const tokenChartData = {
    labels: dailyTokenBreakdown.map((item: any) => {
      const date = new Date(item.date);
      return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    }),
    datasets: [
      {
        label: 'Tokens',
        data: dailyTokenBreakdown.map((item: any) => item.tokens || 0),
        borderColor: '#FBBC04',
        backgroundColor: 'rgba(251, 188, 4, 0.1)',
        fill: true,
        tension: 0.4,
      },
    ],
  };

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        display: false,
      },
      tooltip: {
        backgroundColor: 'rgba(0, 0, 0, 0.8)',
        padding: 12,
      },
    },
    scales: {
      x: {
        grid: { display: false },
        ticks: { color: '#9AA0A6', font: { size: 12 } },
      },
      y: {
        grid: { color: 'rgba(255, 255, 255, 0.05)' },
        ticks: { color: '#9AA0A6', font: { size: 12 } },
      },
    },
  };

  return (
    <div className="h-full">
      <div className="mb-6">
        <h1 className="text-2xl font-semibold text-text-primary">Cost & Tokens</h1>
        <p className="text-sm text-text-secondary mt-1">
          View detailed cost and token usage analytics
        </p>
      </div>

      {/* Statistics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <div className="bg-surface rounded-xl border border-border-default p-5">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-10 h-10 rounded-lg bg-green-500/10 flex items-center justify-center">
              <DollarSign className="w-5 h-5 text-green-500" />
            </div>
            <div>
              <h3 className="text-sm font-medium text-text-secondary">Total Cost</h3>
            </div>
          </div>
          <p className="text-3xl font-bold text-text-primary">
            {formatCurrency(costSummary.total_cost)}
          </p>
          <p className="text-xs text-text-tertiary mt-1">
            Avg: {formatCurrency(costSummary.daily_avg_cost)}/day
          </p>
        </div>

        <div className="bg-surface rounded-xl border border-border-default p-5">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-10 h-10 rounded-lg bg-yellow-500/10 flex items-center justify-center">
              <Zap className="w-5 h-5 text-yellow-500" />
            </div>
            <div>
              <h3 className="text-sm font-medium text-text-secondary">Total Tokens</h3>
            </div>
          </div>
          <p className="text-3xl font-bold text-text-primary">
            {formatNumber(tokenSummary.total_tokens)}
          </p>
          <p className="text-xs text-text-tertiary mt-1">
            Avg: {formatNumber(tokenSummary.avg_tokens_per_call)} per call
          </p>
        </div>

        <div className="bg-surface rounded-xl border border-border-default p-5">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-10 h-10 rounded-lg bg-blue-500/10 flex items-center justify-center">
              <Database className="w-5 h-5 text-blue-500" />
            </div>
            <div>
              <h3 className="text-sm font-medium text-text-secondary">Total Calls</h3>
            </div>
          </div>
          <p className="text-3xl font-bold text-text-primary">
            {formatNumber(costSummary.total_calls || tokenSummary.total_calls)}
          </p>
          <p className="text-xs text-text-tertiary mt-1">
            Avg cost: {formatCurrency(costSummary.avg_cost_per_call)}/call
          </p>
        </div>

        <div className="bg-surface rounded-xl border border-border-default p-5">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-10 h-10 rounded-lg bg-purple-500/10 flex items-center justify-center">
              <Users className="w-5 h-5 text-purple-500" />
            </div>
            <div>
              <h3 className="text-sm font-medium text-text-secondary">Active Users</h3>
            </div>
          </div>
          <p className="text-3xl font-bold text-text-primary">
            {formatNumber(userCostBreakdown.length)}
          </p>
          <p className="text-xs text-text-tertiary mt-1">Users with costs</p>
        </div>
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        <div className="bg-surface rounded-2xl border border-border-default p-6">
          <h2 className="text-lg font-semibold text-text-primary mb-4">Cost Trend</h2>
          <div className="h-64">
            {dailyCostBreakdown.length > 0 ? (
              <Line data={costChartData} options={chartOptions} />
            ) : (
              <div className="h-full flex items-center justify-center text-text-tertiary">
                No cost data available
              </div>
            )}
          </div>
        </div>

        <div className="bg-surface rounded-2xl border border-border-default p-6">
          <h2 className="text-lg font-semibold text-text-primary mb-4">Token Consumption Trend</h2>
          <div className="h-64">
            {dailyTokenBreakdown.length > 0 ? (
              <Line data={tokenChartData} options={chartOptions} />
            ) : (
              <div className="h-full flex items-center justify-center text-text-tertiary">
                No token data available
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Cost Breakdown Tables */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        {/* User Cost Breakdown */}
        {userCostBreakdown.length > 0 && (
          <div className="bg-surface rounded-2xl border border-border-default p-6">
            <h2 className="text-lg font-semibold text-text-primary mb-4">Cost by User</h2>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-surface-hover border-b border-border-default">
                  <tr>
                    <th className="px-4 py-3 text-left text-sm font-semibold text-text-primary">User ID</th>
                    <th className="px-4 py-3 text-left text-sm font-semibold text-text-primary">Cost</th>
                    <th className="px-4 py-3 text-left text-sm font-semibold text-text-primary">Percentage</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border-default">
                  {userCostBreakdown.slice(0, 10).map((item: any, idx: number) => (
                    <tr key={idx}>
                      <td className="px-4 py-3 text-text-primary font-mono text-sm">{item.user_id || 'Unknown'}</td>
                      <td className="px-4 py-3 text-text-primary">{formatCurrency(item.cost)}</td>
                      <td className="px-4 py-3 text-text-secondary">{item.percentage?.toFixed(2) || '0.00'}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Model Cost Breakdown */}
        {modelCostBreakdown.length > 0 && (
          <div className="bg-surface rounded-2xl border border-border-default p-6">
            <h2 className="text-lg font-semibold text-text-primary mb-4">Cost by Model</h2>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-surface-hover border-b border-border-default">
                  <tr>
                    <th className="px-4 py-3 text-left text-sm font-semibold text-text-primary">Model</th>
                    <th className="px-4 py-3 text-left text-sm font-semibold text-text-primary">Cost</th>
                    <th className="px-4 py-3 text-left text-sm font-semibold text-text-primary">Percentage</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border-default">
                  {modelCostBreakdown.map((item: any, idx: number) => (
                    <tr key={idx}>
                      <td className="px-4 py-3 text-text-primary font-medium">{item.model || 'Unknown'}</td>
                      <td className="px-4 py-3 text-text-primary">{formatCurrency(item.cost)}</td>
                      <td className="px-4 py-3 text-text-secondary">{item.percentage?.toFixed(2) || '0.00'}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>

      {/* Token Breakdown by Feature */}
      {tokenBreakdown.length > 0 && (
        <div className="bg-surface rounded-2xl border border-border-default p-6">
          <h2 className="text-lg font-semibold text-text-primary mb-4">Token Consumption by Feature</h2>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead className="bg-surface-hover border-b border-border-default">
                <tr>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-text-primary">Feature</th>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-text-primary">Total Tokens</th>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-text-primary">Input Tokens</th>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-text-primary">Output Tokens</th>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-text-primary">Calls</th>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-text-primary">Cost</th>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-text-primary">Percentage</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border-default">
                {tokenBreakdown.map((item: any, idx: number) => (
                  <tr key={idx}>
                    <td className="px-4 py-3 text-text-primary font-medium">{item.key || 'Unknown'}</td>
                    <td className="px-4 py-3 text-text-primary">{formatNumber(item.total_tokens)}</td>
                    <td className="px-4 py-3 text-text-secondary">{formatNumber(item.prompt_tokens || item.input_tokens)}</td>
                    <td className="px-4 py-3 text-text-secondary">{formatNumber(item.completion_tokens || item.output_tokens)}</td>
                    <td className="px-4 py-3 text-text-primary">{formatNumber(item.total_calls)}</td>
                    <td className="px-4 py-3 text-text-primary">{formatCurrency(item.cost)}</td>
                    <td className="px-4 py-3 text-text-secondary">{item.percentage?.toFixed(2) || '0.00'}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
