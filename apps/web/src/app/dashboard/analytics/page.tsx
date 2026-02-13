/**
 * Analytics Dashboard Page
 * 
 * Admin analytics dashboard with KPI cards, charts, and auto-refresh.
 */

'use client';

import { useEffect, useState, useCallback } from 'react';
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
import { 
  TrendingUp, 
  DollarSign, 
  Clock, 
  Database, 
  CheckCircle, 
  AlertCircle,
  RefreshCw 
} from 'lucide-react';
import { MetricCard } from '@/components/analytics/MetricCard';
import { useAuth } from '@clerk/nextjs';
import axios from 'axios';

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

interface DashboardData {
  tokens?: {
    total?: number;
    trend?: { date: string; value: number }[];
  };
  cost?: {
    total?: number;
    trend?: { date: string; value: number }[];
  };
  latency?: {
    average?: number;
    trend?: { date: string; value: number }[];
  };
  cache?: {
    hitRate?: number;
    trend?: { date: string; value: number }[];
  };
  ragQuality?: {
    score?: number;
    trend?: { date: string; value: number }[];
  };
  alerts?: {
    active?: number;
  };
}

const REFRESH_INTERVAL = 10000; // 10 seconds

export default function AnalyticsDashboardPage() {
  const { getToken } = useAuth();
  const [data, setData] = useState<DashboardData>({});
  const [loading, setLoading] = useState(true);
  const [lastRefresh, setLastRefresh] = useState<Date>(new Date());
  const [errors, setErrors] = useState<Record<string, boolean>>({});

  const fetchDashboardData = useCallback(async () => {
    const newErrors: Record<string, boolean> = {};
    
    try {
      // Get base URL and prepare headers
      const baseURL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
      
      // Get tenant ID from cookie
      const getTenantId = () => {
        if (typeof document === 'undefined') return 'default';
        const match = document.cookie
          .split('; ')
          .find(row => row.startsWith('tenantId='));
        return match ? match.split('=')[1] : 'default';
      };

      // Get auth token from Clerk
      const token = await getToken();
      const tenantId = getTenantId();
      
      const headers: Record<string, string> = {
        'X-Tenant-ID': tenantId,
      };
      
      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      // Create axios instance for these requests
      const client = axios.create({
        baseURL,
        headers,
        timeout: 10000,
      });

      // Fetch all endpoints in parallel
      const [
        metricsRes,
        dashboardMetricsRes,
        alertsRes,
        ragQualityRes,
        tokensRes,
        costRes,
        cacheRes,
        latencyRes,
      ] = await Promise.allSettled([
        client.get('/metrics'),
        client.get('/api/v1/metrics/dashboard'),
        client.get('/api/v1/alerts/status'),
        client.get('/api/v1/dashboards/rag-quality'),
        client.get('/api/v1/dashboards/tokens'),
        client.get('/api/v1/dashboards/cost'),
        client.get('/api/v1/dashboards/cache'),
        client.get('/api/v1/dashboards/latency'),
      ]);

      const newData: DashboardData = {};

      // Process metrics endpoint
      if (metricsRes.status === 'fulfilled') {
        const metrics = metricsRes.value.data;
        // Extract data based on actual API response structure
        if (metrics) {
          newData.tokens = { total: metrics.total_tokens };
          newData.cost = { total: metrics.total_cost };
          newData.latency = { average: metrics.avg_latency };
        }
      } else {
        newErrors.metrics = true;
      }

      // Process dashboard metrics
      if (dashboardMetricsRes.status === 'fulfilled') {
        const dashboard = dashboardMetricsRes.value.data;
        if (dashboard) {
          // Merge dashboard data
          if (dashboard.tokens) newData.tokens = { ...newData.tokens, ...dashboard.tokens };
          if (dashboard.cost) newData.cost = { ...newData.cost, ...dashboard.cost };
          if (dashboard.latency) newData.latency = { ...newData.latency, ...dashboard.latency };
        }
      } else {
        newErrors.dashboard = true;
      }

      // Process alerts
      if (alertsRes.status === 'fulfilled') {
        const alerts = alertsRes.value.data;
        newData.alerts = { active: alerts?.active_count || alerts?.count || 0 };
      } else {
        newErrors.alerts = true;
      }

      // Process RAG quality
      if (ragQualityRes.status === 'fulfilled') {
        const rag = ragQualityRes.value.data;
        newData.ragQuality = {
          score: rag?.score || rag?.quality_score || rag?.average_score,
          trend: rag?.trend || rag?.history,
        };
      } else {
        newErrors.ragQuality = true;
      }

      // Process tokens dashboard
      if (tokensRes.status === 'fulfilled') {
        const tokens = tokensRes.value.data;
        newData.tokens = {
          ...newData.tokens,
          total: tokens?.total || tokens?.total_tokens,
          trend: tokens?.trend || tokens?.history,
        };
      } else {
        newErrors.tokens = true;
      }

      // Process cost dashboard
      if (costRes.status === 'fulfilled') {
        const cost = costRes.value.data;
        newData.cost = {
          ...newData.cost,
          total: cost?.total || cost?.total_cost,
          trend: cost?.trend || cost?.history,
        };
      } else {
        newErrors.cost = true;
      }

      // Process cache dashboard
      if (cacheRes.status === 'fulfilled') {
        const cache = cacheRes.value.data;
        newData.cache = {
          hitRate: cache?.hit_rate || cache?.hitRate || cache?.cache_hit_rate,
          trend: cache?.trend || cache?.history,
        };
      } else {
        newErrors.cache = true;
      }

      // Process latency dashboard
      if (latencyRes.status === 'fulfilled') {
        const latency = latencyRes.value.data;
        newData.latency = {
          ...newData.latency,
          average: latency?.average || latency?.avg_latency,
          trend: latency?.trend || latency?.history,
        };
      } else {
        newErrors.latency = true;
      }

      setData(newData);
      setErrors(newErrors);
      setLastRefresh(new Date());
    } catch (error) {
      console.error('Error fetching dashboard data:', error);
      setErrors({ general: true });
    } finally {
      setLoading(false);
    }
  }, []);

  // Initial fetch and setup auto-refresh
  useEffect(() => {
    fetchDashboardData();
    
    const interval = setInterval(() => {
      fetchDashboardData();
    }, REFRESH_INTERVAL);

    return () => clearInterval(interval);
  }, [fetchDashboardData]);

  // Format number with commas
  const formatNumber = (num: number | null | undefined): string => {
    if (num === null || num === undefined) return '—';
    return new Intl.NumberFormat('en-US').format(num);
  };

  // Format currency
  const formatCurrency = (num: number | null | undefined): string => {
    if (num === null || num === undefined) return '—';
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
    }).format(num);
  };

  // Format percentage
  const formatPercentage = (num: number | null | undefined): string => {
    if (num === null || num === undefined) return '—';
    return `${num.toFixed(1)}%`;
  };

  // Format latency
  const formatLatency = (num: number | null | undefined): string => {
    if (num === null || num === undefined) return '—';
    return `${num.toFixed(0)}ms`;
  };

  // Prepare chart data
  const prepareChartData = (
    trend: { date: string; value: number }[] | undefined,
    label: string,
    color: string
  ) => {
    if (!trend || trend.length === 0) {
      return {
        labels: [],
        datasets: [],
      };
    }

    return {
      labels: trend.map((item) => {
        const date = new Date(item.date);
        return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
      }),
      datasets: [
        {
          label,
          data: trend.map((item) => item.value),
          borderColor: color,
          backgroundColor: `${color}20`,
          fill: true,
          tension: 0.4,
          pointRadius: 3,
          pointHoverRadius: 5,
        },
      ],
    };
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
        },
      },
      y: {
        grid: {
          color: 'rgba(255, 255, 255, 0.05)',
        },
        ticks: {
          color: '#9AA0A6',
          font: { size: 12 },
        },
      },
    },
  };

  return (
    <div className="h-full flex flex-col overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-border-default">
        <div>
          <h1 className="text-2xl font-semibold text-text-primary">Analytics Dashboard</h1>
          <p className="text-sm text-text-secondary mt-1">
            Last updated: {lastRefresh.toLocaleTimeString()}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <RefreshCw 
            className={`w-4 h-4 text-text-secondary ${loading ? 'animate-spin' : ''}`} 
          />
          <span className="text-sm text-text-secondary">Auto-refreshing every 10s</span>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6">
        {/* KPI Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4 mb-8">
          <MetricCard
            title="Total Tokens"
            value={formatNumber(data.tokens?.total)}
            icon={<TrendingUp className="w-5 h-5" />}
            isLoading={loading && !data.tokens}
            error={errors.tokens || errors.metrics}
          />
          <MetricCard
            title="Total Cost"
            value={formatCurrency(data.cost?.total)}
            icon={<DollarSign className="w-5 h-5" />}
            isLoading={loading && !data.cost}
            error={errors.cost || errors.metrics}
          />
          <MetricCard
            title="Avg Latency"
            value={formatLatency(data.latency?.average)}
            icon={<Clock className="w-5 h-5" />}
            isLoading={loading && !data.latency}
            error={errors.latency || errors.metrics}
          />
          <MetricCard
            title="Cache Hit %"
            value={formatPercentage(data.cache?.hitRate)}
            icon={<Database className="w-5 h-5" />}
            isLoading={loading && !data.cache}
            error={errors.cache}
          />
          <MetricCard
            title="RAG Quality Score"
            value={data.ragQuality?.score ? `${data.ragQuality.score.toFixed(1)}/10` : '—'}
            icon={<CheckCircle className="w-5 h-5" />}
            isLoading={loading && !data.ragQuality}
            error={errors.ragQuality}
          />
          <MetricCard
            title="Active Alerts"
            value={formatNumber(data.alerts?.active)}
            icon={<AlertCircle className="w-5 h-5" />}
            isLoading={loading && !data.alerts}
            error={errors.alerts}
          />
        </div>

        {/* Charts Section */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Token Consumption Trend */}
          <div className="bg-surface rounded-2xl border border-border-default p-6">
            <h3 className="text-lg font-semibold text-text-primary mb-4">Token Consumption Trend</h3>
            <div className="h-64">
              {data.tokens?.trend && data.tokens.trend.length > 0 ? (
                <Line
                  data={prepareChartData(data.tokens.trend, 'Tokens', '#1A73E8')}
                  options={chartOptions}
                />
              ) : (
                <div className="h-full flex items-center justify-center text-text-tertiary">
                  {errors.tokens ? 'Data unavailable' : 'No data available'}
                </div>
              )}
            </div>
          </div>

          {/* Cost Trend */}
          <div className="bg-surface rounded-2xl border border-border-default p-6">
            <h3 className="text-lg font-semibold text-text-primary mb-4">Cost Trend</h3>
            <div className="h-64">
              {data.cost?.trend && data.cost.trend.length > 0 ? (
                <Line
                  data={prepareChartData(data.cost.trend, 'Cost ($)', '#34A853')}
                  options={chartOptions}
                />
              ) : (
                <div className="h-full flex items-center justify-center text-text-tertiary">
                  {errors.cost ? 'Data unavailable' : 'No data available'}
                </div>
              )}
            </div>
          </div>

          {/* Latency Trend */}
          <div className="bg-surface rounded-2xl border border-border-default p-6">
            <h3 className="text-lg font-semibold text-text-primary mb-4">Latency Trend</h3>
            <div className="h-64">
              {data.latency?.trend && data.latency.trend.length > 0 ? (
                <Line
                  data={prepareChartData(data.latency.trend, 'Latency (ms)', '#EA4335')}
                  options={chartOptions}
                />
              ) : (
                <div className="h-full flex items-center justify-center text-text-tertiary">
                  {errors.latency ? 'Data unavailable' : 'No data available'}
                </div>
              )}
            </div>
          </div>

          {/* Cache Efficiency Trend */}
          <div className="bg-surface rounded-2xl border border-border-default p-6">
            <h3 className="text-lg font-semibold text-text-primary mb-4">Cache Efficiency Trend</h3>
            <div className="h-64">
              {data.cache?.trend && data.cache.trend.length > 0 ? (
                <Bar
                  data={prepareChartData(data.cache.trend, 'Cache Hit Rate (%)', '#FBBC04')}
                  options={chartOptions}
                />
              ) : (
                <div className="h-full flex items-center justify-center text-text-tertiary">
                  {errors.cache ? 'Data unavailable' : 'No data available'}
                </div>
              )}
            </div>
          </div>

          {/* RAG Quality Trend */}
          <div className="bg-surface rounded-2xl border border-border-default p-6 lg:col-span-2">
            <h3 className="text-lg font-semibold text-text-primary mb-4">RAG Quality Trend</h3>
            <div className="h-64">
              {data.ragQuality?.trend && data.ragQuality.trend.length > 0 ? (
                <Line
                  data={prepareChartData(data.ragQuality.trend, 'Quality Score', '#9C27B0')}
                  options={chartOptions}
                />
              ) : (
                <div className="h-full flex items-center justify-center text-text-tertiary">
                  {errors.ragQuality ? 'Data unavailable' : 'No data available'}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
