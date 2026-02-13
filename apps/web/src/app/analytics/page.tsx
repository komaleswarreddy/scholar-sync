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
  X
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
    inputTokens?: number;
    outputTokens?: number;
    totalCalls?: number;
    avgTokensPerCall?: number;
    breakdown?: Array<{
      key: string;
      total_tokens: number;
      total_calls: number;
      avg_tokens: number;
      cost: number;
      percentage: number;
    }>;
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

export default function AnalyticsDashboardPage() {
  const { getToken } = useAuth();
  const [data, setData] = useState<DashboardData>({});
  const [loading, setLoading] = useState(true);
  const [lastRefresh, setLastRefresh] = useState<Date | null>(null);
  const [errors, setErrors] = useState<Record<string, boolean>>({});
  const [mounted, setMounted] = useState(false);
  const [selectedCard, setSelectedCard] = useState<string | null>(null);
  const [tokenDetails, setTokenDetails] = useState<any>(null);
  const [loadingTokenDetails, setLoadingTokenDetails] = useState(false);
  const [costDetails, setCostDetails] = useState<any>(null);
  const [loadingCostDetails, setLoadingCostDetails] = useState(false);
  const [latencyDetails, setLatencyDetails] = useState<any>(null);
  const [loadingLatencyDetails, setLoadingLatencyDetails] = useState(false);
  const [cacheDetails, setCacheDetails] = useState<any>(null);
  const [loadingCacheDetails, setLoadingCacheDetails] = useState(false);
  const [ragQualityDetails, setRagQualityDetails] = useState<any>(null);
  const [loadingRagQualityDetails, setLoadingRagQualityDetails] = useState(false);

  // Initialize on client only to prevent hydration mismatch
  useEffect(() => {
    setMounted(true);
    setLastRefresh(new Date());
  }, []);

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
        dashboardMetricsRes,
        alertsRes,
        ragQualityRes,
        tokensRes,
        costRes,
        cacheRes,
        latencyRes,
      ] = await Promise.allSettled([
        client.get('/api/v1/metrics/dashboard'),
        client.get('/api/v1/alerts/status'),
        client.get('/api/v1/dashboards/rag-quality'),
        client.get('/api/v1/dashboards/tokens'),
        client.get('/api/v1/dashboards/cost'),
        client.get('/api/v1/dashboards/cache'),
        client.get('/api/v1/dashboards/latency'),
      ]);

      const newData: DashboardData = {};

      // Process dashboard metrics (main source of data)
      if (dashboardMetricsRes.status === 'fulfilled') {
        const dashboard = dashboardMetricsRes.value.data;
        if (dashboard) {
          const metricsData = dashboard.metrics || dashboard;
          const usageData = dashboard.usage || {};
          
          // Extract from metrics summary - try multiple possible field names
          const totalTokens = metricsData.total_tokens || metricsData.tokens?.total || usageData.total_tokens;
          if (totalTokens !== undefined) {
            newData.tokens = { ...newData.tokens, total: totalTokens };
          }
          
          const totalCost = usageData.total_cost || metricsData.total_cost || metricsData.cost?.total;
          if (totalCost !== undefined) {
            newData.cost = { ...newData.cost, total: totalCost };
          }
          
          const avgLatency = metricsData.avg_latency || metricsData.latency?.average || usageData.avg_latency;
          if (avgLatency !== undefined) {
            newData.latency = { ...newData.latency, average: avgLatency };
          }
          
          // Extract cache hit rate
          const hitRate = metricsData.cache?.hit_rate || metricsData.cache_hit_rate || usageData.cache_hit_rate;
          if (hitRate !== undefined) {
            newData.cache = { ...newData.cache, hitRate: typeof hitRate === 'number' ? hitRate * 100 : hitRate };
          }
          
          // Extract alerts count
          if (dashboard.alerts && Array.isArray(dashboard.alerts)) {
            newData.alerts = { active: dashboard.alerts.length };
          }
        }
      } else {
        newErrors.dashboard = true;
      }

      // Process alerts
      if (alertsRes.status === 'fulfilled') {
        const alerts = alertsRes.value.data;
        // Handle status object structure
        const status = alerts?.status || alerts;
        const activeCount = status?.active_alerts || alerts?.active_count || alerts?.count || (Array.isArray(alerts?.alerts) ? alerts.alerts.length : 0);
        if (activeCount > 0 || newData.alerts?.active === undefined) {
          newData.alerts = { active: activeCount };
        }
      } else {
        if (!newData.alerts) {
          newErrors.alerts = true;
        }
      }

      // Process RAG quality
      if (ragQualityRes.status === 'fulfilled') {
        const rag = ragQualityRes.value.data;
        const summary = rag?.summary || rag;
        newData.ragQuality = {
          score: summary?.positive_rate ? (summary.positive_rate * 10) : (rag?.score || rag?.quality_score || rag?.average_score),
          trend: rag?.daily_breakdown?.map((item: any) => ({
            date: item.date,
            value: item.positive_rate ? (item.positive_rate * 10) : (item.hallucination_rate ? (1 - item.hallucination_rate) * 10 : 0)
          })) || rag?.trend || rag?.history,
        };
      } else {
        newErrors.ragQuality = true;
      }

      // Process tokens dashboard
      if (tokensRes.status === 'fulfilled') {
        const tokens = tokensRes.value.data;
        const summary = tokens?.summary || tokens;
        newData.tokens = {
          ...newData.tokens,
          total: summary?.total_tokens || tokens?.total || tokens?.total_tokens || newData.tokens?.total,
          trend: tokens?.daily_breakdown?.map((item: any) => ({
            date: item.date,
            value: item.tokens || 0
          })) || tokens?.trend || tokens?.history,
        };
      } else {
        if (!newData.tokens?.total) {
          newErrors.tokens = true;
        }
      }

      // Process cost dashboard
      if (costRes.status === 'fulfilled') {
        const cost = costRes.value.data;
        const summary = cost?.summary || cost;
        newData.cost = {
          ...newData.cost,
          total: summary?.total_cost || cost?.total || cost?.total_cost || newData.cost?.total,
          trend: cost?.daily_breakdown?.map((item: any) => ({
            date: item.date,
            value: item.cost || 0
          })) || cost?.trend || cost?.history,
        };
      } else {
        if (!newData.cost?.total) {
          newErrors.cost = true;
        }
      }

      // Process cache dashboard
      if (cacheRes.status === 'fulfilled') {
        const cache = cacheRes.value.data;
        const summary = cache?.summary || cache;
        newData.cache = {
          hitRate: summary?.hit_rate || cache?.hit_rate || cache?.hitRate || cache?.cache_hit_rate || newData.cache?.hitRate,
          trend: cache?.daily_breakdown?.map((item: any) => ({
            date: item.date,
            value: item.hit_rate ? (item.hit_rate * 100) : 0
          })) || cache?.trend || cache?.history,
        };
      } else {
        if (newData.cache?.hitRate === undefined) {
          newErrors.cache = true;
        }
      }

      // Process latency dashboard
      if (latencyRes.status === 'fulfilled') {
        const latency = latencyRes.value.data;
        const summary = latency?.summary || latency;
        newData.latency = {
          ...newData.latency,
          average: summary?.avg_latency_ms || latency?.average || latency?.avg_latency || newData.latency?.average,
          trend: latency?.daily_breakdown?.map((item: any) => ({
            date: item.date,
            value: item.avg_latency_ms || 0
          })) || latency?.trend || latency?.history,
        };
      } else {
        if (newData.latency?.average === undefined) {
          newErrors.latency = true;
        }
      }

      setData(newData);
      setErrors(newErrors);
      setLastRefresh(new Date());
    } catch (error) {
      setErrors({ general: true });
    } finally {
      setLoading(false);
    }
  }, [getToken]);

  // Initial fetch and setup auto-refresh
  useEffect(() => {
    fetchDashboardData();
    
    const interval = setInterval(() => {
      fetchDashboardData();
    }, REFRESH_INTERVAL);

    return () => clearInterval(interval);
  }, [fetchDashboardData]);

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
          <p className="text-sm text-text-secondary mt-1" suppressHydrationWarning>
            Last updated: {mounted && lastRefresh ? lastRefresh.toLocaleTimeString() : '—'}
          </p>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6">
        {/* KPI Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4 mb-8">
          <MetricCard
            title="Token Consumption"
            value={formatNumber(data.tokens?.total)}
            icon={<TrendingUp className="w-5 h-5" />}
            isLoading={loading && !data.tokens}
            error={errors.tokens || errors.metrics}
            onClick={() => setSelectedCard('tokens')}
          />
          <MetricCard
            title="Total Cost"
            value={formatCurrency(data.cost?.total)}
            icon={<DollarSign className="w-5 h-5" />}
            isLoading={loading && !data.cost}
            error={errors.cost || errors.metrics}
            onClick={() => setSelectedCard('cost')}
          />
          <MetricCard
            title="Avg Latency"
            value={formatLatency(data.latency?.average)}
            icon={<Clock className="w-5 h-5" />}
            isLoading={loading && !data.latency}
            error={errors.latency || errors.metrics}
            onClick={() => setSelectedCard('latency')}
          />
          <MetricCard
            title="Cache Hit %"
            value={formatPercentage(data.cache?.hitRate)}
            icon={<Database className="w-5 h-5" />}
            isLoading={loading && !data.cache}
            error={errors.cache}
            onClick={() => setSelectedCard('cache')}
          />
          <MetricCard
            title="RAG Quality Score"
            value={data.ragQuality?.score ? `${data.ragQuality.score.toFixed(1)}/10` : '—'}
            icon={<CheckCircle className="w-5 h-5" />}
            isLoading={loading && !data.ragQuality}
            error={errors.ragQuality}
            onClick={() => setSelectedCard('rag-quality')}
          />
          <MetricCard
            title="Active Alerts"
            value={formatNumber(data.alerts?.active)}
            icon={<AlertCircle className="w-5 h-5" />}
            isLoading={loading && !data.alerts}
            error={errors.alerts}
            onClick={() => setSelectedCard('alerts')}
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

      {/* Metric Detail Modal */}
      {selectedCard && (
        <MetricDetailModal
          cardType={selectedCard}
          data={data}
          tokenDetails={tokenDetails}
          loadingTokenDetails={loadingTokenDetails}
          onLoadTokenDetails={async () => {
            setLoadingTokenDetails(true);
            try {
              const baseURL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
              const getTenantId = () => {
                if (typeof document === 'undefined') return 'default';
                const match = document.cookie
                  .split('; ')
                  .find(row => row.startsWith('tenantId='));
                return match ? match.split('=')[1] : 'default';
              };
              const token = await getToken();
              const tenantId = getTenantId();
              const headers: Record<string, string> = {
                'X-Tenant-ID': tenantId,
              };
              if (token) {
                headers['Authorization'] = `Bearer ${token}`;
              }
              const client = axios.create({
                baseURL,
                headers,
                timeout: 10000,
              });
              const response = await client.get('/api/v1/dashboards/tokens', {
                params: { days: 30, group_by: 'feature' }
              });
              setTokenDetails(response.data);
            } catch (error) {
              // Silently fail
            } finally {
              setLoadingTokenDetails(false);
            }
          }}
          costDetails={costDetails}
          loadingCostDetails={loadingCostDetails}
          latencyDetails={latencyDetails}
          loadingLatencyDetails={loadingLatencyDetails}
          cacheDetails={cacheDetails}
          loadingCacheDetails={loadingCacheDetails}
          ragQualityDetails={ragQualityDetails}
          loadingRagQualityDetails={loadingRagQualityDetails}
          onLoadCostDetails={async () => {
            setLoadingCostDetails(true);
            try {
              const baseURL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
              const getTenantId = () => {
                if (typeof document === 'undefined') return 'default';
                const match = document.cookie
                  .split('; ')
                  .find(row => row.startsWith('tenantId='));
                return match ? match.split('=')[1] : 'default';
              };
              const token = await getToken();
              const tenantId = getTenantId();
              const headers: Record<string, string> = {
                'X-Tenant-ID': tenantId,
              };
              if (token) {
                headers['Authorization'] = `Bearer ${token}`;
              }
              const client = axios.create({
                baseURL,
                headers,
                timeout: 10000,
              });
              const response = await client.get('/api/v1/dashboards/cost', {
                params: { days: 30 }
              });
              setCostDetails(response.data);
            } catch (error) {
              // Silently fail
            } finally {
              setLoadingCostDetails(false);
            }
          }}
          onLoadLatencyDetails={async () => {
            setLoadingLatencyDetails(true);
            try {
              const baseURL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
              const getTenantId = () => {
                if (typeof document === 'undefined') return 'default';
                const match = document.cookie
                  .split('; ')
                  .find(row => row.startsWith('tenantId='));
                return match ? match.split('=')[1] : 'default';
              };
              const token = await getToken();
              const tenantId = getTenantId();
              const headers: Record<string, string> = {
                'X-Tenant-ID': tenantId,
              };
              if (token) {
                headers['Authorization'] = `Bearer ${token}`;
              }
              const client = axios.create({
                baseURL,
                headers,
                timeout: 10000,
              });
              const response = await client.get('/api/v1/dashboards/latency', {
                params: { days: 30 }
              });
              setLatencyDetails(response.data);
            } catch (error) {
              // Silently fail
            } finally {
              setLoadingLatencyDetails(false);
            }
          }}
          onLoadCacheDetails={async () => {
            setLoadingCacheDetails(true);
            try {
              const baseURL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
              const getTenantId = () => {
                if (typeof document === 'undefined') return 'default';
                const match = document.cookie
                  .split('; ')
                  .find(row => row.startsWith('tenantId='));
                return match ? match.split('=')[1] : 'default';
              };
              const token = await getToken();
              const tenantId = getTenantId();
              const headers: Record<string, string> = {
                'X-Tenant-ID': tenantId,
              };
              if (token) {
                headers['Authorization'] = `Bearer ${token}`;
              }
              const client = axios.create({
                baseURL,
                headers,
                timeout: 10000,
              });
              const response = await client.get('/api/v1/dashboards/cache', {
                params: { days: 30 }
              });
              setCacheDetails(response.data);
            } catch (error) {
              // Silently fail
            } finally {
              setLoadingCacheDetails(false);
            }
          }}
          onLoadRagQualityDetails={async () => {
            setLoadingRagQualityDetails(true);
            try {
              const baseURL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
              const getTenantId = () => {
                if (typeof document === 'undefined') return 'default';
                const match = document.cookie
                  .split('; ')
                  .find(row => row.startsWith('tenantId='));
                return match ? match.split('=')[1] : 'default';
              };
              const token = await getToken();
              const tenantId = getTenantId();
              const headers: Record<string, string> = {
                'X-Tenant-ID': tenantId,
              };
              if (token) {
                headers['Authorization'] = `Bearer ${token}`;
              }
              const client = axios.create({
                baseURL,
                headers,
                timeout: 10000,
              });
              const response = await client.get('/api/v1/dashboards/rag-quality', {
                params: { days: 30 }
              });
              setRagQualityDetails(response.data);
            } catch (error) {
              // Silently fail
            } finally {
              setLoadingRagQualityDetails(false);
            }
          }}
          onClose={() => {
            setSelectedCard(null);
            setTokenDetails(null);
            setCostDetails(null);
            setLatencyDetails(null);
            setCacheDetails(null);
            setRagQualityDetails(null);
          }}
        />
      )}
    </div>
  );
}

// Token Consumption Details Component
interface TokenConsumptionDetailsProps {
  data: DashboardData;
  tokenDetails: any;
  loading: boolean;
  onLoadDetails: () => Promise<void>;
}

function TokenConsumptionDetails({ data, tokenDetails, loading, onLoadDetails }: TokenConsumptionDetailsProps) {
  useEffect(() => {
    if (!tokenDetails && !loading) {
      onLoadDetails();
    }
  }, []);

  const summary = tokenDetails?.summary || {};
  const breakdown = tokenDetails?.breakdown || [];
  
  // Get input/output tokens from summary (API now provides these)
  const inputTokens = summary.input_tokens || summary.prompt_tokens;
  const outputTokens = summary.output_tokens || summary.completion_tokens;

  return (
    <div className="space-y-6">
      {/* Summary Stats */}
      <div className="grid grid-cols-2 gap-4">
        <div className="bg-surface rounded-xl p-4 border border-border-default">
          <h4 className="text-xs font-medium text-text-secondary mb-1">Total Tokens</h4>
          <p className="text-2xl font-bold text-text-primary">{formatNumber(summary.total_tokens || data.tokens?.total)}</p>
        </div>
        <div className="bg-surface rounded-xl p-4 border border-border-default">
          <h4 className="text-xs font-medium text-text-secondary mb-1">Total Calls</h4>
          <p className="text-2xl font-bold text-text-primary">{formatNumber(summary.total_calls || data.tokens?.totalCalls)}</p>
        </div>
        <div className="bg-surface rounded-xl p-4 border border-border-default">
          <h4 className="text-xs font-medium text-text-secondary mb-1">Avg Tokens/Call</h4>
          <p className="text-2xl font-bold text-text-primary">{formatNumber(summary.avg_tokens_per_call || data.tokens?.avgTokensPerCall)}</p>
        </div>
        <div className="bg-surface rounded-xl p-4 border border-border-default">
          <h4 className="text-xs font-medium text-text-secondary mb-1">Input Tokens</h4>
          <p className="text-2xl font-bold text-text-primary">
            {inputTokens !== undefined && inputTokens > 0 ? formatNumber(inputTokens) : '—'}
          </p>
        </div>
        <div className="bg-surface rounded-xl p-4 border border-border-default">
          <h4 className="text-xs font-medium text-text-secondary mb-1">Output Tokens</h4>
          <p className="text-2xl font-bold text-text-primary">
            {outputTokens !== undefined && outputTokens > 0 ? formatNumber(outputTokens) : '—'}
          </p>
        </div>
      </div>

      {/* Breakdown by Feature */}
      {breakdown.length > 0 && (
        <div>
          <h4 className="text-sm font-medium text-text-secondary mb-3">Breakdown by Feature</h4>
          <div className="space-y-2">
            {breakdown.map((item: any, idx: number) => (
              <div key={idx} className="bg-surface rounded-lg p-3 border border-border-default">
                <div className="flex justify-between items-start mb-2">
                  <div>
                    <p className="text-sm font-medium text-text-primary capitalize">{item.key}</p>
                    <p className="text-xs text-text-secondary mt-1">
                      {formatNumber(item.total_calls)} calls • {item.percentage.toFixed(1)}% of total
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-bold text-text-primary">{formatNumber(item.total_tokens)}</p>
                    <p className="text-xs text-text-secondary">Avg: {formatNumber(item.avg_tokens)}</p>
                  </div>
                </div>
                {(item.prompt_tokens || item.completion_tokens || item.input_tokens || item.output_tokens) && (
                  <div className="mt-2 pt-2 border-t border-border-default flex gap-4 text-xs">
                    <div>
                      <span className="text-text-secondary">Input: </span>
                      <span className="text-text-primary font-medium">
                        {formatNumber(item.input_tokens || item.prompt_tokens)}
                      </span>
                    </div>
                    <div>
                      <span className="text-text-secondary">Output: </span>
                      <span className="text-text-primary font-medium">
                        {formatNumber(item.output_tokens || item.completion_tokens)}
                      </span>
                    </div>
                  </div>
                )}
                <div className="w-full bg-surface-hover rounded-full h-2 overflow-hidden mt-2">
                  <div
                    className="bg-accent-blue h-full transition-all"
                    style={{ width: `${item.percentage}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Recent Trend */}
      {data.tokens?.trend && data.tokens.trend.length > 0 && (
        <div>
          <h4 className="text-sm font-medium text-text-secondary mb-3">Recent Trend (Last 7 Days)</h4>
          <div className="space-y-2">
            {data.tokens.trend.slice(-7).map((item, idx) => (
              <div key={idx} className="flex justify-between text-sm py-2 border-b border-border-default last:border-0">
                <span className="text-text-secondary">{new Date(item.date).toLocaleDateString()}</span>
                <span className="text-text-primary font-medium">{formatNumber(item.value)}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {loading && (
        <div className="flex items-center justify-center py-8">
          <div className="text-text-secondary">Loading detailed information...</div>
        </div>
      )}
    </div>
  );
}

// Cost Details Component
interface CostDetailsProps {
  data: DashboardData;
  costDetails: any;
  loading: boolean;
  onLoadDetails: () => Promise<void>;
}

function CostDetails({ data, costDetails, loading, onLoadDetails }: CostDetailsProps) {
  useEffect(() => {
    if (!costDetails && !loading) {
      onLoadDetails();
    }
  }, []);

  const summary = costDetails?.summary || {};
  const modelBreakdown = costDetails?.model_breakdown || [];
  const userBreakdown = costDetails?.user_breakdown || [];

  return (
    <div className="space-y-6">
      {/* Summary Stats */}
      <div className="grid grid-cols-2 gap-4">
        <div className="bg-surface rounded-xl p-4 border border-border-default">
          <h4 className="text-xs font-medium text-text-secondary mb-1">Total Cost</h4>
          <p className="text-2xl font-bold text-text-primary">{formatCurrency(summary.total_cost || data.cost?.total)}</p>
        </div>
        <div className="bg-surface rounded-xl p-4 border border-border-default">
          <h4 className="text-xs font-medium text-text-secondary mb-1">Total Calls</h4>
          <p className="text-2xl font-bold text-text-primary">{formatNumber(summary.total_calls)}</p>
        </div>
        <div className="bg-surface rounded-xl p-4 border border-border-default">
          <h4 className="text-xs font-medium text-text-secondary mb-1">Avg Cost/Call</h4>
          <p className="text-2xl font-bold text-text-primary">{formatCurrency(summary.avg_cost_per_call)}</p>
        </div>
        <div className="bg-surface rounded-xl p-4 border border-border-default">
          <h4 className="text-xs font-medium text-text-secondary mb-1">Daily Avg Cost</h4>
          <p className="text-2xl font-bold text-text-primary">{formatCurrency(summary.daily_avg_cost)}</p>
        </div>
      </div>

      {/* Model Breakdown */}
      {modelBreakdown.length > 0 && (
        <div>
          <h4 className="text-sm font-medium text-text-secondary mb-3">Breakdown by Model</h4>
          <div className="space-y-2">
            {modelBreakdown.map((item: any, idx: number) => (
              <div key={idx} className="bg-surface rounded-lg p-3 border border-border-default">
                <div className="flex justify-between items-start mb-2">
                  <div>
                    <p className="text-sm font-medium text-text-primary">{item.model}</p>
                    <p className="text-xs text-text-secondary mt-1">
                      {item.percentage?.toFixed(1)}% of total
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-bold text-text-primary">{formatCurrency(item.cost)}</p>
                  </div>
                </div>
                <div className="w-full bg-surface-hover rounded-full h-2 overflow-hidden">
                  <div
                    className="bg-accent-green h-full transition-all"
                    style={{ width: `${item.percentage || 0}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Recent Trend */}
      {data.cost?.trend && data.cost.trend.length > 0 && (
        <div>
          <h4 className="text-sm font-medium text-text-secondary mb-3">Recent Trend (Last 7 Days)</h4>
          <div className="space-y-2">
            {data.cost.trend.slice(-7).map((item, idx) => (
              <div key={idx} className="flex justify-between text-sm py-2 border-b border-border-default last:border-0">
                <span className="text-text-secondary">{new Date(item.date).toLocaleDateString()}</span>
                <span className="text-text-primary font-medium">{formatCurrency(item.value)}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {loading && (
        <div className="flex items-center justify-center py-8">
          <div className="text-text-secondary">Loading detailed information...</div>
        </div>
      )}
    </div>
  );
}

// Latency Details Component
interface LatencyDetailsProps {
  data: DashboardData;
  latencyDetails: any;
  loading: boolean;
  onLoadDetails: () => Promise<void>;
}

function LatencyDetails({ data, latencyDetails, loading, onLoadDetails }: LatencyDetailsProps) {
  useEffect(() => {
    if (!latencyDetails && !loading) {
      onLoadDetails();
    }
  }, []);

  const summary = latencyDetails?.summary || {};
  const byModel = latencyDetails?.by_model || [];
  const byFeature = latencyDetails?.by_feature || [];
  const bottlenecks = latencyDetails?.bottlenecks || [];

  return (
    <div className="space-y-6">
      {/* Summary Stats */}
      <div className="grid grid-cols-2 gap-4">
        <div className="bg-surface rounded-xl p-4 border border-border-default">
          <h4 className="text-xs font-medium text-text-secondary mb-1">Avg Latency</h4>
          <p className="text-2xl font-bold text-text-primary">{formatLatency(summary.avg_latency_ms || data.latency?.average)}</p>
        </div>
        <div className="bg-surface rounded-xl p-4 border border-border-default">
          <h4 className="text-xs font-medium text-text-secondary mb-1">P50 Latency</h4>
          <p className="text-2xl font-bold text-text-primary">{formatLatency(summary.p50_latency_ms)}</p>
        </div>
        <div className="bg-surface rounded-xl p-4 border border-border-default">
          <h4 className="text-xs font-medium text-text-secondary mb-1">P95 Latency</h4>
          <p className="text-2xl font-bold text-text-primary">{formatLatency(summary.p95_latency_ms)}</p>
        </div>
        <div className="bg-surface rounded-xl p-4 border border-border-default">
          <h4 className="text-xs font-medium text-text-secondary mb-1">P99 Latency</h4>
          <p className="text-2xl font-bold text-text-primary">{formatLatency(summary.p99_latency_ms)}</p>
        </div>
        <div className="bg-surface rounded-xl p-4 border border-border-default">
          <h4 className="text-xs font-medium text-text-secondary mb-1">Total Calls</h4>
          <p className="text-2xl font-bold text-text-primary">{formatNumber(summary.total_calls)}</p>
        </div>
      </div>

      {/* By Model */}
      {byModel.length > 0 && (
        <div>
          <h4 className="text-sm font-medium text-text-secondary mb-3">Latency by Model</h4>
          <div className="space-y-2">
            {byModel.map((item: any, idx: number) => (
              <div key={idx} className="bg-surface rounded-lg p-3 border border-border-default">
                <div className="flex justify-between items-start">
                  <div>
                    <p className="text-sm font-medium text-text-primary">{item.model}</p>
                    <p className="text-xs text-text-secondary mt-1">
                      {formatNumber(item.call_count)} calls
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-bold text-text-primary">{formatLatency(item.avg_latency_ms)}</p>
                    <p className="text-xs text-text-secondary">P95: {formatLatency(item.p95_latency_ms)}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Bottlenecks */}
      {bottlenecks.length > 0 && (
        <div>
          <h4 className="text-sm font-medium text-text-secondary mb-3">Bottlenecks</h4>
          <div className="space-y-2">
            {bottlenecks.map((item: any, idx: number) => (
              <div key={idx} className="bg-surface rounded-lg p-3 border border-red-500/50">
                <div className="flex justify-between items-start">
                  <div>
                    <p className="text-sm font-medium text-text-primary capitalize">{item.type}: {item.name}</p>
                    <p className="text-xs text-text-secondary mt-1">
                      Severity: <span className="text-red-500 font-medium">{item.severity}</span>
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-bold text-red-500">{formatLatency(item.p95_latency_ms)}</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Recent Trend */}
      {data.latency?.trend && data.latency.trend.length > 0 && (
        <div>
          <h4 className="text-sm font-medium text-text-secondary mb-3">Recent Trend (Last 7 Days)</h4>
          <div className="space-y-2">
            {data.latency.trend.slice(-7).map((item, idx) => (
              <div key={idx} className="flex justify-between text-sm py-2 border-b border-border-default last:border-0">
                <span className="text-text-secondary">{new Date(item.date).toLocaleDateString()}</span>
                <span className="text-text-primary font-medium">{formatLatency(item.value)}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {loading && (
        <div className="flex items-center justify-center py-8">
          <div className="text-text-secondary">Loading detailed information...</div>
        </div>
      )}
    </div>
  );
}

// Cache Details Component
interface CacheDetailsProps {
  data: DashboardData;
  cacheDetails: any;
  loading: boolean;
  onLoadDetails: () => Promise<void>;
}

function CacheDetails({ data, cacheDetails, loading, onLoadDetails }: CacheDetailsProps) {
  useEffect(() => {
    if (!cacheDetails && !loading) {
      onLoadDetails();
    }
  }, []);

  const summary = cacheDetails?.summary || {};
  const cacheTypeBreakdown = cacheDetails?.cache_type_breakdown || [];
  const performance = cacheDetails?.performance || {};

  return (
    <div className="space-y-6">
      {/* Summary Stats */}
      <div className="grid grid-cols-2 gap-4">
        <div className="bg-surface rounded-xl p-4 border border-border-default">
          <h4 className="text-xs font-medium text-text-secondary mb-1">Hit Rate</h4>
          <p className="text-2xl font-bold text-text-primary">{formatPercentage(summary.hit_rate || data.cache?.hitRate)}</p>
        </div>
        <div className="bg-surface rounded-xl p-4 border border-border-default">
          <h4 className="text-xs font-medium text-text-secondary mb-1">Total Operations</h4>
          <p className="text-2xl font-bold text-text-primary">{formatNumber(summary.total_operations)}</p>
        </div>
        <div className="bg-surface rounded-xl p-4 border border-border-default">
          <h4 className="text-xs font-medium text-text-secondary mb-1">Hits</h4>
          <p className="text-2xl font-bold text-text-primary">{formatNumber(summary.hits)}</p>
        </div>
        <div className="bg-surface rounded-xl p-4 border border-border-default">
          <h4 className="text-xs font-medium text-text-secondary mb-1">Misses</h4>
          <p className="text-2xl font-bold text-text-primary">{formatNumber(summary.misses)}</p>
        </div>
        <div className="bg-surface rounded-xl p-4 border border-border-default">
          <h4 className="text-xs font-medium text-text-secondary mb-1">Cost Savings</h4>
          <p className="text-2xl font-bold text-text-primary">{formatCurrency(summary.estimated_cost_savings)}</p>
        </div>
        <div className="bg-surface rounded-xl p-4 border border-border-default">
          <h4 className="text-xs font-medium text-text-secondary mb-1">Latency Improvement</h4>
          <p className="text-2xl font-bold text-text-primary">{formatLatency(performance.latency_improvement_ms)}</p>
        </div>
      </div>

      {/* Cache Type Breakdown */}
      {cacheTypeBreakdown.length > 0 && (
        <div>
          <h4 className="text-sm font-medium text-text-secondary mb-3">Breakdown by Cache Type</h4>
          <div className="space-y-2">
            {cacheTypeBreakdown.map((item: any, idx: number) => (
              <div key={idx} className="bg-surface rounded-lg p-3 border border-border-default">
                <div className="flex justify-between items-start mb-2">
                  <div>
                    <p className="text-sm font-medium text-text-primary capitalize">{item.cache_type}</p>
                    <p className="text-xs text-text-secondary mt-1">
                      {formatNumber(item.hits)} hits • {formatNumber(item.misses)} misses • {formatNumber(item.total)} total
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-bold text-text-primary">{formatPercentage(item.hit_rate)}</p>
                  </div>
                </div>
                <div className="w-full bg-surface-hover rounded-full h-2 overflow-hidden">
                  <div
                    className="bg-accent-blue h-full transition-all"
                    style={{ width: `${(item.hit_rate || 0) * 100}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Recent Trend */}
      {data.cache?.trend && data.cache.trend.length > 0 && (
        <div>
          <h4 className="text-sm font-medium text-text-secondary mb-3">Recent Trend (Last 7 Days)</h4>
          <div className="space-y-2">
            {data.cache.trend.slice(-7).map((item, idx) => (
              <div key={idx} className="flex justify-between text-sm py-2 border-b border-border-default last:border-0">
                <span className="text-text-secondary">{new Date(item.date).toLocaleDateString()}</span>
                <span className="text-text-primary font-medium">{formatPercentage(item.value)}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {loading && (
        <div className="flex items-center justify-center py-8">
          <div className="text-text-secondary">Loading detailed information...</div>
        </div>
      )}
    </div>
  );
}

// RAG Quality Details Component
interface RAGQualityDetailsProps {
  data: DashboardData;
  ragQualityDetails: any;
  loading: boolean;
  onLoadDetails: () => Promise<void>;
}

function RAGQualityDetails({ data, ragQualityDetails, loading, onLoadDetails }: RAGQualityDetailsProps) {
  useEffect(() => {
    if (!ragQualityDetails && !loading) {
      onLoadDetails();
    }
  }, []);

  const summary = ragQualityDetails?.summary || {};
  const dailyBreakdown = ragQualityDetails?.daily_breakdown || [];

  return (
    <div className="space-y-6">
      {/* Summary Stats */}
      <div className="grid grid-cols-2 gap-4">
        <div className="bg-surface rounded-xl p-4 border border-border-default">
          <h4 className="text-xs font-medium text-text-secondary mb-1">Quality Score</h4>
          <p className="text-2xl font-bold text-text-primary">
            {data.ragQuality?.score ? `${data.ragQuality.score.toFixed(1)}/10` : '—'}
          </p>
        </div>
        <div className="bg-surface rounded-xl p-4 border border-border-default">
          <h4 className="text-xs font-medium text-text-secondary mb-1">Total Feedback</h4>
          <p className="text-2xl font-bold text-text-primary">{formatNumber(summary.total_feedback)}</p>
        </div>
        <div className="bg-surface rounded-xl p-4 border border-border-default">
          <h4 className="text-xs font-medium text-text-secondary mb-1">Thumbs Up</h4>
          <p className="text-2xl font-bold text-text-primary">{formatNumber(summary.thumbs_up)}</p>
        </div>
        <div className="bg-surface rounded-xl p-4 border border-border-default">
          <h4 className="text-xs font-medium text-text-secondary mb-1">Thumbs Down</h4>
          <p className="text-2xl font-bold text-text-primary">{formatNumber(summary.thumbs_down)}</p>
        </div>
        <div className="bg-surface rounded-xl p-4 border border-border-default">
          <h4 className="text-xs font-medium text-text-secondary mb-1">Positive Rate</h4>
          <p className="text-2xl font-bold text-text-primary">{formatPercentage((summary.positive_rate || 0) * 100)}</p>
        </div>
        <div className="bg-surface rounded-xl p-4 border border-border-default">
          <h4 className="text-xs font-medium text-text-secondary mb-1">Hallucination Rate</h4>
          <p className="text-2xl font-bold text-text-primary">{formatPercentage((summary.hallucination_rate || 0) * 100)}</p>
        </div>
      </div>

      {/* Daily Breakdown */}
      {dailyBreakdown.length > 0 && (
        <div>
          <h4 className="text-sm font-medium text-text-secondary mb-3">Daily Breakdown</h4>
          <div className="space-y-2">
            {dailyBreakdown.slice(-7).map((item: any, idx: number) => (
              <div key={idx} className="bg-surface rounded-lg p-3 border border-border-default">
                <div className="flex justify-between items-start mb-2">
                  <div>
                    <p className="text-sm font-medium text-text-primary">{new Date(item.date).toLocaleDateString()}</p>
                    <p className="text-xs text-text-secondary mt-1">
                      {formatNumber(item.total)} total • {formatNumber(item.thumbs_up)} up • {formatNumber(item.thumbs_down)} down
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-bold text-text-primary">{formatPercentage((item.hallucination_rate || 0) * 100)}</p>
                    <p className="text-xs text-text-secondary">Hallucination</p>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Recent Trend */}
      {data.ragQuality?.trend && data.ragQuality.trend.length > 0 && (
        <div>
          <h4 className="text-sm font-medium text-text-secondary mb-3">Recent Trend (Last 7 Days)</h4>
          <div className="space-y-2">
            {data.ragQuality.trend.slice(-7).map((item, idx) => (
              <div key={idx} className="flex justify-between text-sm py-2 border-b border-border-default last:border-0">
                <span className="text-text-secondary">{new Date(item.date).toLocaleDateString()}</span>
                <span className="text-text-primary font-medium">{item.value.toFixed(1)}/10</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {loading && (
        <div className="flex items-center justify-center py-8">
          <div className="text-text-secondary">Loading detailed information...</div>
        </div>
      )}
    </div>
  );
}

// Metric Detail Modal Component
interface MetricDetailModalProps {
  cardType: string;
  data: DashboardData;
  tokenDetails: any;
  loadingTokenDetails: boolean;
  costDetails: any;
  loadingCostDetails: boolean;
  latencyDetails: any;
  loadingLatencyDetails: boolean;
  cacheDetails: any;
  loadingCacheDetails: boolean;
  ragQualityDetails: any;
  loadingRagQualityDetails: boolean;
  onLoadTokenDetails: () => Promise<void>;
  onLoadCostDetails: () => Promise<void>;
  onLoadLatencyDetails: () => Promise<void>;
  onLoadCacheDetails: () => Promise<void>;
  onLoadRagQualityDetails: () => Promise<void>;
  onClose: () => void;
}

function MetricDetailModal({ 
  cardType, 
  data, 
  tokenDetails, 
  loadingTokenDetails,
  costDetails,
  loadingCostDetails,
  latencyDetails,
  loadingLatencyDetails,
  cacheDetails,
  loadingCacheDetails,
  ragQualityDetails,
  loadingRagQualityDetails,
  onLoadTokenDetails,
  onLoadCostDetails,
  onLoadLatencyDetails,
  onLoadCacheDetails,
  onLoadRagQualityDetails,
  onClose 
}: MetricDetailModalProps) {
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };
    document.addEventListener('keydown', handleEscape);
    document.body.style.overflow = 'hidden';
    return () => {
      document.removeEventListener('keydown', handleEscape);
      document.body.style.overflow = 'unset';
    };
  }, [onClose]);

  const getModalContent = () => {
    switch (cardType) {
      case 'tokens':
        return {
          title: 'Token Consumption Details',
          content: (
            <TokenConsumptionDetails
              data={data}
              tokenDetails={tokenDetails}
              loading={loadingTokenDetails}
              onLoadDetails={onLoadTokenDetails}
            />
          ),
        };
      case 'cost':
        return {
          title: 'Cost Details',
          content: (
            <CostDetails
              data={data}
              costDetails={costDetails}
              loading={loadingCostDetails}
              onLoadDetails={onLoadCostDetails}
            />
          ),
        };
      case 'latency':
        return {
          title: 'Latency Details',
          content: (
            <LatencyDetails
              data={data}
              latencyDetails={latencyDetails}
              loading={loadingLatencyDetails}
              onLoadDetails={onLoadLatencyDetails}
            />
          ),
        };
      case 'cache':
        return {
          title: 'Cache Efficiency Details',
          content: (
            <CacheDetails
              data={data}
              cacheDetails={cacheDetails}
              loading={loadingCacheDetails}
              onLoadDetails={onLoadCacheDetails}
            />
          ),
        };
      case 'rag-quality':
        return {
          title: 'RAG Quality Details',
          content: (
            <div className="space-y-4">
              <div>
                <h4 className="text-sm font-medium text-text-secondary mb-2">Quality Score</h4>
                <p className="text-2xl font-bold text-text-primary">
                  {data.ragQuality?.score ? `${data.ragQuality.score.toFixed(1)}/10` : '—'}
                </p>
              </div>
              {data.ragQuality?.trend && data.ragQuality.trend.length > 0 && (
                <div>
                  <h4 className="text-sm font-medium text-text-secondary mb-2">Recent Trend</h4>
                  <div className="space-y-2">
                    {data.ragQuality.trend.slice(-7).map((item, idx) => (
                      <div key={idx} className="flex justify-between text-sm">
                        <span className="text-text-secondary">{new Date(item.date).toLocaleDateString()}</span>
                        <span className="text-text-primary font-medium">{item.value.toFixed(1)}/10</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ),
        };
      case 'alerts':
        return {
          title: 'Active Alerts Details',
          content: (
            <div className="space-y-4">
              <div>
                <h4 className="text-sm font-medium text-text-secondary mb-2">Active Alerts Count</h4>
                <p className="text-2xl font-bold text-text-primary">{formatNumber(data.alerts?.active)}</p>
              </div>
            </div>
          ),
        };
      default:
        return { title: 'Details', content: <div>No details available</div> };
    }
  };

  const { title, content } = getModalContent();

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="bg-modal rounded-2xl border border-border-default shadow-xl max-w-2xl w-full mx-4 max-h-[80vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between p-6 border-b border-border-default">
          <h2 className="text-xl font-semibold text-text-primary">{title}</h2>
          <button
            onClick={onClose}
            className="p-2 rounded-lg hover:bg-surface-hover transition-colors text-text-secondary hover:text-text-primary"
            aria-label="Close modal"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
        <div className="p-6">{content}</div>
      </div>
    </div>
  );
}
