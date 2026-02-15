/**
 * Analytics Dashboard Page
 * 
 * Admin master dashboard with aggregate metrics, user list, and detailed views.
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
  Users,
  X,
  ChevronRight,
  RefreshCw,
  AlertCircle
} from 'lucide-react';
import { MetricCard } from '@/components/analytics/MetricCard';
import { useAuth } from '@clerk/nextjs';
import { apiClient } from '@/lib/api-client';

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

const REFRESH_INTERVAL = 3600000; // 1 hour (3600000 milliseconds)

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
  data: { date: string; [key: string]: any }[] | undefined,
  valueKey: string,
  label: string,
  color: string
) => {
  if (!data || data.length === 0) {
    return {
      labels: [],
      datasets: [],
    };
  }

  return {
    labels: data.map((item) => {
      const date = new Date(item.date);
      return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    }),
    datasets: [
      {
        label,
        data: data.map((item) => item[valueKey] || 0),
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

export default function AnalyticsDashboardPage() {
  const { getToken } = useAuth();
  const [mounted, setMounted] = useState(false);
  const [authLoaded, setAuthLoaded] = useState(false);
  const [isAdmin, setIsAdmin] = useState<boolean | null>(null);
  
  // Admin data state
  const [users, setUsers] = useState<any[]>([]);
  const [aggregateMetrics, setAggregateMetrics] = useState<any>(null);
  const [selectedUser, setSelectedUser] = useState<string | null>(null);
  const [userMetrics, setUserMetrics] = useState<any>(null);
  const [adminAlertStatus, setAdminAlertStatus] = useState<any>(null);
  
  // User data state (for non-admin users)
  const [myMetrics, setMyMetrics] = useState<any>(null);
  const [alertStatus, setAlertStatus] = useState<any>(null);
  const [trendData, setTrendData] = useState<{
    tokens?: { date: string; tokens: number }[];
    cost?: { date: string; cost: number }[];
    latency?: { date: string; avg_latency_ms: number }[];
    cache?: { date: string; hit_rate: number }[];
    ragQuality?: { date: string; positive_rate: number }[];
  }>({});
  
  // Loading states
  const [loadingUsers, setLoadingUsers] = useState(false);
  const [loadingAggregate, setLoadingAggregate] = useState(false);
  const [loadingUserMetrics, setLoadingUserMetrics] = useState(false);
  const [loadingMyMetrics, setLoadingMyMetrics] = useState(false);
  const [loadingTrends, setLoadingTrends] = useState(false);
  const [loadingAlerts, setLoadingAlerts] = useState(false);
  const [loadingAdminAlerts, setLoadingAdminAlerts] = useState(false);
  
  // Admin metric detail state
  const [selectedAdminMetric, setSelectedAdminMetric] = useState<string | null>(null);
  const [adminMetricDetails, setAdminMetricDetails] = useState<any>(null);
  const [loadingAdminMetricDetails, setLoadingAdminMetricDetails] = useState(false);
  
  // User metric detail state
  const [selectedUserMetric, setSelectedUserMetric] = useState<string | null>(null);
  
  // Admin RAG quality state
  const [ragQuality, setRagQuality] = useState<any>(null);
  const [loadingRagQuality, setLoadingRagQuality] = useState(false);
  
  const [lastRefresh, setLastRefresh] = useState<Date>(new Date());

  // Set mounted state
  useEffect(() => {
    setMounted(true);
  }, []);

  // Check auth loaded
  useEffect(() => {
    if (getToken) {
      setAuthLoaded(true);
    }
  }, [getToken]);

  // Check if user is admin
  useEffect(() => {
    const checkAdmin = async () => {
      if (!authLoaded) {
        return;
      }
      
      if (!getToken) {
        return;
      }
      
      // Ensure token getter is set in API client
      apiClient.setTokenGetter(getToken);
      
      // Wait a bit for token to be fetched
      await new Promise(resolve => setTimeout(resolve, 2000));
      
      try {
        // Use silent=true to suppress error logging for expected 403s
        await apiClient.getAggregateMetrics(30, true);
        setIsAdmin(true);
      } catch (error: any) {
        if (error?.response?.status === 403) {
          // Expected 403 for non-admin users - silently set isAdmin to false
          setIsAdmin(false);
        } else if (error?.response?.status === 401) {
          // Token issue - might need more time
          setTimeout(async () => {
            try {
              await apiClient.getAggregateMetrics(30, true);
              setIsAdmin(true);
            } catch (retryError: any) {
              setIsAdmin(false);
            }
          }, 2000);
        } else {
          setIsAdmin(false);
        }
      }
    };
    
    if (mounted && authLoaded && getToken) {
      checkAdmin();
    }
  }, [mounted, authLoaded, getToken]);

  // Fetch admin data
  const fetchAdminData = useCallback(async () => {
    if (!isAdmin) return;
    
    setLoadingUsers(true);
    setLoadingAggregate(true);
    setLoadingRagQuality(false);
    
    try {
      // Ensure token is ready
      await new Promise(resolve => setTimeout(resolve, 500));
      
      const [usersRes, aggregateRes, alertsRes] = await Promise.allSettled([
        apiClient.listAllUsers(),
        apiClient.getAggregateMetrics(30),
        apiClient.getAlertsStatus(),
      ]);
      
      if (usersRes.status === 'fulfilled') {
        setUsers(usersRes.value.users || []);
      } else {
        console.error('[ADMIN] Failed to fetch users:', usersRes.reason);
      }
      
      if (aggregateRes.status === 'fulfilled') {
        const agg = aggregateRes.value;
        // Update total users from users list if available
        if (usersRes.status === 'fulfilled' && usersRes.value.users) {
          agg.users = {
            ...agg.users,
            total: usersRes.value.users.length,
          };
        }
        setAggregateMetrics(agg);
        
        // Extract RAG quality from aggregate response if available
        if (agg.rag_quality) {
          setRagQuality(agg.rag_quality);
        } else {
          setRagQuality(null);
        }
        
        setLastRefresh(new Date());
      } else {
        console.error('[ADMIN] Failed to fetch aggregate metrics:', aggregateRes.reason);
        setRagQuality(null);
      }

      if (alertsRes.status === 'fulfilled') {
        setAdminAlertStatus(alertsRes.value);
      } else {
        console.error('[ADMIN] Failed to fetch alert status:', alertsRes.reason);
      }
    } catch (error) {
      console.error('[ADMIN] Error fetching admin data:', error);
    } finally {
      setLoadingUsers(false);
      setLoadingAggregate(false);
    }
  }, [isAdmin]);

  // Fetch user metrics when user is selected
  const fetchUserMetrics = useCallback(async (userId: string) => {
    setLoadingUserMetrics(true);
    try {
      const metrics = await apiClient.getUserMetrics(userId, 30);
      setUserMetrics(metrics);
    } catch (error) {
      console.error('Error fetching user metrics:', error);
    } finally {
      setLoadingUserMetrics(false);
    }
  }, []);

  // Fetch admin metric details
  const fetchAdminMetricDetails = useCallback(async (metricType: string) => {
    if (!isAdmin) return;
    
    setLoadingAdminMetricDetails(true);
    try {
      // The aggregate metrics already contain all the details we need
      if (aggregateMetrics) {
        setAdminMetricDetails(aggregateMetrics);
      }
    } catch (error) {
      console.error('Error fetching admin metric details:', error);
    } finally {
      setLoadingAdminMetricDetails(false);
    }
  }, [isAdmin, aggregateMetrics]);

  // Fetch user metrics for non-admin users
  const fetchMyMetrics = useCallback(async () => {
    if (isAdmin !== false) return; // Only fetch if we know user is not admin
    
    setLoadingMyMetrics(true);
    try {
      await new Promise(resolve => setTimeout(resolve, 500));
      const metrics = await apiClient.getMyMetrics(30);
      setMyMetrics(metrics);
      setLastRefresh(new Date());
    } catch (error) {
      console.error('[USER] Error fetching my metrics:', error);
    } finally {
      setLoadingMyMetrics(false);
    }
  }, [isAdmin]);

  // Fetch alert status
  const fetchAlertStatus = useCallback(async () => {
    if (isAdmin !== false) return; // Only fetch if we know user is not admin
    
    setLoadingAlerts(true);
    try {
      const status = await apiClient.getAlertsStatus();
      setAlertStatus(status);
    } catch (error) {
      console.error('[USER] Error fetching alert status:', error);
    } finally {
      setLoadingAlerts(false);
    }
  }, [isAdmin]);

  // Fetch trend data for charts
  const fetchTrendData = useCallback(async () => {
    if (isAdmin !== false) return; // Only fetch if we know user is not admin
    
    setLoadingTrends(true);
    try {
      const [tokenData, costData, latencyData, cacheData, ragData] = await Promise.allSettled([
        apiClient.getTokenConsumption(30),
        apiClient.getCostTracking(30),
        apiClient.getLatencyDashboard(30),
        apiClient.getCacheEfficiency(30),
        apiClient.getRagQuality(30),
      ]);

      const trends: any = {};
      
      if (tokenData.status === 'fulfilled' && tokenData.value?.daily_breakdown) {
        trends.tokens = tokenData.value.daily_breakdown.map((item: any) => ({
          date: item.date,
          tokens: item.tokens,
        }));
      }
      
      if (costData.status === 'fulfilled' && costData.value?.daily_breakdown) {
        trends.cost = costData.value.daily_breakdown.map((item: any) => ({
          date: item.date,
          cost: item.cost,
        }));
      }
      
      if (latencyData.status === 'fulfilled' && latencyData.value?.daily_breakdown) {
        trends.latency = latencyData.value.daily_breakdown.map((item: any) => ({
          date: item.date,
          avg_latency_ms: item.avg_latency_ms,
        }));
      }
      
      if (cacheData.status === 'fulfilled') {
        // Cache efficiency doesn't have daily breakdown, we'll need to calculate from cache operations
        // For now, we'll skip it or use a placeholder
      }
      
      if (ragData.status === 'fulfilled' && ragData.value?.daily_breakdown) {
        trends.ragQuality = ragData.value.daily_breakdown.map((item: any) => ({
          date: item.date,
          positive_rate: item.hallucination_rate !== undefined ? 1 - item.hallucination_rate : item.positive_rate || 0,
        }));
      }
      
      setTrendData(trends);
    } catch (error) {
      console.error('[USER] Error fetching trend data:', error);
    } finally {
      setLoadingTrends(false);
    }
  }, [isAdmin]);

  useEffect(() => {
    if (isAdmin === true) {
      fetchAdminData();
      const interval = setInterval(fetchAdminData, REFRESH_INTERVAL);
      return () => clearInterval(interval);
    } else if (isAdmin === false) {
      fetchMyMetrics();
      fetchTrendData();
      fetchAlertStatus();
      const interval = setInterval(() => {
        fetchMyMetrics();
        fetchTrendData();
        fetchAlertStatus();
      }, REFRESH_INTERVAL);
      return () => clearInterval(interval);
    }
  }, [isAdmin, fetchAdminData, fetchMyMetrics, fetchTrendData, fetchAlertStatus]);

  useEffect(() => {
    if (selectedUser) {
      fetchUserMetrics(selectedUser);
    }
  }, [selectedUser, fetchUserMetrics]);

  // Show admin dashboard if user is admin
  if (isAdmin === true) {
    return (
      <div className="h-full flex flex-col overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-border-default">
          <div className="flex items-center gap-4">
            <div>
              <h1 className="text-2xl font-semibold text-text-primary">Master Dashboard</h1>
              <p className="text-sm text-text-secondary mt-1" suppressHydrationWarning>
                Last updated: {mounted && lastRefresh ? lastRefresh.toLocaleTimeString() : '—'}
              </p>
            </div>
            <button
              onClick={() => {
                fetchAdminData();
                if (selectedUser) {
                  fetchUserMetrics(selectedUser);
                }
              }}
              disabled={loadingAggregate || loadingUsers}
              className="flex items-center gap-2 px-4 py-2 rounded-lg bg-surface-hover border border-border-default hover:bg-surface-hover/80 transition-colors disabled:opacity-50 disabled:cursor-not-allowed text-text-secondary hover:text-text-primary"
              title="Refresh metrics"
            >
              <RefreshCw className={`w-4 h-4 ${(loadingAggregate || loadingUsers) ? 'animate-spin' : ''}`} />
              <span className="text-sm font-medium">Refresh</span>
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {/* Aggregate Metrics Cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4 mb-8">
            <MetricCard
              title="Total Tokens"
              value={formatNumber(aggregateMetrics?.metrics?.tokens?.total || aggregateMetrics?.usage?.total_tokens)}
              icon={<TrendingUp className="w-5 h-5" />}
              isLoading={loadingAggregate}
              onClick={() => {
                setSelectedAdminMetric('tokens');
                fetchAdminMetricDetails('tokens');
              }}
            />
            <MetricCard
              title="Total Cost"
              value={formatCurrency(aggregateMetrics?.metrics?.costs?.total || aggregateMetrics?.usage?.total_cost)}
              icon={<DollarSign className="w-5 h-5" />}
              isLoading={loadingAggregate}
              onClick={() => {
                setSelectedAdminMetric('cost');
                fetchAdminMetricDetails('cost');
              }}
            />
            <MetricCard
              title="Avg Latency"
              value={formatLatency(aggregateMetrics?.metrics?.latency?.average)}
              icon={<Clock className="w-5 h-5" />}
              isLoading={loadingAggregate}
              onClick={() => {
                setSelectedAdminMetric('latency');
                fetchAdminMetricDetails('latency');
              }}
            />
            <MetricCard
              title="Total Users"
              value={formatNumber(users.length || aggregateMetrics?.users?.total)}
              icon={<Users className="w-5 h-5" />}
              isLoading={loadingUsers || loadingAggregate}
            />
            <MetricCard
              title="RAG Quality"
              value={
                ragQuality?.summary?.positive_rate !== undefined && ragQuality.summary.positive_rate !== null
                  ? `${(ragQuality.summary.positive_rate * 10).toFixed(1)}/10`
                  : ragQuality?.summary?.total_feedback !== undefined && ragQuality.summary.total_feedback === 0
                  ? 'No feedback'
                  : '—'
              }
              icon={<CheckCircle className="w-5 h-5" />}
              isLoading={loadingRagQuality || loadingAggregate}
              onClick={() => {
                setSelectedAdminMetric('rag-quality');
                fetchAdminMetricDetails('rag-quality');
              }}
            />
            <MetricCard
              title="Cache Hit %"
              value={formatPercentage(aggregateMetrics?.metrics?.cache?.hit_rate != null ? aggregateMetrics.metrics.cache.hit_rate * 100 : undefined)}
              icon={<Database className="w-5 h-5" />}
              isLoading={loadingAggregate}
              onClick={() => {
                setSelectedAdminMetric('cache');
                fetchAdminMetricDetails('cache');
              }}
            />
            <MetricCard
              title="Active Alerts"
              value={formatNumber(adminAlertStatus?.status?.active_alerts || 0)}
              icon={<AlertCircle className="w-5 h-5" />}
              isLoading={loadingAggregate}
              onClick={() => {
                setSelectedAdminMetric('alerts');
                fetchAdminMetricDetails('alerts');
              }}
            />
          </div>

          {/* User List and Details */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* User List */}
            <div className="lg:col-span-1 bg-surface rounded-2xl border border-border-default p-6">
              <h2 className="text-lg font-semibold text-text-primary mb-4 flex items-center gap-2">
                <Users className="w-5 h-5" />
                All Users
              </h2>
              <div className="space-y-2 max-h-[calc(100vh-300px)] overflow-y-auto">
                {loadingUsers ? (
                  <div className="text-text-secondary text-center py-8">Loading users...</div>
                ) : users.length === 0 ? (
                  <div className="text-text-secondary text-center py-8">No users found</div>
                ) : (
                  users.map((user) => (
                    <button
                      key={user.id}
                      onClick={() => setSelectedUser(user.clerk_user_id || user.id)}
                      className={`w-full text-left p-3 rounded-lg border transition-colors ${
                        selectedUser === (user.clerk_user_id || user.id)
                          ? 'bg-accent-blue/10 border-accent-blue text-text-primary'
                          : 'bg-surface-hover border-border-default text-text-secondary hover:bg-surface-hover/80'
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium text-text-primary truncate">{user.email || user.username || 'N/A'}</p>
                          <p className="text-xs text-text-secondary mt-1">
                            {user.role === 'admin' ? 'Admin' : 'User'}
                          </p>
                        </div>
                        <ChevronRight className="w-4 h-4 text-text-tertiary flex-shrink-0 ml-2" />
                      </div>
                    </button>
                  ))
                )}
              </div>
            </div>

            {/* User Details */}
            <div className="lg:col-span-2 bg-surface rounded-2xl border border-border-default p-6">
              {selectedUser ? (
                <>
                  <h2 className="text-lg font-semibold text-text-primary mb-4">User Details</h2>
                  {loadingUserMetrics ? (
                    <div className="text-text-secondary text-center py-8">Loading user metrics...</div>
                  ) : userMetrics ? (
                    <div className="space-y-6">
                      {/* User Summary Cards */}
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                        <button
                          onClick={() => setSelectedUserMetric('tokens')}
                          className="bg-surface-hover rounded-xl p-4 border border-border-default hover:border-accent-blue transition-colors text-left cursor-pointer"
                        >
                          <h4 className="text-xs font-medium text-text-secondary mb-1">Total Tokens</h4>
                          <p className="text-xl font-bold text-text-primary">
                            {formatNumber(userMetrics.summary?.tokens?.total || userMetrics.usage?.total_tokens)}
                          </p>
                        </button>
                        <button
                          onClick={() => setSelectedUserMetric('cost')}
                          className="bg-surface-hover rounded-xl p-4 border border-border-default hover:border-accent-blue transition-colors text-left cursor-pointer"
                        >
                          <h4 className="text-xs font-medium text-text-secondary mb-1">Total Cost</h4>
                          <p className="text-xl font-bold text-text-primary">
                            {formatCurrency(userMetrics.summary?.costs?.total || userMetrics.usage?.total_cost)}
                          </p>
                        </button>
                        <button
                          onClick={() => setSelectedUserMetric('latency')}
                          className="bg-surface-hover rounded-xl p-4 border border-border-default hover:border-accent-blue transition-colors text-left cursor-pointer"
                        >
                          <h4 className="text-xs font-medium text-text-secondary mb-1">Avg Latency</h4>
                          <p className="text-xl font-bold text-text-primary">
                            {formatLatency(userMetrics.summary?.latency?.average)}
                          </p>
                        </button>
                        <button
                          onClick={() => setSelectedUserMetric('cache')}
                          className="bg-surface-hover rounded-xl p-4 border border-border-default hover:border-accent-blue transition-colors text-left cursor-pointer"
                        >
                          <h4 className="text-xs font-medium text-text-secondary mb-1">Cache Hit %</h4>
                          <p className="text-xl font-bold text-text-primary">
                            {formatPercentage(
                              userMetrics.summary?.cache?.hit_rate != null && userMetrics.summary.cache.hit_rate !== null
                                ? userMetrics.summary.cache.hit_rate * 100
                                : undefined
                            )}
                          </p>
                        </button>
                      </div>

                      {/* Endpoints */}
                      {userMetrics.endpoints && userMetrics.endpoints.length > 0 ? (
                        <div>
                          <h3 className="text-sm font-semibold text-text-primary mb-3">Endpoint Usage</h3>
                          <div className="space-y-2">
                            {userMetrics.endpoints.map((endpoint: any, idx: number) => (
                              <div key={idx} className="bg-surface-hover rounded-lg p-4 border border-border-default">
                                <div className="flex justify-between items-start mb-2">
                                  <div>
                                    <p className="text-sm font-medium text-text-primary capitalize">{endpoint.endpoint}</p>
                                    <p className="text-xs text-text-secondary mt-1">
                                      {formatNumber(endpoint.total_calls)} calls
                                    </p>
                                  </div>
                                  <div className="text-right">
                                    <p className="text-sm font-bold text-text-primary">
                                      Tokens: {formatNumber(endpoint.total_tokens)}
                                    </p>
                                    <p className="text-xs text-text-secondary">
                                      Cost: {formatCurrency(endpoint.total_cost)}
                                    </p>
                                    {endpoint.avg_latency && (
                                      <p className="text-xs text-text-secondary">
                                        Avg Latency: {formatLatency(endpoint.avg_latency)}
                                      </p>
                                    )}
                                  </div>
                                </div>
                                <div className="w-full bg-border-default rounded-full h-2.5">
                                  <div
                                    className="bg-accent-blue h-full transition-all"
                                    style={{
                                      width: `${Math.min((endpoint.total_tokens / (userMetrics.summary?.tokens?.total || 1)) * 100, 100)}%`,
                                    }}
                                  />
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>
                      ) : (
                        <div className="text-text-secondary text-center py-8">No endpoint usage data available</div>
                      )}
                    </div>
                  ) : (
                    <div className="text-text-secondary text-center py-8">No metrics available</div>
                  )}
                </>
              ) : (
                <div className="text-text-secondary text-center py-8">
                  Select a user from the list to view their details
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Admin Metric Detail Modal */}
        {selectedAdminMetric && (
          <AdminMetricDetailModal
            metricType={selectedAdminMetric}
            aggregateMetrics={aggregateMetrics}
            details={{ ...adminMetricDetails, ragQuality }}
            loading={loadingAdminMetricDetails}
            onClose={() => setSelectedAdminMetric(null)}
          />
        )}

        {/* User Metric Detail Modal */}
        {selectedUserMetric && selectedUser && userMetrics && (
          <UserMetricDetailModal
            metricType={selectedUserMetric}
            userMetrics={userMetrics}
            onClose={() => setSelectedUserMetric(null)}
          />
        )}
      </div>
    );
  }

  // Show loading
  if (isAdmin === null) {
    return (
      <div className="h-full flex items-center justify-center">
        <p className="text-text-secondary">Loading...</p>
      </div>
    );
  }

  // Show user dashboard for non-admin users
  if (isAdmin === false) {
    return (
      <div className="h-full flex flex-col overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-border-default">
          <div className="flex items-center gap-4">
            <div>
              <h1 className="text-2xl font-semibold text-text-primary">My Dashboard</h1>
              <p className="text-sm text-text-secondary mt-1" suppressHydrationWarning>
                Last updated: {mounted && lastRefresh ? lastRefresh.toLocaleTimeString() : '—'}
              </p>
            </div>
            <button
              onClick={() => {
                fetchMyMetrics();
                fetchTrendData();
                fetchAlertStatus();
              }}
              disabled={loadingMyMetrics || loadingTrends || loadingAlerts}
              className="flex items-center gap-2 px-4 py-2 rounded-lg bg-surface-hover border border-border-default hover:bg-surface-hover/80 transition-colors disabled:opacity-50 disabled:cursor-not-allowed text-text-secondary hover:text-text-primary"
              title="Refresh metrics"
            >
              <RefreshCw className={`w-4 h-4 ${(loadingMyMetrics || loadingTrends || loadingAlerts) ? 'animate-spin' : ''}`} />
              <span className="text-sm font-medium">Refresh</span>
            </button>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {/* User Metrics Cards */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4 mb-8">
            <MetricCard
              title="Total Tokens"
              value={formatNumber(myMetrics?.summary?.tokens?.total || myMetrics?.usage?.total_tokens)}
              icon={<TrendingUp className="w-5 h-5" />}
              isLoading={loadingMyMetrics}
              onClick={() => {
                setSelectedUserMetric('tokens');
              }}
            />
            <MetricCard
              title="Total Cost"
              value={formatCurrency(myMetrics?.summary?.costs?.total || myMetrics?.usage?.total_cost)}
              icon={<DollarSign className="w-5 h-5" />}
              isLoading={loadingMyMetrics}
              onClick={() => {
                setSelectedUserMetric('cost');
              }}
            />
            <MetricCard
              title="Avg Latency"
              value={formatLatency(myMetrics?.summary?.latency?.average)}
              icon={<Clock className="w-5 h-5" />}
              isLoading={loadingMyMetrics}
              onClick={() => {
                setSelectedUserMetric('latency');
              }}
            />
            <MetricCard
              title="RAG Quality"
              value={
                myMetrics?.rag_quality?.summary?.positive_rate !== undefined && myMetrics.rag_quality.summary.positive_rate !== null
                  ? `${(myMetrics.rag_quality.summary.positive_rate * 10).toFixed(1)}/10`
                  : myMetrics?.rag_quality?.summary?.total_feedback !== undefined && myMetrics.rag_quality.summary.total_feedback === 0
                  ? 'No feedback'
                  : '—'
              }
              icon={<CheckCircle className="w-5 h-5" />}
              isLoading={loadingMyMetrics}
              onClick={() => {
                setSelectedUserMetric('rag-quality');
              }}
            />
            <MetricCard
              title="Cache Hit %"
              value={formatPercentage(myMetrics?.summary?.cache?.hit_rate != null ? myMetrics.summary.cache.hit_rate * 100 : undefined)}
              icon={<Database className="w-5 h-5" />}
              isLoading={loadingMyMetrics}
              onClick={() => {
                setSelectedUserMetric('cache');
              }}
            />
            <MetricCard
              title="Active Alerts"
              value={formatNumber(alertStatus?.status?.active_alerts || 0)}
              icon={<AlertCircle className="w-5 h-5" />}
              isLoading={loadingAlerts}
              onClick={() => {
                setSelectedUserMetric('alerts');
              }}
            />
          </div>

          {/* Endpoints */}
          {myMetrics?.endpoints && myMetrics.endpoints.length > 0 ? (
            <div className="bg-surface rounded-2xl border border-border-default p-6 mb-8">
              <h2 className="text-lg font-semibold text-text-primary mb-4">Endpoint Usage</h2>
              <div className="space-y-2">
                {myMetrics.endpoints.map((endpoint: any, idx: number) => (
                  <div key={idx} className="bg-surface-hover rounded-lg p-4 border border-border-default">
                    <div className="flex justify-between items-start mb-2">
                      <div>
                        <p className="text-sm font-medium text-text-primary capitalize">{endpoint.endpoint}</p>
                        <p className="text-xs text-text-secondary mt-1">
                          {formatNumber(endpoint.total_calls)} calls
                        </p>
                      </div>
                      <div className="text-right">
                        <p className="text-sm font-bold text-text-primary">
                          Tokens: {formatNumber(endpoint.total_tokens)}
                        </p>
                        <p className="text-xs text-text-secondary">
                          Cost: {formatCurrency(endpoint.total_cost)}
                        </p>
                        {endpoint.avg_latency && (
                          <p className="text-xs text-text-secondary">
                            Avg Latency: {formatLatency(endpoint.avg_latency)}
                          </p>
                        )}
                      </div>
                    </div>
                    <div className="w-full bg-border-default rounded-full h-2.5">
                      <div
                        className="bg-accent-blue h-full transition-all"
                        style={{
                          width: `${Math.min((endpoint.total_tokens / (myMetrics.summary?.tokens?.total || 1)) * 100, 100)}%`,
                        }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ) : (
            <div className="bg-surface rounded-2xl border border-border-default p-6 mb-8">
              <p className="text-text-secondary text-center py-8">No endpoint usage data available</p>
            </div>
          )}

          {/* Trend Charts */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
            {/* Token Consumption Trend */}
            <div className="bg-surface rounded-2xl border border-border-default p-6">
              <h3 className="text-lg font-semibold text-text-primary mb-4">Token Consumption Trend</h3>
              <div className="h-64">
                {loadingTrends ? (
                  <div className="h-full flex items-center justify-center text-text-tertiary">
                    Loading...
                  </div>
                ) : trendData.tokens && trendData.tokens.length > 0 ? (
                  <Line
                    data={prepareChartData(trendData.tokens, 'tokens', 'Tokens', '#1A73E8')}
                    options={chartOptions}
                  />
                ) : (
                  <div className="h-full flex items-center justify-center text-text-tertiary">
                    No data available
                  </div>
                )}
              </div>
            </div>

            {/* Cost Trend */}
            <div className="bg-surface rounded-2xl border border-border-default p-6">
              <h3 className="text-lg font-semibold text-text-primary mb-4">Cost Trend</h3>
              <div className="h-64">
                {loadingTrends ? (
                  <div className="h-full flex items-center justify-center text-text-tertiary">
                    Loading...
                  </div>
                ) : trendData.cost && trendData.cost.length > 0 ? (
                  <Line
                    data={prepareChartData(trendData.cost, 'cost', 'Cost ($)', '#34A853')}
                    options={chartOptions}
                  />
                ) : (
                  <div className="h-full flex items-center justify-center text-text-tertiary">
                    No data available
                  </div>
                )}
              </div>
            </div>

            {/* Latency Trend */}
            <div className="bg-surface rounded-2xl border border-border-default p-6">
              <h3 className="text-lg font-semibold text-text-primary mb-4">Latency Trend</h3>
              <div className="h-64">
                {loadingTrends ? (
                  <div className="h-full flex items-center justify-center text-text-tertiary">
                    Loading...
                  </div>
                ) : trendData.latency && trendData.latency.length > 0 ? (
                  <Line
                    data={prepareChartData(trendData.latency, 'avg_latency_ms', 'Avg Latency (ms)', '#EA4335')}
                    options={chartOptions}
                  />
                ) : (
                  <div className="h-full flex items-center justify-center text-text-tertiary">
                    No data available
                  </div>
                )}
              </div>
            </div>

            {/* RAG Quality Trend */}
            <div className="bg-surface rounded-2xl border border-border-default p-6">
              <h3 className="text-lg font-semibold text-text-primary mb-4">RAG Quality Trend</h3>
              <div className="h-64">
                {loadingTrends ? (
                  <div className="h-full flex items-center justify-center text-text-tertiary">
                    Loading...
                  </div>
                ) : trendData.ragQuality && trendData.ragQuality.length > 0 ? (
                  <Line
                    data={prepareChartData(trendData.ragQuality, 'positive_rate', 'Positive Rate', '#FBBC04')}
                    options={{
                      ...chartOptions,
                      scales: {
                        ...chartOptions.scales,
                        y: {
                          ...chartOptions.scales.y,
                          min: 0,
                          max: 1,
                          ticks: {
                            ...chartOptions.scales.y.ticks,
                            callback: function(value: any) {
                              return `${(value * 100).toFixed(0)}%`;
                            },
                          },
                        },
                      },
                    }}
                  />
                ) : (
                  <div className="h-full flex items-center justify-center text-text-tertiary">
                    No data available
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>

        {/* User Metric Detail Modal */}
        {selectedUserMetric && myMetrics && (
          <UserMetricDetailModal
            metricType={selectedUserMetric}
            userMetrics={myMetrics}
            onClose={() => setSelectedUserMetric(null)}
          />
        )}
      </div>
    );
  }

  return (
    <div className="h-full flex items-center justify-center">
      <p className="text-text-secondary">Access denied. Admin privileges required.</p>
    </div>
  );
}

// Admin Metric Detail Modal Component
interface AdminMetricDetailModalProps {
  metricType: string;
  aggregateMetrics: any;
  details: any;
  loading: boolean;
  onClose: () => void;
}

function AdminMetricDetailModal({
  metricType,
  aggregateMetrics,
  details,
  loading,
  onClose,
}: AdminMetricDetailModalProps) {
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
    const metrics = aggregateMetrics?.metrics || {};
    const usage = aggregateMetrics?.usage || {};
    const ragQuality = details?.ragQuality || null;

    switch (metricType) {
      case 'tokens':
        return {
          title: 'Token Consumption Details',
          content: (
            <div className="space-y-6">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="bg-surface-hover rounded-xl p-4 border border-border-default">
                  <h4 className="text-xs font-medium text-text-secondary mb-1">Total Tokens</h4>
                  <p className="text-2xl font-bold text-text-primary">
                    {formatNumber(metrics.tokens?.total || usage.total_tokens)}
                  </p>
                </div>
                <div className="bg-surface-hover rounded-xl p-4 border border-border-default">
                  <h4 className="text-xs font-medium text-text-secondary mb-1">Input Tokens</h4>
                  <p className="text-2xl font-bold text-text-primary">
                    {formatNumber(metrics.tokens?.input || usage.input_tokens)}
                  </p>
                </div>
                <div className="bg-surface-hover rounded-xl p-4 border border-border-default">
                  <h4 className="text-xs font-medium text-text-secondary mb-1">Output Tokens</h4>
                  <p className="text-2xl font-bold text-text-primary">
                    {formatNumber(metrics.tokens?.output || usage.output_tokens)}
                  </p>
                </div>
                <div className="bg-surface-hover rounded-xl p-4 border border-border-default">
                  <h4 className="text-xs font-medium text-text-secondary mb-1">Total Calls</h4>
                  <p className="text-2xl font-bold text-text-primary">
                    {formatNumber(metrics.llm_calls?.total || usage.total_calls)}
                  </p>
                </div>
              </div>

              <div>
                <h4 className="text-sm font-semibold text-text-primary mb-3">Token Breakdown</h4>
                <div className="space-y-2">
                  <div className="flex justify-between items-center p-3 bg-surface-hover rounded-lg border border-border-default">
                    <span className="text-sm text-text-secondary">Input Tokens</span>
                    <span className="text-sm font-bold text-text-primary">
                      {formatNumber(metrics.tokens?.input || usage.input_tokens)} (
                      {metrics.tokens?.total
                        ? ((metrics.tokens.input / metrics.tokens.total) * 100).toFixed(1)
                        : usage.total_tokens
                        ? ((usage.input_tokens / usage.total_tokens) * 100).toFixed(1)
                        : '0'}
                      %)
                    </span>
                  </div>
                  <div className="flex justify-between items-center p-3 bg-surface-hover rounded-lg border border-border-default">
                    <span className="text-sm text-text-secondary">Output Tokens</span>
                    <span className="text-sm font-bold text-text-primary">
                      {formatNumber(metrics.tokens?.output || usage.output_tokens)} (
                      {metrics.tokens?.total
                        ? ((metrics.tokens.output / metrics.tokens.total) * 100).toFixed(1)
                        : usage.total_tokens
                        ? ((usage.output_tokens / usage.total_tokens) * 100).toFixed(1)
                        : '0'}
                      %)
                    </span>
                  </div>
                  <div className="flex justify-between items-center p-3 bg-surface-hover rounded-lg border border-border-default">
                    <span className="text-sm text-text-secondary">Avg Tokens per Call</span>
                    <span className="text-sm font-bold text-text-primary">
                      {formatNumber(
                        metrics.llm_calls?.avg_tokens_per_call || usage.avg_tokens_per_call
                      )}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          ),
        };
      case 'cost':
        return {
          title: 'Cost Details',
          content: (
            <div className="space-y-6">
              <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                <div className="bg-surface-hover rounded-xl p-4 border border-border-default">
                  <h4 className="text-xs font-medium text-text-secondary mb-1">Total Cost</h4>
                  <p className="text-2xl font-bold text-text-primary">
                    {formatCurrency(metrics.costs?.total || usage.total_cost)}
                  </p>
                </div>
                <div className="bg-surface-hover rounded-xl p-4 border border-border-default">
                  <h4 className="text-xs font-medium text-text-secondary mb-1">Avg Cost per Call</h4>
                  <p className="text-2xl font-bold text-text-primary">
                    {formatCurrency(metrics.costs?.avg_per_call || usage.avg_cost_per_call)}
                  </p>
                </div>
                <div className="bg-surface-hover rounded-xl p-4 border border-border-default">
                  <h4 className="text-xs font-medium text-text-secondary mb-1">Total Calls</h4>
                  <p className="text-2xl font-bold text-text-primary">
                    {formatNumber(metrics.llm_calls?.total || usage.total_calls)}
                  </p>
                </div>
              </div>
            </div>
          ),
        };
      case 'latency':
        return {
          title: 'Latency Details',
          content: (
            <div className="space-y-6">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="bg-surface-hover rounded-xl p-4 border border-border-default">
                  <h4 className="text-xs font-medium text-text-secondary mb-1">Avg Latency</h4>
                  <p className="text-2xl font-bold text-text-primary">
                    {formatLatency(metrics.latency?.average)}
                  </p>
                </div>
                <div className="bg-surface-hover rounded-xl p-4 border border-border-default">
                  <h4 className="text-xs font-medium text-text-secondary mb-1">P50 Latency</h4>
                  <p className="text-2xl font-bold text-text-primary">
                    {formatLatency(metrics.latency?.p50)}
                  </p>
                </div>
                <div className="bg-surface-hover rounded-xl p-4 border border-default">
                  <h4 className="text-xs font-medium text-text-secondary mb-1">P95 Latency</h4>
                  <p className="text-2xl font-bold text-text-primary">
                    {formatLatency(metrics.latency?.p95)}
                  </p>
                </div>
                <div className="bg-surface-hover rounded-xl p-4 border border-border-default">
                  <h4 className="text-xs font-medium text-text-secondary mb-1">P99 Latency</h4>
                  <p className="text-2xl font-bold text-text-primary">
                    {formatLatency(metrics.latency?.p99)}
                  </p>
                </div>
              </div>
            </div>
          ),
        };
      case 'cache':
        return {
          title: 'Cache Efficiency Details',
          content: (
            <div className="space-y-6">
              <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                <div className="bg-surface-hover rounded-xl p-4 border border-border-default">
                  <h4 className="text-xs font-medium text-text-secondary mb-1">Cache Hit Rate</h4>
                  <p className="text-2xl font-bold text-text-primary">
                    {formatPercentage(
                      metrics.cache?.hit_rate != null ? metrics.cache.hit_rate * 100 : undefined
                    )}
                  </p>
                </div>
                <div className="bg-surface-hover rounded-xl p-4 border border-border-default">
                  <h4 className="text-xs font-medium text-text-secondary mb-1">Cache Hits</h4>
                  <p className="text-2xl font-bold text-text-primary">
                    {formatNumber(metrics.cache?.hits)}
                  </p>
                </div>
                <div className="bg-surface-hover rounded-xl p-4 border border-border-default">
                  <h4 className="text-xs font-medium text-text-secondary mb-1">Cache Misses</h4>
                  <p className="text-2xl font-bold text-text-primary">
                    {formatNumber(metrics.cache?.misses)}
                  </p>
                </div>
              </div>
            </div>
          ),
        };
      case 'rag-quality':
        return {
          title: 'RAG Quality Details',
          content: (
            <div className="space-y-6">
              <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                <div className="bg-surface-hover rounded-xl p-4 border border-border-default">
                  <h4 className="text-xs font-medium text-text-secondary mb-1">Quality Score</h4>
                  <p className="text-2xl font-bold text-text-primary">
                    {ragQuality?.summary?.positive_rate ? `${(ragQuality.summary.positive_rate * 10).toFixed(1)}/10` : '—'}
                  </p>
                </div>
                <div className="bg-surface-hover rounded-xl p-4 border border-border-default">
                  <h4 className="text-xs font-medium text-text-secondary mb-1">Total Feedback</h4>
                  <p className="text-2xl font-bold text-text-primary">
                    {formatNumber(ragQuality?.summary?.total_feedback)}
                  </p>
                </div>
                <div className="bg-surface-hover rounded-xl p-4 border border-border-default">
                  <h4 className="text-xs font-medium text-text-secondary mb-1">Positive Rate</h4>
                  <p className="text-2xl font-bold text-text-primary">
                    {formatPercentage(ragQuality?.summary?.positive_rate ? ragQuality.summary.positive_rate * 100 : undefined)}
                  </p>
                </div>
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
        className="bg-modal rounded-2xl border border-border-default shadow-xl max-w-3xl w-full mx-4 max-h-[85vh] overflow-y-auto"
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
        <div className="p-6">
          {loading ? (
            <div className="text-center py-8 text-text-secondary">Loading details...</div>
          ) : (
            content
          )}
        </div>
      </div>
    </div>
  );
}

// User Metric Detail Modal Component
interface UserMetricDetailModalProps {
  metricType: string;
  userMetrics: any;
  onClose: () => void;
}

function UserMetricDetailModal({
  metricType,
  userMetrics,
  onClose,
}: UserMetricDetailModalProps) {
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
    const metrics = userMetrics?.metrics || userMetrics?.summary || {};
    const usage = userMetrics?.usage || {};

    switch (metricType) {
      case 'tokens':
        return {
          title: 'Token Consumption Details',
          content: (
            <div className="space-y-6">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="bg-surface-hover rounded-xl p-4 border border-border-default">
                  <h4 className="text-xs font-medium text-text-secondary mb-1">Total Tokens</h4>
                  <p className="text-2xl font-bold text-text-primary">
                    {formatNumber(metrics.tokens?.total || usage.total_tokens)}
                  </p>
                </div>
                <div className="bg-surface-hover rounded-xl p-4 border border-border-default">
                  <h4 className="text-xs font-medium text-text-secondary mb-1">Input Tokens</h4>
                  <p className="text-2xl font-bold text-text-primary">
                    {formatNumber(metrics.tokens?.input || usage.input_tokens)}
                  </p>
                </div>
                <div className="bg-surface-hover rounded-xl p-4 border border-border-default">
                  <h4 className="text-xs font-medium text-text-secondary mb-1">Output Tokens</h4>
                  <p className="text-2xl font-bold text-text-primary">
                    {formatNumber(metrics.tokens?.output || usage.output_tokens)}
                  </p>
                </div>
                <div className="bg-surface-hover rounded-xl p-4 border border-border-default">
                  <h4 className="text-xs font-medium text-text-secondary mb-1">Total Calls</h4>
                  <p className="text-2xl font-bold text-text-primary">
                    {formatNumber(metrics.llm_calls?.total || usage.total_calls)}
                  </p>
                </div>
              </div>

              <div>
                <h4 className="text-sm font-semibold text-text-primary mb-3">Token Breakdown</h4>
                <div className="space-y-2">
                  <div className="flex justify-between items-center p-3 bg-surface-hover rounded-lg border border-border-default">
                    <span className="text-sm text-text-secondary">Input Tokens</span>
                    <span className="text-sm font-bold text-text-primary">
                      {formatNumber(metrics.tokens?.input || usage.input_tokens)} (
                      {metrics.tokens?.total
                        ? ((metrics.tokens.input / metrics.tokens.total) * 100).toFixed(1)
                        : usage.total_tokens
                        ? ((usage.input_tokens / usage.total_tokens) * 100).toFixed(1)
                        : '0'}
                      %)
                    </span>
                  </div>
                  <div className="flex justify-between items-center p-3 bg-surface-hover rounded-lg border border-border-default">
                    <span className="text-sm text-text-secondary">Output Tokens</span>
                    <span className="text-sm font-bold text-text-primary">
                      {formatNumber(metrics.tokens?.output || usage.output_tokens)} (
                      {metrics.tokens?.total
                        ? ((metrics.tokens.output / metrics.tokens.total) * 100).toFixed(1)
                        : usage.total_tokens
                        ? ((usage.output_tokens / usage.total_tokens) * 100).toFixed(1)
                        : '0'}
                      %)
                    </span>
                  </div>
                </div>
              </div>

              {userMetrics.endpoints && userMetrics.endpoints.length > 0 && (
                <div>
                  <h4 className="text-sm font-semibold text-text-primary mb-3">Usage by Endpoint</h4>
                  <div className="space-y-2">
                    {userMetrics.endpoints.map((endpoint: any, idx: number) => (
                      <div
                        key={idx}
                        className="bg-surface-hover rounded-lg p-4 border border-border-default"
                      >
                        <div className="flex justify-between items-start mb-2">
                          <div>
                            <p className="text-sm font-medium text-text-primary capitalize">
                              {endpoint.endpoint?.replace(/_/g, ' ')}
                            </p>
                            <p className="text-xs text-text-secondary mt-1">
                              {formatNumber(endpoint.total_calls)} calls
                            </p>
                          </div>
                          <div className="text-right">
                            <p className="text-sm font-bold text-text-primary">
                              {formatNumber(endpoint.total_tokens)} tokens
                            </p>
                            <p className="text-xs text-text-secondary">
                              {formatCurrency(endpoint.total_cost)} cost
                            </p>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ),
        };
      case 'cost':
        return {
          title: 'Cost Details',
          content: (
            <div className="space-y-6">
              <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                <div className="bg-surface-hover rounded-xl p-4 border border-border-default">
                  <h4 className="text-xs font-medium text-text-secondary mb-1">Total Cost</h4>
                  <p className="text-2xl font-bold text-text-primary">
                    {formatCurrency(metrics.costs?.total || usage.total_cost)}
                  </p>
                </div>
                <div className="bg-surface-hover rounded-xl p-4 border border-border-default">
                  <h4 className="text-xs font-medium text-text-secondary mb-1">Avg Cost per Call</h4>
                  <p className="text-2xl font-bold text-text-primary">
                    {formatCurrency(metrics.costs?.avg_per_call || usage.avg_cost_per_call)}
                  </p>
                </div>
                <div className="bg-surface-hover rounded-xl p-4 border border-border-default">
                  <h4 className="text-xs font-medium text-text-secondary mb-1">Total Calls</h4>
                  <p className="text-2xl font-bold text-text-primary">
                    {formatNumber(metrics.llm_calls?.total || usage.total_calls)}
                  </p>
                </div>
              </div>

              {userMetrics.endpoints && userMetrics.endpoints.length > 0 && (
                <div>
                  <h4 className="text-sm font-semibold text-text-primary mb-3">Cost by Endpoint</h4>
                  <div className="space-y-2">
                    {userMetrics.endpoints
                      .sort((a: any, b: any) => (b.total_cost || 0) - (a.total_cost || 0))
                      .map((endpoint: any, idx: number) => (
                        <div
                          key={idx}
                          className="flex justify-between items-center p-3 bg-surface-hover rounded-lg border border-border-default"
                        >
                          <span className="text-sm text-text-primary capitalize">
                            {endpoint.endpoint?.replace(/_/g, ' ')}
                          </span>
                          <span className="text-sm font-bold text-text-primary">
                            {formatCurrency(endpoint.total_cost || 0)}
                          </span>
                        </div>
                      ))}
                  </div>
                </div>
              )}
            </div>
          ),
        };
      case 'latency':
        return {
          title: 'Latency Details',
          content: (
            <div className="space-y-6">
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                <div className="bg-surface-hover rounded-xl p-4 border border-border-default">
                  <h4 className="text-xs font-medium text-text-secondary mb-1">Avg Latency</h4>
                  <p className="text-2xl font-bold text-text-primary">
                    {formatLatency(metrics.latency?.average)}
                  </p>
                </div>
                <div className="bg-surface-hover rounded-xl p-4 border border-border-default">
                  <h4 className="text-xs font-medium text-text-secondary mb-1">P50 Latency</h4>
                  <p className="text-2xl font-bold text-text-primary">
                    {formatLatency(metrics.latency?.p50)}
                  </p>
                </div>
                <div className="bg-surface-hover rounded-xl p-4 border border-border-default">
                  <h4 className="text-xs font-medium text-text-secondary mb-1">P95 Latency</h4>
                  <p className="text-2xl font-bold text-text-primary">
                    {formatLatency(metrics.latency?.p95)}
                  </p>
                </div>
                <div className="bg-surface-hover rounded-xl p-4 border border-border-default">
                  <h4 className="text-xs font-medium text-text-secondary mb-1">P99 Latency</h4>
                  <p className="text-2xl font-bold text-text-primary">
                    {formatLatency(metrics.latency?.p99)}
                  </p>
                </div>
              </div>
            </div>
          ),
        };
      case 'cache':
        return {
          title: 'Cache Efficiency Details',
          content: (
            <div className="space-y-6">
              <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
                <div className="bg-surface-hover rounded-xl p-4 border border-border-default">
                  <h4 className="text-xs font-medium text-text-secondary mb-1">Cache Hit Rate</h4>
                  <p className="text-2xl font-bold text-text-primary">
                    {formatPercentage(
                      metrics.cache?.hit_rate != null ? metrics.cache.hit_rate * 100 : undefined
                    )}
                  </p>
                </div>
                <div className="bg-surface-hover rounded-xl p-4 border border-border-default">
                  <h4 className="text-xs font-medium text-text-secondary mb-1">Cache Hits</h4>
                  <p className="text-2xl font-bold text-text-primary">
                    {formatNumber(metrics.cache?.hits)}
                  </p>
                </div>
                <div className="bg-surface-hover rounded-xl p-4 border border-border-default">
                  <h4 className="text-xs font-medium text-text-secondary mb-1">Cache Misses</h4>
                  <p className="text-2xl font-bold text-text-primary">
                    {formatNumber(metrics.cache?.misses)}
                  </p>
                </div>
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
        className="bg-modal rounded-2xl border border-border-default shadow-xl max-w-3xl w-full mx-4 max-h-[85vh] overflow-y-auto"
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
