/**
 * RAG Metrics Page
 * 
 * Admin page for viewing RAG (Retrieval-Augmented Generation) metrics.
 */

'use client';

import { useEffect, useState } from 'react';
import { useAdminPortalApi } from '@/hooks/useAdminPortalApi';
import { apiClient } from '@/lib/api-client';
import { Loader2, TrendingUp, TrendingDown, AlertTriangle, CheckCircle2 } from 'lucide-react';
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
import { AdminTableSkeleton } from '@/components/skeleton';

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

export default function RAGMetricsPage() {
  const { ready } = useAdminPortalApi();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [ragData, setRagData] = useState<any>(null);

  useEffect(() => {
    const fetchData = async () => {
      if (!ready) return;
      
      setLoading(true);
      setError(null);
      
      try {
        const data = await apiClient.getRagQuality(30);
        console.log('[RAG Metrics] Raw API response:', JSON.stringify(data, null, 2));
        setRagData(data);
      } catch (err: any) {
        console.error('[RAG Metrics] Failed to fetch data:', err);
        console.error('[RAG Metrics] Error details:', err?.response?.data || err?.message);
        setError(err?.message || 'Failed to load RAG metrics');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [ready]);

  const formatNumber = (num: number | null | undefined) => {
    // Always show the number, even if it's 0
    const value = num === null || num === undefined || isNaN(Number(num)) ? 0 : Number(num);
    return new Intl.NumberFormat('en-US').format(value);
  };

  const formatPercentage = (num: number | null | undefined) => {
    // Always show the percentage, even if it's 0
    const value = num === null || num === undefined || isNaN(Number(num)) ? 0 : Number(num);
    // If num is already a percentage (0-1), multiply by 100, otherwise use as-is
    const percentage = value > 1 ? value : value * 100;
    return `${percentage.toFixed(2)}%`;
  };

  if (loading) return <AdminTableSkeleton />;

  if (error) {
    return (
      <div className="h-full">
        <div className="mb-6">
          <h1 className="text-2xl font-semibold text-text-primary">RAG Metrics</h1>
          <p className="text-sm text-text-secondary mt-1">
            View and analyze RAG performance metrics
          </p>
        </div>
        <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-6">
          <p className="text-red-500">{error}</p>
        </div>
      </div>
    );
  }

  // Extract data - ensure we always get numbers
  const summary = ragData?.summary || {};
  const dailyBreakdown = ragData?.daily_breakdown || [];
  
  // Extract values - convert to numbers, defaulting to 0 if missing/invalid
  const totalFeedback = Number(summary.total_feedback) || 0;
  const thumbsUp = Number(summary.thumbs_up) || 0;
  const thumbsDown = Number(summary.thumbs_down) || 0;
  const hallucinationRate = Number(summary.hallucination_rate) || 0;
  const positiveRate = Number(summary.positive_rate) || 0;

  // Prepare chart data
  const chartData = {
    labels: dailyBreakdown.map((item: any) => {
      const date = new Date(item.date);
      return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    }),
    datasets: [
      {
        label: 'Helpful',
        data: dailyBreakdown.map((item: any) => item.thumbs_up || 0),
        borderColor: '#10B981',
        backgroundColor: 'rgba(16, 185, 129, 0.1)',
        fill: true,
        tension: 0.4,
      },
      {
        label: 'Negative signals',
        data: dailyBreakdown.map((item: any) => item.thumbs_down || 0),
        borderColor: '#EF4444',
        backgroundColor: 'rgba(239, 68, 68, 0.1)',
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
        display: true,
        position: 'top' as const,
        labels: {
          color: '#9AA0A6',
          font: { size: 12 },
        },
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
        ticks: { color: '#9AA0A6', font: { size: 12 }, stepSize: 1 },
        beginAtZero: true,
      },
    },
  };

  return (
    <div className="h-full">
      <div className="mb-6">
        <h1 className="text-2xl font-semibold text-text-primary">RAG Metrics</h1>
        <p className="text-sm text-text-secondary mt-1">
          View and analyze RAG performance metrics
        </p>
      </div>

      {/* Statistics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4 mb-6">
        <div className="bg-surface rounded-xl border border-border-default p-5">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-10 h-10 rounded-lg bg-accent-blue/10 flex items-center justify-center">
              <TrendingUp className="w-5 h-5 text-accent-blue" />
            </div>
            <div>
              <h3 className="text-sm font-medium text-text-secondary">Total Feedback</h3>
            </div>
          </div>
          <p className="text-3xl font-bold text-text-primary">{formatNumber(totalFeedback)}</p>
          <p className="text-xs text-text-tertiary mt-1">
            {totalFeedback === 0 ? 'No feedback yet' : `${totalFeedback} total responses`}
          </p>
        </div>

        <div className="bg-surface rounded-xl border border-border-default p-5">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-10 h-10 rounded-lg bg-green-500/10 flex items-center justify-center">
              <CheckCircle2 className="w-5 h-5 text-green-500" />
            </div>
            <div>
              <h3 className="text-sm font-medium text-text-secondary">Helpful</h3>
            </div>
          </div>
          <p className="text-3xl font-bold text-text-primary">{formatNumber(thumbsUp)}</p>
          <p className="text-xs text-text-tertiary mt-1">
            {totalFeedback > 0 ? `${formatPercentage(positiveRate)} positive` : 'No feedback yet'}
          </p>
        </div>

        <div className="bg-surface rounded-xl border border-border-default p-5">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-10 h-10 rounded-lg bg-red-500/10 flex items-center justify-center">
              <AlertTriangle className="w-5 h-5 text-red-500" />
            </div>
            <div>
              <h3 className="text-sm font-medium text-text-secondary">Negative signals</h3>
            </div>
          </div>
          <p className="text-3xl font-bold text-text-primary">{formatNumber(thumbsDown)}</p>
          <p className="text-xs text-text-tertiary mt-1">
            {totalFeedback > 0 ? `${formatPercentage(hallucinationRate)} hallucination rate` : 'No feedback yet'}
          </p>
        </div>

        <div className="bg-surface rounded-xl border border-border-default p-5">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-10 h-10 rounded-lg bg-yellow-500/10 flex items-center justify-center">
              <TrendingDown className="w-5 h-5 text-yellow-500" />
            </div>
            <div>
              <h3 className="text-sm font-medium text-text-secondary">Hallucination Rate</h3>
            </div>
          </div>
          <p className="text-3xl font-bold text-text-primary">{formatPercentage(hallucinationRate)}</p>
          <p className="text-xs text-text-tertiary mt-1">
            {totalFeedback > 0 ? 'Based on not_helpful + inaccurate' : 'No feedback yet'}
          </p>
        </div>

        <div className="bg-surface rounded-xl border border-border-default p-5">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-10 h-10 rounded-lg bg-green-500/10 flex items-center justify-center">
              <TrendingUp className="w-5 h-5 text-green-500" />
            </div>
            <div>
              <h3 className="text-sm font-medium text-text-secondary">Positive Rate</h3>
            </div>
          </div>
          <p className="text-3xl font-bold text-text-primary">{formatPercentage(positiveRate)}</p>
          <p className="text-xs text-text-tertiary mt-1">
            {totalFeedback > 0 ? 'Based on helpful + expert_validated' : 'No feedback yet'}
          </p>
        </div>
      </div>

      {/* Daily Breakdown Chart */}
      {dailyBreakdown.length > 0 && (
        <div className="bg-surface rounded-2xl border border-border-default p-6 mb-6">
          <h2 className="text-lg font-semibold text-text-primary mb-4">Daily Feedback Trend</h2>
          <div className="h-80">
            <Line data={chartData} options={chartOptions} />
          </div>
        </div>
      )}

      {/* Detailed Breakdown Table */}
      <div className="bg-surface rounded-2xl border border-border-default p-6">
        <h2 className="text-lg font-semibold text-text-primary mb-4">Daily Breakdown</h2>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-surface-hover border-b border-border-default">
              <tr>
                <th className="px-4 py-3 text-left text-sm font-semibold text-text-primary">Date</th>
                <th className="px-4 py-3 text-left text-sm font-semibold text-text-primary">Helpful</th>
                <th className="px-4 py-3 text-left text-sm font-semibold text-text-primary">Negative</th>
                <th className="px-4 py-3 text-left text-sm font-semibold text-text-primary">Total</th>
                <th className="px-4 py-3 text-left text-sm font-semibold text-text-primary">Hallucination Rate</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border-default">
              {dailyBreakdown.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-4 py-8 text-center text-text-secondary">
                    No feedback data available
                  </td>
                </tr>
              ) : (
                dailyBreakdown.map((item: any, idx: number) => (
                  <tr key={idx}>
                    <td className="px-4 py-3 text-text-primary">
                      {new Date(item.date).toLocaleDateString('en-US', { 
                        year: 'numeric', 
                        month: 'short', 
                        day: 'numeric' 
                      })}
                    </td>
                    <td className="px-4 py-3 text-text-primary">{formatNumber(item.thumbs_up || 0)}</td>
                    <td className="px-4 py-3 text-text-primary">{formatNumber(item.thumbs_down || 0)}</td>
                    <td className="px-4 py-3 text-text-primary">{formatNumber(item.total || 0)}</td>
                    <td className="px-4 py-3 text-text-primary">{formatPercentage(item.hallucination_rate || 0)}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}