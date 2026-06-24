/**
 * Documents Page
 * 
 * Admin page for viewing document indexing statistics and trends.
 */

'use client';

import { useEffect, useState, useMemo } from 'react';
import { useAdminPortalApi } from '@/hooks/useAdminPortalApi';
import { apiClient } from '@/lib/api-client';
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
import { Line } from 'react-chartjs-2';
import { FileText, CheckCircle2, XCircle, Clock, Loader2 } from 'lucide-react';
import { AdminTableSkeleton } from '@/components/skeleton';

// Register Chart.js components
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

interface Source {
  id: string;
  title: string;
  type: string;
  status: string;
  chunks_count?: number;
  created_at?: string;
  error_message?: string;
}

export default function DocumentsPage() {
  const { ready } = useAdminPortalApi();
  const [sources, setSources] = useState<Source[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Fetch sources from backend
  useEffect(() => {
    const fetchSources = async () => {
      if (!ready) return;
      
      setLoading(true);
      setError(null);
      
      try {
        const sourcesList = await apiClient.listSources();
        setSources(sourcesList || []);
      } catch (err: any) {
        console.error('[Documents] Failed to fetch sources:', err);
        setError(err?.message || 'Failed to load documents');
      } finally {
        setLoading(false);
      }
    };

    fetchSources();
  }, [ready]);

  // Calculate statistics
  const stats = useMemo(() => {
    const total = sources.length;
    const indexed = sources.filter(s => s.status === 'indexed' || s.status === 'completed').length;
    const processing = sources.filter(s => s.status === 'processing').length;
    const failed = sources.filter(s => s.status === 'error' || s.status === 'failed').length;
    
    return {
      total,
      indexed,
      processing,
      failed,
      successRate: total > 0 ? ((indexed / total) * 100).toFixed(1) : '0',
    };
  }, [sources]);

  // Prepare trend chart data (group by date)
  const chartData = useMemo(() => {
    const dateMap = new Map<string, { indexed: number; failed: number; processing: number }>();
    
    sources.forEach((source) => {
      if (!source.created_at) return;
      
      const date = new Date(source.created_at).toISOString().split('T')[0];
      if (!dateMap.has(date)) {
        dateMap.set(date, { indexed: 0, failed: 0, processing: 0 });
      }
      
      const dayData = dateMap.get(date)!;
      if (source.status === 'indexed' || source.status === 'completed') {
        dayData.indexed++;
      } else if (source.status === 'error' || source.status === 'failed') {
        dayData.failed++;
      } else if (source.status === 'processing') {
        dayData.processing++;
      }
    });
    
    // Sort dates
    const sortedDates = Array.from(dateMap.keys()).sort();
    
    return {
      labels: sortedDates.map(date => {
        const d = new Date(date);
        return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
      }),
      datasets: [
        {
          label: 'Indexed',
          data: sortedDates.map(date => dateMap.get(date)!.indexed),
          borderColor: '#10B981',
          backgroundColor: 'rgba(16, 185, 129, 0.1)',
          fill: true,
          tension: 0.4,
        },
        {
          label: 'Failed',
          data: sortedDates.map(date => dateMap.get(date)!.failed),
          borderColor: '#EF4444',
          backgroundColor: 'rgba(239, 68, 68, 0.1)',
          fill: true,
          tension: 0.4,
        },
        {
          label: 'Processing',
          data: sortedDates.map(date => dateMap.get(date)!.processing),
          borderColor: '#F59E0B',
          backgroundColor: 'rgba(245, 158, 11, 0.1)',
          fill: true,
          tension: 0.4,
        },
      ],
    };
  }, [sources]);

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
          usePointStyle: true,
          padding: 15,
        },
      },
      tooltip: {
        backgroundColor: 'rgba(0, 0, 0, 0.8)',
        padding: 12,
        titleFont: { size: 14 },
        bodyFont: { size: 13 },
      },
    },
    scales: {
      x: {
        grid: {
          display: false,
        },
        ticks: {
          color: '#9AA0A6',
          font: { size: 12 },
          maxRotation: 45,
          minRotation: 0,
        },
      },
      y: {
        grid: {
          color: 'rgba(255, 255, 255, 0.05)',
        },
        ticks: {
          color: '#9AA0A6',
          font: { size: 12 },
          stepSize: 1,
        },
        beginAtZero: true,
      },
    },
  };

  const formatNumber = (num: number) => {
    return num.toLocaleString('en-US');
  };

  if (loading) return <AdminTableSkeleton />;

  if (error) {
    return (
      <div className="h-full">
        <div className="mb-6">
          <h1 className="text-2xl font-semibold text-text-primary">Documents</h1>
          <p className="text-sm text-text-secondary mt-1">
            View and manage all documents in the system
          </p>
        </div>
        <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-6">
          <p className="text-red-500">{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full">
      <div className="mb-6">
        <h1 className="text-2xl font-semibold text-text-primary">Documents</h1>
        <p className="text-sm text-text-secondary mt-1">
          View document indexing statistics and trends
        </p>
      </div>

      {/* Statistics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        {/* Total Documents */}
        <div className="bg-surface rounded-xl border border-border-default p-5">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-10 h-10 rounded-lg bg-accent-blue/10 flex items-center justify-center">
              <FileText className="w-5 h-5 text-accent-blue" />
            </div>
            <div>
              <h3 className="text-sm font-medium text-text-secondary">Total Documents</h3>
            </div>
          </div>
          <p className="text-3xl font-bold text-text-primary">{formatNumber(stats.total)}</p>
        </div>

        {/* Successfully Indexed */}
        <div className="bg-surface rounded-xl border border-border-default p-5">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-10 h-10 rounded-lg bg-green-500/10 flex items-center justify-center">
              <CheckCircle2 className="w-5 h-5 text-green-500" />
            </div>
            <div>
              <h3 className="text-sm font-medium text-text-secondary">Successfully Indexed</h3>
            </div>
          </div>
          <p className="text-3xl font-bold text-text-primary">{formatNumber(stats.indexed)}</p>
          <p className="text-xs text-text-tertiary mt-1">{stats.successRate}% success rate</p>
        </div>

        {/* Processing */}
        <div className="bg-surface rounded-xl border border-border-default p-5">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-10 h-10 rounded-lg bg-yellow-500/10 flex items-center justify-center">
              <Clock className="w-5 h-5 text-yellow-500" />
            </div>
            <div>
              <h3 className="text-sm font-medium text-text-secondary">Processing</h3>
            </div>
          </div>
          <p className="text-3xl font-bold text-text-primary">{formatNumber(stats.processing)}</p>
        </div>

        {/* Failed */}
        <div className="bg-surface rounded-xl border border-border-default p-5">
          <div className="flex items-center gap-3 mb-3">
            <div className="w-10 h-10 rounded-lg bg-red-500/10 flex items-center justify-center">
              <XCircle className="w-5 h-5 text-red-500" />
            </div>
            <div>
              <h3 className="text-sm font-medium text-text-secondary">Failed</h3>
            </div>
          </div>
          <p className="text-3xl font-bold text-text-primary">{formatNumber(stats.failed)}</p>
        </div>
      </div>

      {/* Status Breakdown Table */}
      <div className="bg-surface rounded-2xl border border-border-default p-6 mb-6">
        <h2 className="text-lg font-semibold text-text-primary mb-4">Indexing Status Breakdown</h2>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-surface-hover border-b border-border-default">
              <tr>
                <th className="px-4 py-3 text-left text-sm font-semibold text-text-primary">Status</th>
                <th className="px-4 py-3 text-left text-sm font-semibold text-text-primary">Count</th>
                <th className="px-4 py-3 text-left text-sm font-semibold text-text-primary">Percentage</th>
                <th className="px-4 py-3 text-left text-sm font-semibold text-text-primary">Visual</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border-default">
              <tr>
                <td className="px-4 py-3">
                  <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full bg-green-500"></div>
                    <span className="text-text-primary font-medium">Indexed</span>
                  </div>
                </td>
                <td className="px-4 py-3 text-text-primary">{formatNumber(stats.indexed)}</td>
                <td className="px-4 py-3 text-text-secondary">
                  {stats.total > 0 ? ((stats.indexed / stats.total) * 100).toFixed(1) : '0'}%
                </td>
                <td className="px-4 py-3">
                  <div className="w-full bg-surface-hover rounded-full h-2">
                    <div
                      className="bg-green-500 h-2 rounded-full transition-all"
                      style={{ width: `${stats.total > 0 ? (stats.indexed / stats.total) * 100 : 0}%` }}
                    ></div>
                  </div>
                </td>
              </tr>
              <tr>
                <td className="px-4 py-3">
                  <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full bg-yellow-500"></div>
                    <span className="text-text-primary font-medium">Processing</span>
                  </div>
                </td>
                <td className="px-4 py-3 text-text-primary">{formatNumber(stats.processing)}</td>
                <td className="px-4 py-3 text-text-secondary">
                  {stats.total > 0 ? ((stats.processing / stats.total) * 100).toFixed(1) : '0'}%
                </td>
                <td className="px-4 py-3">
                  <div className="w-full bg-surface-hover rounded-full h-2">
                    <div
                      className="bg-yellow-500 h-2 rounded-full transition-all"
                      style={{ width: `${stats.total > 0 ? (stats.processing / stats.total) * 100 : 0}%` }}
                    ></div>
                  </div>
                </td>
              </tr>
              <tr>
                <td className="px-4 py-3">
                  <div className="flex items-center gap-2">
                    <div className="w-3 h-3 rounded-full bg-red-500"></div>
                    <span className="text-text-primary font-medium">Failed</span>
                  </div>
                </td>
                <td className="px-4 py-3 text-text-primary">{formatNumber(stats.failed)}</td>
                <td className="px-4 py-3 text-text-secondary">
                  {stats.total > 0 ? ((stats.failed / stats.total) * 100).toFixed(1) : '0'}%
                </td>
                <td className="px-4 py-3">
                  <div className="w-full bg-surface-hover rounded-full h-2">
                    <div
                      className="bg-red-500 h-2 rounded-full transition-all"
                      style={{ width: `${stats.total > 0 ? (stats.failed / stats.total) * 100 : 0}%` }}
                    ></div>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      {/* Chunks Summary */}
      <div className="bg-surface rounded-2xl border border-border-default p-6 mb-6">
        <h2 className="text-lg font-semibold text-text-primary mb-4">Chunks Summary</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="bg-surface-hover rounded-xl p-4 border border-border-default">
            <h3 className="text-sm font-medium text-text-secondary mb-2">Total Chunks</h3>
            <p className="text-2xl font-bold text-text-primary">
              {formatNumber(
                sources.reduce((sum, s) => sum + (s.chunks_count || 0), 0)
              )}
            </p>
          </div>
          <div className="bg-surface-hover rounded-xl p-4 border border-border-default">
            <h3 className="text-sm font-medium text-text-secondary mb-2">Avg Chunks per Document</h3>
            <p className="text-2xl font-bold text-text-primary">
              {stats.indexed > 0
                ? formatNumber(
                    Math.round(sources.reduce((sum, s) => sum + (s.chunks_count || 0), 0) / stats.indexed)
                  )
                : '0'}
            </p>
          </div>
          <div className="bg-surface-hover rounded-xl p-4 border border-border-default">
            <h3 className="text-sm font-medium text-text-secondary mb-2">Documents with Chunks</h3>
            <p className="text-2xl font-bold text-text-primary">
              {formatNumber(sources.filter(s => s.chunks_count && s.chunks_count > 0).length)}
            </p>
          </div>
        </div>
      </div>

      {/* Documents Table with Chunks */}
      <div className="bg-surface rounded-2xl border border-border-default p-6 mb-6">
        <h2 className="text-lg font-semibold text-text-primary mb-4">All Documents</h2>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-surface-hover border-b border-border-default">
              <tr>
                <th className="px-4 py-3 text-left text-sm font-semibold text-text-primary">Title</th>
                <th className="px-4 py-3 text-left text-sm font-semibold text-text-primary">Type</th>
                <th className="px-4 py-3 text-left text-sm font-semibold text-text-primary">Status</th>
                <th className="px-4 py-3 text-left text-sm font-semibold text-text-primary">Chunks</th>
                <th className="px-4 py-3 text-left text-sm font-semibold text-text-primary">Created</th>
                <th className="px-4 py-3 text-left text-sm font-semibold text-text-primary">Error</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border-default">
              {sources.map((source) => (
                <tr key={source.id}>
                  <td className="px-4 py-3 text-text-primary font-medium">{source.title}</td>
                  <td className="px-4 py-3 text-text-secondary">{source.type}</td>
                  <td className="px-4 py-3">
                    <span className={`px-2 py-1 rounded text-xs font-medium ${
                      source.status === 'indexed' || source.status === 'completed'
                        ? 'bg-green-500/20 text-green-500'
                        : source.status === 'processing'
                        ? 'bg-yellow-500/20 text-yellow-500'
                        : 'bg-red-500/20 text-red-500'
                    }`}>
                      {source.status}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-text-primary">
                    {source.chunks_count !== undefined && source.chunks_count !== null
                      ? formatNumber(source.chunks_count)
                      : source.status === 'indexed' || source.status === 'completed'
                      ? '—'
                      : 'Processing...'}
                  </td>
                  <td className="px-4 py-3 text-text-secondary text-sm">
                    {source.created_at ? new Date(source.created_at).toLocaleDateString() : 'N/A'}
                  </td>
                  <td className="px-4 py-3 text-text-secondary text-sm">
                    {source.error_message ? (
                      <span className="text-red-500 text-xs" title={source.error_message}>
                        {source.error_message.length > 50 
                          ? `${source.error_message.substring(0, 50)}...` 
                          : source.error_message}
                      </span>
                    ) : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Trend Chart */}
      <div className="bg-surface rounded-2xl border border-border-default p-6">
        <h2 className="text-lg font-semibold text-text-primary mb-4">Document Indexing Trend</h2>
        <div className="h-80">
          {chartData.labels.length > 0 ? (
            <Line data={chartData} options={chartOptions} />
          ) : (
            <div className="h-full flex items-center justify-center text-text-tertiary">
              No data available for trend chart
            </div>
          )}
        </div>
      </div>
    </div>
  );
}