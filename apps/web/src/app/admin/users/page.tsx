/**
 * Users Analytics Page
 * 
 * Admin page for viewing user analytics with real backend data.
 * Shows token consumption, costs, and detailed user metrics.
 */

'use client';

import { useState, useMemo, useEffect, useCallback } from 'react';
import { Search, ChevronUp, ChevronDown, ChevronLeft, ChevronRight, X, User, Calendar, Database, Zap, FileText, AlertTriangle, Clock, DollarSign, TrendingUp, Loader2, Filter, XCircle } from 'lucide-react';
import { Input } from '@/components/ui/Input';
import { Button } from '@/components/ui/Button';
import { useAdminPortalApi } from '@/hooks/useAdminPortalApi';
import { apiClient } from '@/lib/api-client';
import { AdminTableSkeleton, AdminDetailSkeleton } from '@/components/skeleton';

// User data type
interface UserData {
  id: string;
  clerk_user_id: string;
  email: string;
  first_name?: string;
  last_name?: string;
  username?: string;
  role: string;
  created_at?: string;
  last_sign_in_at?: string;
}

// User analytics aggregated from backend
interface UserAnalytics {
  userId: string;
  email: string;
  name: string;
  tokensUsed: number;
  inputTokens: number;
  outputTokens: number;
  cost: number;
  queries: number;
  avgLatency: number;
  cacheHits: number;
  cacheMisses: number;
  cacheHitRate: number;
  lastActive: string;
  alerts: number;
}

// Detailed user metrics
interface UserDetailMetrics {
  summary: any;
  usage: any;
  endpoints: any[];
  tokenConsumption?: {
    input_tokens: number;
    output_tokens: number;
    total_tokens: number;
  };
  costs?: {
    total_cost: number;
    breakdown: any[];
  };
  latency?: {
    avg_latency_ms: number;
    p95_latency_ms: number;
    p99_latency_ms: number;
  };
  cache?: {
    hits: number;
    misses: number;
    hit_rate: number;
  };
  alerts?: any[];
  sessions?: Array<{
    session_id: string;
    login_time: string;
    logout_time?: string;
    duration?: string;
    token_consumption?: number;
  }>;
}

type SortField = keyof UserAnalytics | null;
type SortDirection = 'asc' | 'desc' | null;

interface UserDetailPanelProps {
  userId: string;
  userName: string;
  userEmail: string;
  onClose: () => void;
}

function UserDetailPanel({ userId, userName, userEmail, onClose }: UserDetailPanelProps) {
  const { ready } = useAdminPortalApi();
  const [loading, setLoading] = useState(true);
  const [metrics, setMetrics] = useState<UserDetailMetrics | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [showSessionsModal, setShowSessionsModal] = useState(false);
  const [sessionsDateRange, setSessionsDateRange] = useState<{ start: string; end: string }>({
    start: new Date(Date.now() - 30 * 24 * 60 * 60 * 1000).toISOString().split('T')[0], // 30 days ago
    end: new Date().toISOString().split('T')[0], // Today
  });
  const [filteredSessions, setFilteredSessions] = useState<any[]>([]);
  const [loadingSessions, setLoadingSessions] = useState(false);

  useEffect(() => {
    const fetchUserDetails = async () => {
      if (!ready) return;
      
      setLoading(true);
      setError(null);
      
      try {
        
        // Fetch user metrics and sessions
        const [userMetrics, tokenData, costData, latencyData, cacheData, alertsData, sessionsData] = await Promise.all([
          apiClient.getUserMetrics(userId, 30).catch(() => null),
          apiClient.getTokenConsumption(30, 'user').catch(() => null),
          apiClient.getCostTracking(30, true).catch(() => null),
          apiClient.getLatencyDashboard(30).catch(() => null),
          apiClient.getCacheEfficiency(30).catch(() => null),
          apiClient.getAlertsStatus().catch(() => null),
          apiClient.getUserSessions(userId, 30).catch(() => null),
        ]);

        // Find user-specific data from token consumption
        const userTokenData = tokenData?.breakdown?.find((item: any) => item.key === userId);
        
        // Find user-specific cost data
        const userCostData = costData?.user_breakdown?.find((item: any) => item.user_id === userId);
        
        // Filter alerts for this user
        const userAlerts = alertsData?.alerts?.filter((alert: any) => alert.user_id === userId) || [];

        // Get sessions from backend
        const sessions = sessionsData?.sessions || [];

        setMetrics({
          summary: userMetrics?.summary || {},
          usage: userMetrics?.usage || {},
          endpoints: userMetrics?.endpoints || [],
          tokenConsumption: userTokenData ? {
            input_tokens: userTokenData.prompt_tokens || 0,
            output_tokens: userTokenData.completion_tokens || 0,
            total_tokens: userTokenData.total_tokens || 0,
          } : undefined,
          costs: userCostData ? {
            total_cost: userCostData.cost || 0,
            breakdown: [],
          } : undefined,
          latency: latencyData?.summary ? {
            avg_latency_ms: latencyData.summary.avg_latency_ms || 0,
            p95_latency_ms: latencyData.summary.p95_latency_ms || 0,
            p99_latency_ms: latencyData.summary.p99_latency_ms || 0,
          } : undefined,
          cache: cacheData?.summary ? {
            hits: cacheData.summary.hits || 0,
            misses: cacheData.summary.misses || 0,
            hit_rate: cacheData.summary.hit_rate || 0,
          } : undefined,
          alerts: userAlerts,
          sessions: sessions,
        });
      } catch (err: any) {
        console.error('[Users] Failed to fetch user details:', err);
        setError(err?.message || 'Failed to load user details');
      } finally {
        setLoading(false);
      }
    };

    if (userId) {
      fetchUserDetails();
    }
  }, [userId, ready]);

  const formatDate = (dateString: string | undefined) => {
    if (!dateString) return 'N/A';
    const date = new Date(dateString);
    return date.toLocaleString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  };

  const formatNumber = (num: number | undefined) => {
    if (num === undefined || num === null) return '0';
    return num.toLocaleString('en-US', { maximumFractionDigits: 2 });
  };

  const formatCurrency = (amount: number | undefined) => {
    if (amount === undefined || amount === null) return '$0.00';
    return `$${amount.toFixed(4)}`;
  };

  const formatDuration = (ms: number | undefined) => {
    if (ms === undefined || ms === null) return 'N/A';
    if (ms < 1000) return `${ms.toFixed(0)}ms`;
    if (ms < 60000) return `${(ms / 1000).toFixed(2)}s`;
    return `${(ms / 60000).toFixed(2)}min`;
  };

  if (loading) {
    return (
      <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-end">
        <div className="h-full w-full max-w-4xl bg-surface border-l border-border-default shadow-2xl overflow-y-auto">
          <AdminDetailSkeleton />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-end">
        <div className="h-full w-full max-w-4xl bg-surface border-l border-border-default shadow-2xl overflow-y-auto">
          <div className="p-6">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-2xl font-semibold text-text-primary">User Details</h2>
              <button
                onClick={onClose}
                className="p-2 rounded-lg hover:bg-surface-hover text-text-secondary hover:text-text-primary transition-colors"
                aria-label="Close panel"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-4">
              <p className="text-red-500">{error}</p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-end">
      <div className="h-full w-full max-w-4xl bg-surface border-l border-border-default shadow-2xl overflow-y-auto">
        <div className="sticky top-0 bg-surface border-b border-border-default p-6 flex items-center justify-between z-10">
          <div>
            <h2 className="text-2xl font-semibold text-text-primary">{userName || 'User Details'}</h2>
            <p className="text-sm text-text-secondary mt-1">{userEmail}</p>
            <p className="text-xs text-text-tertiary mt-1">ID: {userId}</p>
          </div>
          <button
            onClick={onClose}
            className="p-2 rounded-lg hover:bg-surface-hover text-text-secondary hover:text-text-primary transition-colors"
            aria-label="Close panel"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-6 space-y-6">
          {/* Sessions Table - Moved to Top */}
          {metrics?.sessions && metrics.sessions.length > 0 ? (
            <div>
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-text-primary flex items-center gap-2">
                  <Calendar className="w-5 h-5" />
                  Recent Sessions ({metrics.sessions.length} total)
                </h3>
                {metrics.sessions.length > 5 && (
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={async () => {
                      setShowSessionsModal(true);
                      // Initialize with current sessions
                      setFilteredSessions(metrics.sessions || []);
                      // Also fetch all sessions for the default date range
                      try {
                        if (!ready) return;
                        const sessionsData = await apiClient.getUserSessions(userId, 30);
                        setFilteredSessions(sessionsData?.sessions || []);
                      } catch (err: any) {
                        console.error('[Sessions] Failed to fetch sessions:', err);
                        // Keep the current sessions if fetch fails
                      }
                    }}
                  >
                    See More
                  </Button>
                )}
              </div>
              <div className="bg-surface-hover rounded-xl border border-border-default overflow-hidden">
                <table className="w-full">
                  <thead className="bg-surface border-b border-border-default">
                    <tr>
                      <th className="px-4 py-3 text-left text-sm font-semibold text-text-primary">Session ID</th>
                      <th className="px-4 py-3 text-left text-sm font-semibold text-text-primary">Login Time</th>
                      <th className="px-4 py-3 text-left text-sm font-semibold text-text-primary">Logout Time</th>
                      <th className="px-4 py-3 text-left text-sm font-semibold text-text-primary">Duration</th>
                      <th className="px-4 py-3 text-right text-sm font-semibold text-text-primary">Token Consumption</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border-default">
                    {metrics.sessions.slice(0, 5).map((session: any, idx: number) => (
                      <tr key={idx}>
                        <td className="px-4 py-3 text-text-primary font-mono text-sm">{session.session_id}</td>
                        <td className="px-4 py-3 text-text-primary">{formatDate(session.login_time)}</td>
                        <td className="px-4 py-3 text-text-primary">{formatDate(session.logout_time)}</td>
                        <td className="px-4 py-3 text-text-secondary">{session.duration || 'N/A'}</td>
                        <td className="px-4 py-3 text-right text-text-primary font-semibold">
                          {formatNumber(session.token_consumption || 0)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          ) : (
            <div>
              <h3 className="text-lg font-semibold text-text-primary mb-4 flex items-center gap-2">
                <Calendar className="w-5 h-5" />
                Sessions
              </h3>
              <div className="bg-surface-hover rounded-xl border border-border-default p-6 text-center">
                <p className="text-text-secondary">No session data available</p>
              </div>
            </div>
          )}

          {/* Token Consumption Table */}
          <div>
            <h3 className="text-lg font-semibold text-text-primary mb-4 flex items-center gap-2">
              <Zap className="w-5 h-5" />
              Token Consumption
            </h3>
            <div className="bg-surface-hover rounded-xl border border-border-default overflow-hidden">
              <table className="w-full">
                <thead className="bg-surface border-b border-border-default">
                  <tr>
                    <th className="px-4 py-3 text-left text-sm font-semibold text-text-primary">Type</th>
                    <th className="px-4 py-3 text-left text-sm font-semibold text-text-primary">Tokens</th>
                    <th className="px-4 py-3 text-left text-sm font-semibold text-text-primary">Percentage</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border-default">
                  <tr>
                    <td className="px-4 py-3 text-text-primary font-medium">Input Tokens</td>
                    <td className="px-4 py-3 text-text-primary">{formatNumber(metrics?.tokenConsumption?.input_tokens)}</td>
                    <td className="px-4 py-3 text-text-secondary">
                      {metrics?.tokenConsumption?.total_tokens 
                        ? `${((metrics.tokenConsumption.input_tokens / metrics.tokenConsumption.total_tokens) * 100).toFixed(1)}%`
                        : '0%'}
                    </td>
                  </tr>
                  <tr>
                    <td className="px-4 py-3 text-text-primary font-medium">Output Tokens</td>
                    <td className="px-4 py-3 text-text-primary">{formatNumber(metrics?.tokenConsumption?.output_tokens)}</td>
                    <td className="px-4 py-3 text-text-secondary">
                      {metrics?.tokenConsumption?.total_tokens 
                        ? `${((metrics.tokenConsumption.output_tokens / metrics.tokenConsumption.total_tokens) * 100).toFixed(1)}%`
                        : '0%'}
                    </td>
                  </tr>
                  <tr className="bg-surface-hover">
                    <td className="px-4 py-3 text-text-primary font-semibold">Total Tokens</td>
                    <td className="px-4 py-3 text-text-primary font-semibold">{formatNumber(metrics?.tokenConsumption?.total_tokens)}</td>
                    <td className="px-4 py-3 text-text-primary font-semibold">100%</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          {/* Costs Table */}
          <div>
            <h3 className="text-lg font-semibold text-text-primary mb-4 flex items-center gap-2">
              <DollarSign className="w-5 h-5" />
              Costs
            </h3>
            <div className="bg-surface-hover rounded-xl border border-border-default overflow-hidden">
              <table className="w-full">
                <thead className="bg-surface border-b border-border-default">
                  <tr>
                    <th className="px-4 py-3 text-left text-sm font-semibold text-text-primary">Metric</th>
                    <th className="px-4 py-3 text-left text-sm font-semibold text-text-primary">Value</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border-default">
                  <tr>
                    <td className="px-4 py-3 text-text-primary font-medium">Total Cost</td>
                    <td className="px-4 py-3 text-text-primary">{formatCurrency(metrics?.costs?.total_cost)}</td>
                  </tr>
                  {metrics?.tokenConsumption?.total_tokens && metrics?.tokenConsumption.total_tokens > 0 && metrics?.costs?.total_cost !== undefined && (
                    <tr>
                      <td className="px-4 py-3 text-text-primary font-medium">Cost per Token</td>
                      <td className="px-4 py-3 text-text-primary">
                        {formatCurrency(metrics.costs.total_cost / metrics.tokenConsumption.total_tokens)}
                      </td>
                    </tr>
                  )}
                  {metrics?.summary?.llm_calls && metrics.summary.llm_calls > 0 && metrics?.costs?.total_cost !== undefined && (
                    <tr>
                      <td className="px-4 py-3 text-text-primary font-medium">Cost per Query</td>
                      <td className="px-4 py-3 text-text-primary">
                        {formatCurrency(metrics.costs.total_cost / metrics.summary.llm_calls)}
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>

          {/* Latency Table */}
          <div>
            <h3 className="text-lg font-semibold text-text-primary mb-4 flex items-center gap-2">
              <Clock className="w-5 h-5" />
              Latency Metrics
            </h3>
            <div className="bg-surface-hover rounded-xl border border-border-default overflow-hidden">
              <table className="w-full">
                <thead className="bg-surface border-b border-border-default">
                  <tr>
                    <th className="px-4 py-3 text-left text-sm font-semibold text-text-primary">Metric</th>
                    <th className="px-4 py-3 text-left text-sm font-semibold text-text-primary">Value</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border-default">
                  <tr>
                    <td className="px-4 py-3 text-text-primary font-medium">Average Latency</td>
                    <td className="px-4 py-3 text-text-primary">{formatDuration(metrics?.latency?.avg_latency_ms)}</td>
                  </tr>
                  <tr>
                    <td className="px-4 py-3 text-text-primary font-medium">P95 Latency</td>
                    <td className="px-4 py-3 text-text-primary">{formatDuration(metrics?.latency?.p95_latency_ms)}</td>
                  </tr>
                  <tr>
                    <td className="px-4 py-3 text-text-primary font-medium">P99 Latency</td>
                    <td className="px-4 py-3 text-text-primary">{formatDuration(metrics?.latency?.p99_latency_ms)}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          {/* Queries Table */}
          <div>
            <h3 className="text-lg font-semibold text-text-primary mb-4 flex items-center gap-2">
              <Search className="w-5 h-5" />
              Queries
            </h3>
            <div className="bg-surface-hover rounded-xl border border-border-default overflow-hidden">
              <table className="w-full">
                <thead className="bg-surface border-b border-border-default">
                  <tr>
                    <th className="px-4 py-3 text-left text-sm font-semibold text-text-primary">Metric</th>
                    <th className="px-4 py-3 text-left text-sm font-semibold text-text-primary">Value</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border-default">
                  <tr>
                    <td className="px-4 py-3 text-text-primary font-medium">Total Queries</td>
                    <td className="px-4 py-3 text-text-primary">{formatNumber(metrics?.summary?.llm_calls?.total || metrics?.usage?.total_calls || 0)}</td>
                  </tr>
                  <tr>
                    <td className="px-4 py-3 text-text-primary font-medium">Successful Queries</td>
                    <td className="px-4 py-3 text-text-primary">{formatNumber(metrics?.summary?.llm_calls?.successful || metrics?.usage?.successful_calls || 0)}</td>
                  </tr>
                  <tr>
                    <td className="px-4 py-3 text-text-primary font-medium">Failed Queries</td>
                    <td className="px-4 py-3 text-text-primary">{formatNumber(metrics?.summary?.llm_calls?.failed || metrics?.usage?.failed_calls || 0)}</td>
                  </tr>
                  <tr>
                    <td className="px-4 py-3 text-text-primary font-medium">Success Rate</td>
                    <td className="px-4 py-3 text-text-primary">
                      {(() => {
                        const total = metrics?.summary?.llm_calls?.total || metrics?.usage?.total_calls || 0;
                        const successful = metrics?.summary?.llm_calls?.successful || metrics?.usage?.successful_calls || 0;
                        return total > 0 ? `${((successful / total) * 100).toFixed(1)}%` : '0%';
                      })()}
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          {/* Cache Hit Table */}
          <div>
            <h3 className="text-lg font-semibold text-text-primary mb-4 flex items-center gap-2">
              <TrendingUp className="w-5 h-5" />
              Cache Performance
            </h3>
            <div className="bg-surface-hover rounded-xl border border-border-default overflow-hidden">
              <table className="w-full">
                <thead className="bg-surface border-b border-border-default">
                  <tr>
                    <th className="px-4 py-3 text-left text-sm font-semibold text-text-primary">Metric</th>
                    <th className="px-4 py-3 text-left text-sm font-semibold text-text-primary">Value</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border-default">
                  <tr>
                    <td className="px-4 py-3 text-text-primary font-medium">Cache Hits</td>
                    <td className="px-4 py-3 text-text-primary">{formatNumber(metrics?.cache?.hits)}</td>
                  </tr>
                  <tr>
                    <td className="px-4 py-3 text-text-primary font-medium">Cache Misses</td>
                    <td className="px-4 py-3 text-text-primary">{formatNumber(metrics?.cache?.misses)}</td>
                  </tr>
                  <tr>
                    <td className="px-4 py-3 text-text-primary font-medium">Cache Hit Rate</td>
                    <td className="px-4 py-3 text-text-primary">
                      {metrics?.cache?.hit_rate !== undefined 
                        ? `${(metrics.cache.hit_rate * 100).toFixed(2)}%`
                        : '0%'}
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>

          {/* Alerts Table */}
          {metrics?.alerts && metrics.alerts.length > 0 && (
            <div>
              <h3 className="text-lg font-semibold text-text-primary mb-4 flex items-center gap-2">
                <AlertTriangle className="w-5 h-5" />
                Alerts ({metrics.alerts.length})
              </h3>
              <div className="bg-surface-hover rounded-xl border border-border-default overflow-hidden">
                <table className="w-full">
                  <thead className="bg-surface border-b border-border-default">
                    <tr>
                      <th className="px-4 py-3 text-left text-sm font-semibold text-text-primary">Type</th>
                      <th className="px-4 py-3 text-left text-sm font-semibold text-text-primary">Severity</th>
                      <th className="px-4 py-3 text-left text-sm font-semibold text-text-primary">Message</th>
                      <th className="px-4 py-3 text-left text-sm font-semibold text-text-primary">Time</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border-default">
                    {metrics.alerts.map((alert: any, idx: number) => (
                      <tr key={idx}>
                        <td className="px-4 py-3 text-text-primary">{alert.alert_type || 'N/A'}</td>
                        <td className="px-4 py-3">
                          <span className={`px-2 py-1 rounded text-xs font-medium ${
                            alert.severity === 'high' ? 'bg-red-500/20 text-red-500' :
                            alert.severity === 'medium' ? 'bg-yellow-500/20 text-yellow-500' :
                            'bg-blue-500/20 text-blue-500'
                          }`}>
                            {alert.severity || 'low'}
                          </span>
                        </td>
                        <td className="px-4 py-3 text-text-primary">{alert.message || alert.detail || 'N/A'}</td>
                        <td className="px-4 py-3 text-text-secondary">{formatDate(alert.timestamp || alert.created_at)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}


          {/* Endpoint Usage Table */}
          {metrics?.endpoints && metrics.endpoints.length > 0 && (
            <div>
              <h3 className="text-lg font-semibold text-text-primary mb-4 flex items-center gap-2">
                <Database className="w-5 h-5" />
                Endpoint Usage
              </h3>
              <div className="bg-surface-hover rounded-xl border border-border-default overflow-hidden">
                <table className="w-full">
                  <thead className="bg-surface border-b border-border-default">
                    <tr>
                      <th className="px-4 py-3 text-left text-sm font-semibold text-text-primary">Endpoint</th>
                      <th className="px-4 py-3 text-left text-sm font-semibold text-text-primary">Calls</th>
                      <th className="px-4 py-3 text-left text-sm font-semibold text-text-primary">Tokens</th>
                      <th className="px-4 py-3 text-left text-sm font-semibold text-text-primary">Cost</th>
                      <th className="px-4 py-3 text-left text-sm font-semibold text-text-primary">Avg Latency</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border-default">
                    {metrics.endpoints.map((endpoint: any, idx: number) => (
                      <tr key={idx}>
                        <td className="px-4 py-3 text-text-primary font-medium">{endpoint.endpoint || 'N/A'}</td>
                        <td className="px-4 py-3 text-text-primary">{formatNumber(endpoint.total_calls)}</td>
                        <td className="px-4 py-3 text-text-primary">{formatNumber(endpoint.total_tokens)}</td>
                        <td className="px-4 py-3 text-text-primary">{formatCurrency(endpoint.total_cost)}</td>
                        <td className="px-4 py-3 text-text-primary">{formatDuration(endpoint.avg_latency)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Sessions Detail Modal */}
      {showSessionsModal && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-surface rounded-2xl border border-border-default shadow-2xl w-full max-w-6xl max-h-[90vh] overflow-hidden flex flex-col">
            {/* Modal Header */}
            <div className="sticky top-0 bg-surface border-b border-border-default p-6 flex items-center justify-between z-10">
              <div>
                <h2 className="text-2xl font-semibold text-text-primary">Session Details</h2>
                <p className="text-sm text-text-secondary mt-1">{userName} - {userEmail}</p>
              </div>
              <button
                onClick={() => setShowSessionsModal(false)}
                className="p-2 rounded-lg hover:bg-surface-hover text-text-secondary hover:text-text-primary transition-colors"
                aria-label="Close modal"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Date Range Selector */}
            <div className="p-6 border-b border-border-default bg-surface-hover">
              <div className="flex items-center gap-4 flex-wrap">
                <div className="flex items-center gap-2">
                  <Calendar className="w-4 h-4 text-text-secondary" />
                  <span className="text-sm font-medium text-text-primary">Date Range:</span>
                </div>
                <div className="flex items-center gap-2">
                  <label className="text-sm text-text-secondary">From:</label>
                  <input
                    type="date"
                    value={sessionsDateRange.start}
                    onChange={(e) => setSessionsDateRange({ ...sessionsDateRange, start: e.target.value })}
                    className="bg-surface border border-border-default rounded-lg px-3 py-2 text-sm text-text-primary focus:outline-none focus:border-accent-blue"
                  />
                </div>
                <div className="flex items-center gap-2">
                  <label className="text-sm text-text-secondary">To:</label>
                  <input
                    type="date"
                    value={sessionsDateRange.end}
                    onChange={(e) => setSessionsDateRange({ ...sessionsDateRange, end: e.target.value })}
                    className="bg-surface border border-border-default rounded-lg px-3 py-2 text-sm text-text-primary focus:outline-none focus:border-accent-blue"
                  />
                </div>
                <Button
                  variant="primary"
                  size="sm"
                  onClick={async () => {
                    setLoadingSessions(true);
                    try {
                      if (!ready) return;                      
                      // Calculate days from start date to end date
                      const startDate = new Date(sessionsDateRange.start);
                      const endDate = new Date(sessionsDateRange.end);
                      const daysDiff = Math.ceil((endDate.getTime() - startDate.getTime()) / (1000 * 60 * 60 * 24)) + 1;
                      const days = Math.max(1, Math.min(daysDiff, 365)); // Limit to 365 days
                      
                      const sessionsData = await apiClient.getUserSessions(userId, days);
                      const allSessions = sessionsData?.sessions || [];
                      
                      // Filter sessions by date range
                      const filtered = allSessions.filter((session: any) => {
                        if (!session.login_time) return false;
                        const sessionDate = new Date(session.login_time);
                        const start = new Date(sessionsDateRange.start);
                        const end = new Date(sessionsDateRange.end);
                        end.setHours(23, 59, 59, 999); // Include entire end date
                        return sessionDate >= start && sessionDate <= end;
                      });
                      
                      setFilteredSessions(filtered);
                    } catch (err: any) {
                      console.error('[Sessions] Failed to fetch sessions:', err);
                      setError(err?.message || 'Failed to load sessions');
                    } finally {
                      setLoadingSessions(false);
                    }
                  }}
                  disabled={loadingSessions}
                >
                  {loadingSessions ? (
                    <>
                      <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                      Loading...
                    </>
                  ) : (
                    <>
                      <Filter className="w-4 h-4 mr-2" />
                      Filter
                    </>
                  )}
                </Button>
                <div className="ml-auto text-sm text-text-secondary">
                  Showing {filteredSessions.length} session{filteredSessions.length !== 1 ? 's' : ''}
                </div>
              </div>
            </div>

            {/* Sessions Table */}
            <div className="flex-1 overflow-y-auto p-6">
              {filteredSessions.length > 0 ? (
                <div className="bg-surface-hover rounded-xl border border-border-default overflow-hidden">
                  <table className="w-full">
                    <thead className="bg-surface border-b border-border-default sticky top-0">
                      <tr>
                        <th className="px-4 py-3 text-left text-sm font-semibold text-text-primary">Session ID</th>
                        <th className="px-4 py-3 text-left text-sm font-semibold text-text-primary">Login Time</th>
                        <th className="px-4 py-3 text-left text-sm font-semibold text-text-primary">Logout Time</th>
                        <th className="px-4 py-3 text-left text-sm font-semibold text-text-primary">Duration</th>
                        <th className="px-4 py-3 text-right text-sm font-semibold text-text-primary">Token Consumption</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border-default">
                      {filteredSessions.map((session: any, idx: number) => (
                        <tr key={idx} className="hover:bg-surface-hover/50 transition-colors">
                          <td className="px-4 py-3 text-text-primary font-mono text-sm">{session.session_id}</td>
                          <td className="px-4 py-3 text-text-primary">{formatDate(session.login_time)}</td>
                          <td className="px-4 py-3 text-text-primary">{formatDate(session.logout_time)}</td>
                          <td className="px-4 py-3 text-text-secondary">{session.duration || 'N/A'}</td>
                          <td className="px-4 py-3 text-right text-text-primary font-semibold">
                            {formatNumber(session.token_consumption || 0)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="bg-surface-hover rounded-xl border border-border-default p-12 text-center">
                  <Calendar className="w-12 h-12 text-text-tertiary mx-auto mb-4" />
                  <p className="text-text-secondary">No sessions found for the selected date range</p>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default function UsersPage() {
  const { ready } = useAdminPortalApi();
  const [users, setUsers] = useState<UserData[]>([]);
  const [userAnalytics, setUserAnalytics] = useState<UserAnalytics[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [sortField, setSortField] = useState<SortField>(null);
  const [sortDirection, setSortDirection] = useState<SortDirection>(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [selectedUserId, setSelectedUserId] = useState<string | null>(null);
  const [showFilters, setShowFilters] = useState(false);
  const [filterMetric, setFilterMetric] = useState<'tokensUsed' | 'cost' | 'queries' | 'lastActive' | 'alerts' | null>(null);
  const [filterType, setFilterType] = useState<'highest' | 'least' | 'top' | 'bottom' | 'above' | 'below' | null>(null);
  const [filterValue, setFilterValue] = useState<string>('');
  const [filterRole, setFilterRole] = useState<'all' | 'admin' | 'user'>('all');
  const [filterActivity, setFilterActivity] = useState<'all' | 'active' | 'inactive'>('all');
  const [filterDays, setFilterDays] = useState<number>(30);
  const itemsPerPage = 10;

  // Fetch users and their analytics
  useEffect(() => {
    const fetchData = async () => {
      if (!ready) return;
      
      setLoading(true);
      setError(null);
      
      try {
        
        // Fetch all users
        const usersResponse = await apiClient.listAllUsers();
        const usersList = usersResponse.users || [];
        setUsers(usersList);

        const [tokenData, costData, cacheData, latencyData, alertsData] = await Promise.all([
          apiClient.getTokenConsumption(30, 'user').catch(() => null),
          apiClient.getCostTracking(30, true).catch(() => null),
          apiClient.getCacheEfficiency(30).catch(() => null),
          apiClient.getLatencyDashboard(30).catch(() => null),
          apiClient.getAlertsStatus().catch(() => null),
        ]);
        
        // Build analytics for each user
        const analytics: UserAnalytics[] = usersList.map((user: UserData) => {
          const userId = user.clerk_user_id || user.id;
          
          // Find user in token breakdown
          const userTokenData = tokenData?.breakdown?.find((item: any) => item.key === userId);
          
          // Find user in cost breakdown
          const userCostData = costData?.user_breakdown?.find((item: any) => item.user_id === userId);
          
          // Count alerts for this user
          const userAlerts = alertsData?.alerts?.filter((alert: any) => alert.user_id === userId) || [];
          
          return {
            userId,
            email: user.email || 'N/A',
            name: `${user.first_name || ''} ${user.last_name || ''}`.trim() || user.username || user.email || 'Unknown',
            tokensUsed: userTokenData?.total_tokens || 0,
            inputTokens: userTokenData?.prompt_tokens || 0,
            outputTokens: userTokenData?.completion_tokens || 0,
            cost: userCostData?.cost || 0,
            queries: userTokenData?.total_calls || 0,
            avgLatency: latencyData?.summary?.avg_latency_ms || 0,
            cacheHits: 0, // Would need user-specific cache data
            cacheMisses: 0,
            cacheHitRate: 0,
            lastActive: user.last_sign_in_at || user.created_at || '',
            alerts: userAlerts.length,
          };
        });
        
        setUserAnalytics(analytics);
      } catch (err: any) {
        console.error('[Users] Failed to fetch data:', err);
        setError(err?.message || 'Failed to load users');
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, [ready]);

  // Filter and sort users
  const filteredAndSortedUsers = useMemo(() => {
    let filtered = [...userAnalytics];

    // Apply search filter
    if (searchQuery) {
      const searchLower = searchQuery.toLowerCase();
      filtered = filtered.filter((user) => {
        return (
          user.userId.toLowerCase().includes(searchLower) ||
          user.email.toLowerCase().includes(searchLower) ||
          user.name.toLowerCase().includes(searchLower) ||
          user.tokensUsed.toString().includes(searchLower) ||
          user.cost.toString().includes(searchLower) ||
          user.queries.toString().includes(searchLower)
        );
      });
    }

    // Apply role filter
    if (filterRole !== 'all') {
      filtered = filtered.filter((user) => {
        const userData = users.find(u => (u.clerk_user_id || u.id) === user.userId);
        return userData?.role === filterRole;
      });
    }

    // Apply activity filter
    if (filterActivity !== 'all') {
      const cutoffDate = new Date();
      cutoffDate.setDate(cutoffDate.getDate() - filterDays);
      
      filtered = filtered.filter((user) => {
        if (!user.lastActive) return filterActivity === 'inactive';
        const lastActiveDate = new Date(user.lastActive);
        return filterActivity === 'active' 
          ? lastActiveDate >= cutoffDate 
          : lastActiveDate < cutoffDate;
      });
    }

    // Apply metric filters
    if (filterMetric && filterType) {
      if (filterType === 'highest') {
        // Sort by metric descending and take top users
        filtered = [...filtered].sort((a, b) => {
          const aVal = a[filterMetric];
          const bVal = b[filterMetric];
          if (typeof aVal === 'number' && typeof bVal === 'number') {
            return bVal - aVal;
          }
          if (typeof aVal === 'string' && typeof bVal === 'string') {
            return new Date(bVal).getTime() - new Date(aVal).getTime();
          }
          return 0;
        });
        const topN = filterValue ? parseInt(filterValue) : 10;
        filtered = filtered.slice(0, Math.min(topN, filtered.length));
      } else if (filterType === 'least') {
        // Sort by metric ascending and take bottom users
        filtered = [...filtered].sort((a, b) => {
          const aVal = a[filterMetric];
          const bVal = b[filterMetric];
          if (typeof aVal === 'number' && typeof bVal === 'number') {
            return aVal - bVal;
          }
          if (typeof aVal === 'string' && typeof bVal === 'string') {
            return new Date(aVal).getTime() - new Date(bVal).getTime();
          }
          return 0;
        });
        const bottomN = filterValue ? parseInt(filterValue) : 10;
        filtered = filtered.slice(0, Math.min(bottomN, filtered.length));
      } else if (filterType === 'top') {
        const topN = filterValue ? parseInt(filterValue) : 10;
        filtered = [...filtered].sort((a, b) => {
          const aVal = a[filterMetric];
          const bVal = b[filterMetric];
          if (typeof aVal === 'number' && typeof bVal === 'number') {
            return bVal - aVal;
          }
          if (typeof aVal === 'string' && typeof bVal === 'string') {
            return new Date(bVal).getTime() - new Date(aVal).getTime();
          }
          return 0;
        }).slice(0, Math.min(topN, filtered.length));
      } else if (filterType === 'bottom') {
        const bottomN = filterValue ? parseInt(filterValue) : 10;
        filtered = [...filtered].sort((a, b) => {
          const aVal = a[filterMetric];
          const bVal = b[filterMetric];
          if (typeof aVal === 'number' && typeof bVal === 'number') {
            return aVal - bVal;
          }
          if (typeof aVal === 'string' && typeof bVal === 'string') {
            return new Date(aVal).getTime() - new Date(bVal).getTime();
          }
          return 0;
        }).slice(0, Math.min(bottomN, filtered.length));
      } else if (filterType === 'above' && filterValue) {
        const threshold = parseFloat(filterValue);
        filtered = filtered.filter((user) => {
          const val = user[filterMetric];
          if (typeof val === 'number') {
            return val >= threshold;
          }
          return false;
        });
      } else if (filterType === 'below' && filterValue) {
        const threshold = parseFloat(filterValue);
        filtered = filtered.filter((user) => {
          const val = user[filterMetric];
          if (typeof val === 'number') {
            return val <= threshold;
          }
          return false;
        });
      }
    }

    // Apply alerts filter
    if (filterMetric === 'alerts' && filterType) {
      if (filterType === 'above' && filterValue) {
        const threshold = parseInt(filterValue);
        filtered = filtered.filter((user) => user.alerts >= threshold);
      } else if (filterType === 'below' && filterValue) {
        const threshold = parseInt(filterValue);
        filtered = filtered.filter((user) => user.alerts <= threshold);
      } else if (filterType === 'highest') {
        filtered = [...filtered].sort((a, b) => b.alerts - a.alerts);
        const topN = filterValue ? parseInt(filterValue) : 10;
        filtered = filtered.slice(0, Math.min(topN, filtered.length));
      } else if (filterType === 'least') {
        filtered = [...filtered].sort((a, b) => a.alerts - b.alerts);
        const bottomN = filterValue ? parseInt(filterValue) : 10;
        filtered = filtered.slice(0, Math.min(bottomN, filtered.length));
      }
    }

    if (sortField && sortDirection) {
      filtered = [...filtered].sort((a, b) => {
        const aVal = a[sortField];
        const bVal = b[sortField];

        if (aVal === bVal) return 0;

        let comparison = 0;
        if (typeof aVal === 'string' && typeof bVal === 'string') {
          comparison = aVal.localeCompare(bVal);
        } else if (typeof aVal === 'number' && typeof bVal === 'number') {
          comparison = aVal - bVal;
        }

        return sortDirection === 'asc' ? comparison : -comparison;
      });
    }

    return filtered;
  }, [userAnalytics, searchQuery, sortField, sortDirection, filterMetric, filterType, filterValue, filterRole, filterActivity, filterDays, users]);

  // Pagination
  const totalPages = Math.ceil(filteredAndSortedUsers.length / itemsPerPage);
  const startIndex = (currentPage - 1) * itemsPerPage;
  const endIndex = startIndex + itemsPerPage;
  const paginatedUsers = filteredAndSortedUsers.slice(startIndex, endIndex);

  // Handle sort
  const handleSort = (field: keyof UserAnalytics) => {
    if (sortField === field) {
      if (sortDirection === 'asc') {
        setSortDirection('desc');
      } else if (sortDirection === 'desc') {
        setSortField(null);
        setSortDirection(null);
      }
    } else {
      setSortField(field);
      setSortDirection('asc');
    }
  };

  // Reset to first page when search changes
  const handleSearchChange = (value: string) => {
    setSearchQuery(value);
    setCurrentPage(1);
  };

  // Reset to first page when filters change
  useEffect(() => {
    setCurrentPage(1);
  }, [filterMetric, filterType, filterValue, filterRole, filterActivity, filterDays]);

  // Format helpers
  const formatNumber = (num: number) => {
    return num.toLocaleString('en-US');
  };

  const formatDate = (dateString: string) => {
    if (!dateString) return 'Never';
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
    const diffDays = Math.floor(diffHours / 24);

    if (diffHours < 1) {
      const diffMins = Math.floor(diffMs / (1000 * 60));
      return `${diffMins}m ago`;
    } else if (diffHours < 24) {
      return `${diffHours}h ago`;
    } else if (diffDays === 1) {
      return 'Yesterday';
    } else if (diffDays < 7) {
      return `${diffDays}d ago`;
    } else {
      return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    }
  };

  const formatCurrency = (amount: number) => {
    return `$${amount.toFixed(4)}`;
  };

  const getSortIcon = (field: keyof UserAnalytics) => {
    if (sortField !== field) {
      return <ChevronUp className="w-4 h-4 text-text-tertiary opacity-0 group-hover:opacity-50" />;
    }
    if (sortDirection === 'asc') {
      return <ChevronUp className="w-4 h-4 text-accent-blue" />;
    }
    return <ChevronDown className="w-4 h-4 text-accent-blue" />;
  };

  const selectedUser = selectedUserId ? userAnalytics.find(u => u.userId === selectedUserId) : null;
  const selectedUserData = selectedUserId ? users.find(u => (u.clerk_user_id || u.id) === selectedUserId) : null;

  if (loading) return <AdminTableSkeleton />;

  if (error) {
    return (
      <div className="h-full">
        <div className="mb-6">
          <h1 className="text-2xl font-semibold text-text-primary">Users Analytics</h1>
          <p className="text-sm text-text-secondary mt-1">
            View and analyze user activity, queries, and performance metrics
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
        <h1 className="text-2xl font-semibold text-text-primary">Users Analytics</h1>
        <p className="text-sm text-text-secondary mt-1">
          View and analyze user activity, token consumption, and costs
        </p>
      </div>
      
      {/* Search and Filters */}
      <div className="mb-6 space-y-4">
        <div className="flex items-center gap-4">
          <div className="relative flex-1">
            <Search className="absolute left-4 top-1/2 transform -translate-y-1/2 w-5 h-5 text-text-tertiary" />
            <Input
              type="text"
              placeholder="Search by User ID, Email, Name, Tokens, Cost, or Queries..."
              value={searchQuery}
              onChange={(e) => handleSearchChange(e.target.value)}
              className="pl-12 pr-4"
            />
          </div>
          <Button
            variant="secondary"
            size="sm"
            onClick={() => setShowFilters(!showFilters)}
            className="flex items-center gap-2"
          >
            <Filter className="w-4 h-4" />
            Filters
            {(filterMetric || filterRole !== 'all' || filterActivity !== 'all') && (
              <span className="ml-1 px-1.5 py-0.5 bg-accent-blue text-background rounded-full text-xs">
                {[filterMetric, filterRole !== 'all' ? filterRole : null, filterActivity !== 'all' ? filterActivity : null].filter(Boolean).length}
              </span>
            )}
          </Button>
        </div>

        {/* Filter Panel */}
        {showFilters && (
          <div className="bg-surface-hover rounded-xl border border-border-default p-4 space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-sm font-semibold text-text-primary">Filter Options</h3>
              <button
                onClick={() => {
                  setFilterMetric(null);
                  setFilterType(null);
                  setFilterValue('');
                  setFilterRole('all');
                  setFilterActivity('all');
                }}
                className="text-xs text-text-secondary hover:text-text-primary transition-colors"
              >
                Clear All
              </button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
              {/* Metric Filter */}
              <div>
                <label className="block text-xs font-medium text-text-secondary mb-2">Filter By</label>
                <select
                  value={filterMetric || ''}
                  onChange={(e) => {
                    setFilterMetric(e.target.value as any || null);
                    setFilterType(null);
                    setFilterValue('');
                  }}
                  className="w-full bg-surface border border-border-default rounded-lg px-3 py-2 text-sm text-text-primary focus:outline-none focus:border-border-active"
                >
                  <option value="">Select metric...</option>
                  <option value="tokensUsed">Tokens Used</option>
                  <option value="cost">Cost</option>
                  <option value="queries">Queries</option>
                  <option value="lastActive">Last Active</option>
                  <option value="alerts">Alerts</option>
                </select>
              </div>

              {/* Filter Type */}
              {filterMetric && (
                <div>
                  <label className="block text-xs font-medium text-text-secondary mb-2">Filter Type</label>
                  <select
                    value={filterType || ''}
                    onChange={(e) => {
                      setFilterType(e.target.value as any || null);
                      if (e.target.value !== 'above' && e.target.value !== 'below') {
                        setFilterValue('');
                      }
                    }}
                    className="w-full bg-surface border border-border-default rounded-lg px-3 py-2 text-sm text-text-primary focus:outline-none focus:border-border-active"
                  >
                    <option value="">Select type...</option>
                    <option value="highest">Highest</option>
                    <option value="least">Least</option>
                    <option value="top">Top N</option>
                    <option value="bottom">Bottom N</option>
                    {filterMetric !== 'lastActive' && filterMetric !== 'alerts' && (
                      <>
                        <option value="above">Above Value</option>
                        <option value="below">Below Value</option>
                      </>
                    )}
                    {filterMetric === 'alerts' && (
                      <>
                        <option value="above">With Alerts ≥</option>
                        <option value="below">With Alerts ≤</option>
                      </>
                    )}
                  </select>
                </div>
              )}

              {/* Filter Value */}
              {filterType && (filterType === 'top' || filterType === 'bottom' || filterType === 'above' || filterType === 'below') && (
                <div>
                  <label className="block text-xs font-medium text-text-secondary mb-2">
                    {filterType === 'top' || filterType === 'bottom' ? 'Number of Users' : 'Value'}
                  </label>
                  <Input
                    type="number"
                    value={filterValue}
                    onChange={(e) => setFilterValue(e.target.value)}
                    placeholder={filterType === 'top' || filterType === 'bottom' ? 'e.g., 10' : filterMetric === 'cost' ? 'e.g., 10.50' : 'e.g., 1000'}
                    className="w-full"
                  />
                </div>
              )}

              {/* Role Filter */}
              <div>
                <label className="block text-xs font-medium text-text-secondary mb-2">Role</label>
                <select
                  value={filterRole}
                  onChange={(e) => setFilterRole(e.target.value as any)}
                  className="w-full bg-surface border border-border-default rounded-lg px-3 py-2 text-sm text-text-primary focus:outline-none focus:border-border-active"
                >
                  <option value="all">All Roles</option>
                  <option value="admin">Admin</option>
                  <option value="user">User</option>
                </select>
              </div>

              {/* Activity Filter */}
              <div>
                <label className="block text-xs font-medium text-text-secondary mb-2">Activity</label>
                <select
                  value={filterActivity}
                  onChange={(e) => setFilterActivity(e.target.value as any)}
                  className="w-full bg-surface border border-border-default rounded-lg px-3 py-2 text-sm text-text-primary focus:outline-none focus:border-border-active"
                >
                  <option value="all">All Users</option>
                  <option value="active">Active (last {filterDays} days)</option>
                  <option value="inactive">Inactive (last {filterDays} days)</option>
                </select>
              </div>

              {/* Activity Days */}
              {filterActivity !== 'all' && (
                <div>
                  <label className="block text-xs font-medium text-text-secondary mb-2">Days</label>
                  <Input
                    type="number"
                    value={filterDays}
                    onChange={(e) => setFilterDays(parseInt(e.target.value) || 30)}
                    min="1"
                    max="365"
                    className="w-full"
                  />
                </div>
              )}
            </div>

            {/* Active Filters Display */}
            {(filterMetric || filterRole !== 'all' || filterActivity !== 'all') && (
              <div className="flex flex-wrap gap-2 pt-2 border-t border-border-default">
                <span className="text-xs text-text-secondary">Active filters:</span>
                {filterMetric && filterType && (
                  <span className="inline-flex items-center gap-1 px-2 py-1 bg-accent-blue/10 text-accent-blue rounded text-xs">
                    {filterMetric} - {filterType}
                    {filterValue && ` (${filterValue})`}
                    <button
                      onClick={() => {
                        setFilterMetric(null);
                        setFilterType(null);
                        setFilterValue('');
                      }}
                      className="hover:opacity-70"
                    >
                      <XCircle className="w-3 h-3" />
                    </button>
                  </span>
                )}
                {filterRole !== 'all' && (
                  <span className="inline-flex items-center gap-1 px-2 py-1 bg-accent-blue/10 text-accent-blue rounded text-xs">
                    Role: {filterRole}
                    <button
                      onClick={() => setFilterRole('all')}
                      className="hover:opacity-70"
                    >
                      <XCircle className="w-3 h-3" />
                    </button>
                  </span>
                )}
                {filterActivity !== 'all' && (
                  <span className="inline-flex items-center gap-1 px-2 py-1 bg-accent-blue/10 text-accent-blue rounded text-xs">
                    Activity: {filterActivity} ({filterDays} days)
                    <button
                      onClick={() => setFilterActivity('all')}
                      className="hover:opacity-70"
                    >
                      <XCircle className="w-3 h-3" />
                    </button>
                  </span>
                )}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Table */}
      <div className="bg-surface rounded-2xl border border-border-default overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-surface-hover border-b border-border-default">
              <tr>
                <th
                  className="px-6 py-4 text-left text-sm font-semibold text-text-primary cursor-pointer hover:bg-surface-hover/80 transition-colors group"
                  onClick={() => handleSort('userId')}
                >
                  <div className="flex items-center gap-2">
                    User ID
                    {getSortIcon('userId')}
                  </div>
                </th>
                <th
                  className="px-6 py-4 text-left text-sm font-semibold text-text-primary cursor-pointer hover:bg-surface-hover/80 transition-colors group"
                  onClick={() => handleSort('name')}
                >
                  <div className="flex items-center gap-2">
                    Name
                    {getSortIcon('name')}
                  </div>
                </th>
                <th
                  className="px-6 py-4 text-left text-sm font-semibold text-text-primary cursor-pointer hover:bg-surface-hover/80 transition-colors group"
                  onClick={() => handleSort('tokensUsed')}
                >
                  <div className="flex items-center gap-2">
                    Tokens Used
                    {getSortIcon('tokensUsed')}
                  </div>
                </th>
                <th
                  className="px-6 py-4 text-left text-sm font-semibold text-text-primary cursor-pointer hover:bg-surface-hover/80 transition-colors group"
                  onClick={() => handleSort('cost')}
                >
                  <div className="flex items-center gap-2">
                    Cost
                    {getSortIcon('cost')}
                  </div>
                </th>
                <th
                  className="px-6 py-4 text-left text-sm font-semibold text-text-primary cursor-pointer hover:bg-surface-hover/80 transition-colors group"
                  onClick={() => handleSort('queries')}
                >
                  <div className="flex items-center gap-2">
                    Queries
                    {getSortIcon('queries')}
                  </div>
                </th>
                <th
                  className="px-6 py-4 text-left text-sm font-semibold text-text-primary cursor-pointer hover:bg-surface-hover/80 transition-colors group"
                  onClick={() => handleSort('lastActive')}
                >
                  <div className="flex items-center gap-2">
                    Last Active
                    {getSortIcon('lastActive')}
                  </div>
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border-default">
              {paginatedUsers.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-6 py-12 text-center">
                    <p className="text-text-secondary">No users found matching your search.</p>
                  </td>
                </tr>
              ) : (
                paginatedUsers.map((user) => (
                  <tr
                    key={user.userId}
                    onClick={() => setSelectedUserId(user.userId)}
                    className="hover:bg-surface-hover cursor-pointer transition-colors"
                  >
                    <td className="px-6 py-4 text-text-primary font-medium font-mono text-sm">{user.userId}</td>
                    <td className="px-6 py-4 text-text-primary">{user.name}</td>
                    <td className="px-6 py-4 text-text-primary">{formatNumber(user.tokensUsed)}</td>
                    <td className="px-6 py-4 text-text-primary">{formatCurrency(user.cost)}</td>
                    <td className="px-6 py-4 text-text-primary">{formatNumber(user.queries)}</td>
                    <td className="px-6 py-4 text-text-secondary">{formatDate(user.lastActive)}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="px-6 py-4 border-t border-border-default flex items-center justify-between">
            <div className="text-sm text-text-secondary">
              Showing {startIndex + 1} to {Math.min(endIndex, filteredAndSortedUsers.length)} of{' '}
              {filteredAndSortedUsers.length} users
            </div>
            <div className="flex items-center gap-2">
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setCurrentPage((prev) => Math.max(1, prev - 1))}
                disabled={currentPage === 1}
                className="disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <ChevronLeft className="w-4 h-4" />
                Previous
              </Button>
              <div className="flex items-center gap-1">
                {Array.from({ length: totalPages }, (_, i) => i + 1).map((page) => {
                  if (
                    page === 1 ||
                    page === totalPages ||
                    (page >= currentPage - 1 && page <= currentPage + 1)
                  ) {
                    return (
                      <button
                        key={page}
                        onClick={() => setCurrentPage(page)}
                        className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                          currentPage === page
                            ? 'bg-accent-blue text-background'
                            : 'text-text-secondary hover:bg-surface-hover hover:text-text-primary'
                        }`}
                      >
                        {page}
                      </button>
                    );
                  } else if (page === currentPage - 2 || page === currentPage + 2) {
                    return (
                      <span key={page} className="px-2 text-text-tertiary">
                        ...
                      </span>
                    );
                  }
                  return null;
                })}
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => setCurrentPage((prev) => Math.min(totalPages, prev + 1))}
                disabled={currentPage === totalPages}
                className="disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Next
                <ChevronRight className="w-4 h-4" />
              </Button>
            </div>
          </div>
        )}
      </div>

      {/* User Detail Panel */}
      {selectedUserId && selectedUser && selectedUserData && (
        <UserDetailPanel
          userId={selectedUserId}
          userName={selectedUser.name}
          userEmail={selectedUser.email}
          onClose={() => setSelectedUserId(null)}
        />
      )}
    </div>
  );
}