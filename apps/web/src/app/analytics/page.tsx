/**
 * Analytics Dashboard Page
 * 
 * Shows admin dashboard for admins, individual user metrics for regular users.
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
import { useAuth } from '@clerk/nextjs';
import { apiClient } from '@/lib/api-client';
import { X, AlertCircle, TrendingUp, DollarSign, Clock, Database, Phone, Users, Search, Shield, AlertTriangle } from 'lucide-react';
import { KPICard } from '@/components/analytics/KPICard';

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

// Chart options for cost/currency charts
const chartOptionsWithCurrency = {
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
      callbacks: {
        label: function(context: any) {
          const value = context.parsed.y;
          if (typeof value === 'number') {
            if (value >= 1000000) {
              return (value / 1000000).toFixed(2) + 'M';
            } else if (value >= 1000) {
              return (value / 1000).toFixed(2) + 'K';
            } else if (value < 1 && value > 0) {
              return '$' + value.toFixed(4);
            } else {
              return value.toLocaleString();
            }
          }
          return value;
        },
      },
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
        callback: function(value: any) {
          if (typeof value === 'number') {
            if (value >= 1000000) {
              return (value / 1000000).toFixed(1) + 'M';
            } else if (value >= 1000) {
              return (value / 1000).toFixed(1) + 'K';
            } else if (value < 1 && value > 0) {
              return '$' + value.toFixed(2);
            }
          }
          return value;
        },
      },
    },
  },
};

// Chart options for numeric charts (queries, tokens, alerts, etc.)
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
      callbacks: {
        label: function(context: any) {
          const value = context.parsed.y;
          if (typeof value === 'number') {
            if (value >= 1000000) {
              return (value / 1000000).toFixed(2) + 'M';
            } else if (value >= 1000) {
              return (value / 1000).toFixed(2) + 'K';
            } else {
              return value.toLocaleString();
            }
          }
          return value;
        },
      },
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
        callback: function(value: any) {
          if (typeof value === 'number') {
            if (value >= 1000000) {
              return (value / 1000000).toFixed(1) + 'M';
            } else if (value >= 1000) {
              return (value / 1000).toFixed(1) + 'K';
            }
          }
          return value;
        },
      },
    },
  },
};

// Prepare chart data
const prepareChartData = (
  data: { date?: string; timestamp?: string; [key: string]: any }[] | undefined,
  valueKey: string,
  label: string,
  color: string
) => {
  if (!data || data.length === 0) {
    // No data provided
    return {
      labels: [],
      datasets: [],
    };
  }

  // Processing chart data

  const processedData = {
    labels: data.map((item) => {
      const dateStr = item.date || item.timestamp || item.day;
      if (!dateStr) {
        // Missing date in item
        return '';
      }
      const date = new Date(dateStr);
      if (isNaN(date.getTime())) {
        // Invalid date format
        return dateStr;
      }
      return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
    }),
    datasets: [
      {
        label,
        data: data.map((item, idx) => {
          // Try multiple possible keys
          const value = item[valueKey] || item.value || item.total || item.count || item.amount || 0;
          if (idx === 0) {
            // Extracting value
          }
          return value;
        }),
        borderColor: color,
        backgroundColor: color + '20',
        fill: true,
        tension: 0.4,
        pointRadius: 3,
        pointHoverRadius: 5,
      },
    ],
  };

  // Chart data processed

  return processedData;
};

// Admin Metric Detail Modal Component
interface AdminMetricDetailModalProps {
  metricType: string;
  adminMetrics: any;
  adminSummary: any;
  adminUsage: any;
  users: any[];
  alerts?: any;
  userBreakdown?: any;
  ragQualityData?: any;
  onClose: () => void;
}

function AdminMetricDetailModal({ 
  metricType, 
  adminMetrics, 
  adminSummary, 
  adminUsage, 
  users,
  alerts,
  userBreakdown,
  ragQualityData,
  onClose 
}: AdminMetricDetailModalProps) {
  
  // Helper function to get user info by ID
  const getUserInfo = (userId: string) => {
    const user = users.find((u: any) => u.id === userId || u.user_id === userId);
    if (user) {
      return {
        email: user.email || user.username || 'N/A',
        name: user.first_name && user.last_name 
          ? `${user.first_name} ${user.last_name}`
          : user.first_name || user.last_name || '—',
      };
    }
    return { email: userId, name: '—' };
  };
  
  // Helper function to get highest user for a metric
  const getHighestUser = (breakdown: any[], valueKey: string) => {
    if (!breakdown || breakdown.length === 0) return null;
    const top = breakdown[0];
    const userInfo = getUserInfo(top.user_id || top.key || '');
    return {
      ...userInfo,
      value: top[valueKey] || top.value || top.cost || top.tokens || 0,
      percentage: top.percentage || 0,
    };
  };
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
    switch (metricType) {
      case 'users':
        return (
          <div className="space-y-6">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="bg-surface-hover rounded-xl p-4 border border-border-default">
                <h4 className="text-xs font-medium text-text-secondary mb-1">Total Users</h4>
                <p className="text-2xl font-bold text-text-primary">
                  {formatNumber(users.length || adminMetrics?.users?.total || 0)}
                </p>
              </div>
              <div className="bg-surface-hover rounded-xl p-4 border border-border-default">
                <h4 className="text-xs font-medium text-text-secondary mb-1">Active Users</h4>
                <p className="text-2xl font-bold text-text-primary">
                  {formatNumber(adminMetrics?.users?.active || users.filter((u: any) => u.last_sign_in_at).length)}
                </p>
              </div>
              <div className="bg-surface-hover rounded-xl p-4 border border-border-default">
                <h4 className="text-xs font-medium text-text-secondary mb-1">Admin Users</h4>
                <p className="text-2xl font-bold text-text-primary">
                  {formatNumber(users.filter((u: any) => u.role === 'admin').length)}
                </p>
              </div>
              <div className="bg-surface-hover rounded-xl p-4 border border-border-default">
                <h4 className="text-xs font-medium text-text-secondary mb-1">Regular Users</h4>
                <p className="text-2xl font-bold text-text-primary">
                  {formatNumber(users.filter((u: any) => u.role === 'user').length)}
                </p>
              </div>
            </div>
            {users.length > 0 && (
              <div>
                <h3 className="text-sm font-semibold text-text-primary mb-3">User List</h3>
                <div className="space-y-2 max-h-96 overflow-y-auto">
                  {users.map((user: any, idx: number) => (
                    <div key={idx} className="p-3 bg-surface-hover rounded-lg border border-border-default">
                      <div className="flex justify-between items-start">
                        <div className="flex-1">
                          <p className="text-sm font-medium text-text-primary">
                            {user.email || user.username || 'N/A'}
                          </p>
                          <p className="text-xs text-text-secondary mt-1">
                            {user.first_name && user.last_name 
                              ? `${user.first_name} ${user.last_name}`
                              : user.first_name || user.last_name || '—'}
                          </p>
                          <p className="text-xs text-text-tertiary mt-1">
                            {user.last_sign_in_at 
                              ? `Last active: ${new Date(user.last_sign_in_at).toLocaleDateString()}`
                              : 'Never signed in'}
                          </p>
                        </div>
                        <span className={`text-xs font-medium px-2 py-1 rounded ${
                          user.role === 'admin' 
                            ? 'bg-accent-blue/20 text-accent-blue' 
                            : 'bg-surface text-text-secondary'
                        }`}>
                          {user.role || 'user'}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        );

      case 'cost':
        const highestCostUser = getHighestUser(userBreakdown?.cost?.user_breakdown || [], 'cost');
        return (
          <div className="space-y-6">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="bg-surface-hover rounded-xl p-4 border border-border-default">
                <h4 className="text-xs font-medium text-text-secondary mb-1">Total Cost</h4>
                <p className="text-2xl font-bold text-text-primary">
                  {formatCurrency(adminSummary.costs?.total || adminUsage.total_cost || userBreakdown?.cost?.summary?.total_cost || 0)}
                </p>
              </div>
              <div className="bg-surface-hover rounded-xl p-4 border border-border-default">
                <h4 className="text-xs font-medium text-text-secondary mb-1">Input Cost</h4>
                <p className="text-2xl font-bold text-text-primary">
                  {formatCurrency(adminSummary.costs?.input || adminUsage.input_cost || 0)}
                </p>
              </div>
              <div className="bg-surface-hover rounded-xl p-4 border border-border-default">
                <h4 className="text-xs font-medium text-text-secondary mb-1">Output Cost</h4>
                <p className="text-2xl font-bold text-text-primary">
                  {formatCurrency(adminSummary.costs?.output || adminUsage.output_cost || 0)}
                </p>
              </div>
              <div className="bg-surface-hover rounded-xl p-4 border border-border-default">
                <h4 className="text-xs font-medium text-text-secondary mb-1">Avg Cost/Call</h4>
                <p className="text-2xl font-bold text-text-primary">
                  {formatCurrency(
                    (adminSummary.costs?.total || adminUsage.total_cost || 0) / 
                    (adminSummary.llm_calls?.total || adminUsage.total_calls || 1)
                  )}
                </p>
              </div>
            </div>
            {highestCostUser && (
              <div className="bg-accent-blue/10 rounded-xl p-4 border border-accent-blue/20">
                <h3 className="text-sm font-semibold text-text-primary mb-2">Highest User</h3>
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-base font-medium text-text-primary">{highestCostUser.email}</p>
                    <p className="text-xs text-text-secondary mt-1">{highestCostUser.name}</p>
                  </div>
                  <div className="text-right">
                    <p className="text-lg font-bold text-accent-blue">{formatCurrency(highestCostUser.value)}</p>
                    <p className="text-xs text-text-tertiary">{highestCostUser.percentage.toFixed(1)}% of total</p>
                  </div>
                </div>
              </div>
            )}
            <div>
              <h3 className="text-sm font-semibold text-text-primary mb-3">Cost Breakdown</h3>
              <div className="space-y-2">
                <div className="flex justify-between items-center p-3 bg-surface-hover rounded-lg border border-border-default">
                  <span className="text-sm text-text-secondary">Total Cost</span>
                  <span className="text-sm font-medium text-text-primary">
                    {formatCurrency(adminSummary.costs?.total || adminUsage.total_cost || 0)}
                  </span>
                </div>
                <div className="flex justify-between items-center p-3 bg-surface-hover rounded-lg border border-border-default">
                  <span className="text-sm text-text-secondary">Input Cost</span>
                  <span className="text-sm font-medium text-text-primary">
                    {formatCurrency(adminSummary.costs?.input || adminUsage.input_cost || 0)}
                  </span>
                </div>
                <div className="flex justify-between items-center p-3 bg-surface-hover rounded-lg border border-border-default">
                  <span className="text-sm text-text-secondary">Output Cost</span>
                  <span className="text-sm font-medium text-text-primary">
                    {formatCurrency(adminSummary.costs?.output || adminUsage.output_cost || 0)}
                  </span>
                </div>
                <div className="flex justify-between items-center p-3 bg-surface-hover rounded-lg border border-border-default">
                  <span className="text-sm text-text-secondary">Avg Cost per Call</span>
                  <span className="text-sm font-medium text-text-primary">
                    {formatCurrency(
                      (adminSummary.costs?.total || adminUsage.total_cost || 0) / 
                      (adminSummary.llm_calls?.total || adminUsage.total_calls || 1)
                    )}
                  </span>
                </div>
              </div>
            </div>
          </div>
        );

      case 'queries':
        return (
          <div className="space-y-6">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="bg-surface-hover rounded-xl p-4 border border-border-default">
                <h4 className="text-xs font-medium text-text-secondary mb-1">Total Queries</h4>
                <p className="text-2xl font-bold text-text-primary">
                  {formatNumber(adminSummary.llm_calls?.total || adminUsage.total_calls || 0)}
                </p>
              </div>
              <div className="bg-surface-hover rounded-xl p-4 border border-border-default">
                <h4 className="text-xs font-medium text-text-secondary mb-1">Successful</h4>
                <p className="text-2xl font-bold text-text-primary">
                  {formatNumber(adminSummary.llm_calls?.successful || adminUsage.successful_calls || 0)}
                </p>
              </div>
              <div className="bg-surface-hover rounded-xl p-4 border border-border-default">
                <h4 className="text-xs font-medium text-text-secondary mb-1">Failed</h4>
                <p className="text-2xl font-bold text-text-primary">
                  {formatNumber(adminSummary.llm_calls?.failed || adminUsage.failed_calls || 0)}
                </p>
              </div>
              <div className="bg-surface-hover rounded-xl p-4 border border-border-default">
                <h4 className="text-xs font-medium text-text-secondary mb-1">Success Rate</h4>
                <p className="text-2xl font-bold text-text-primary">
                  {formatPercentage(
                    ((adminSummary.llm_calls?.successful || adminUsage.successful_calls || 0) / 
                     (adminSummary.llm_calls?.total || adminUsage.total_calls || 1)) * 100
                  )}
                </p>
              </div>
            </div>
            <div>
              <h3 className="text-sm font-semibold text-text-primary mb-3">Query Statistics</h3>
              <div className="space-y-2">
                <div className="flex justify-between items-center p-3 bg-surface-hover rounded-lg border border-border-default">
                  <span className="text-sm text-text-secondary">Total API Calls</span>
                  <span className="text-sm font-medium text-text-primary">
                    {formatNumber(adminSummary.llm_calls?.total || adminUsage.total_calls || 0)}
                  </span>
                </div>
                <div className="flex justify-between items-center p-3 bg-surface-hover rounded-lg border border-border-default">
                  <span className="text-sm text-text-secondary">Avg Queries per User</span>
                  <span className="text-sm font-medium text-text-primary">
                    {formatNumber(
                      (adminSummary.llm_calls?.total || adminUsage.total_calls || 0) / (users.length || 1)
                    )}
                  </span>
                </div>
              </div>
            </div>
          </div>
        );

      case 'tokens':
        const highestTokenUser = getHighestUser(userBreakdown?.tokens?.breakdown || [], 'total_tokens');
        return (
          <div className="space-y-6">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="bg-surface-hover rounded-xl p-4 border border-border-default">
                <h4 className="text-xs font-medium text-text-secondary mb-1">Total Tokens</h4>
                <p className="text-2xl font-bold text-text-primary">
                  {formatNumber(adminSummary.tokens?.total || adminUsage.total_tokens || 0)}
                </p>
              </div>
              <div className="bg-surface-hover rounded-xl p-4 border border-border-default">
                <h4 className="text-xs font-medium text-text-secondary mb-1">Input Tokens</h4>
                <p className="text-2xl font-bold text-text-primary">
                  {formatNumber(adminSummary.tokens?.input || adminUsage.input_tokens || 0)}
                </p>
              </div>
              <div className="bg-surface-hover rounded-xl p-4 border border-border-default">
                <h4 className="text-xs font-medium text-text-secondary mb-1">Output Tokens</h4>
                <p className="text-2xl font-bold text-text-primary">
                  {formatNumber(adminSummary.tokens?.output || adminUsage.output_tokens || 0)}
                </p>
              </div>
              <div className="bg-surface-hover rounded-xl p-4 border border-border-default">
                <h4 className="text-xs font-medium text-text-secondary mb-1">Avg Tokens/Call</h4>
                <p className="text-2xl font-bold text-text-primary">
                  {formatNumber(
                    (adminSummary.tokens?.total || adminUsage.total_tokens || 0) / 
                    (adminSummary.llm_calls?.total || adminUsage.total_calls || 1)
                  )}
                </p>
              </div>
            </div>
            {highestTokenUser && (
              <div className="bg-accent-blue/10 rounded-xl p-4 border border-accent-blue/20">
                <h3 className="text-sm font-semibold text-text-primary mb-2">Highest User</h3>
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-base font-medium text-text-primary">{highestTokenUser.email}</p>
                    <p className="text-xs text-text-secondary mt-1">{highestTokenUser.name}</p>
                  </div>
                  <div className="text-right">
                    <p className="text-lg font-bold text-accent-blue">{formatNumber(highestTokenUser.value)}</p>
                    <p className="text-xs text-text-tertiary">{highestTokenUser.percentage.toFixed(1)}% of total</p>
                  </div>
                </div>
              </div>
            )}
            <div>
              <h3 className="text-sm font-semibold text-text-primary mb-3">Token Breakdown</h3>
              <div className="space-y-2">
                <div className="flex justify-between items-center p-3 bg-surface-hover rounded-lg border border-border-default">
                  <span className="text-sm text-text-secondary">Input Tokens</span>
                  <span className="text-sm font-medium text-text-primary">
                    {formatNumber(adminSummary.tokens?.input || adminUsage.input_tokens || 0)} (
                    {formatPercentage(
                      ((adminSummary.tokens?.input || adminUsage.input_tokens || 0) / 
                       (adminSummary.tokens?.total || adminUsage.total_tokens || 1)) * 100
                    )})
                  </span>
                </div>
                <div className="flex justify-between items-center p-3 bg-surface-hover rounded-lg border border-border-default">
                  <span className="text-sm text-text-secondary">Output Tokens</span>
                  <span className="text-sm font-medium text-text-primary">
                    {formatNumber(adminSummary.tokens?.output || adminUsage.output_tokens || 0)} (
                    {formatPercentage(
                      ((adminSummary.tokens?.output || adminUsage.output_tokens || 0) / 
                       (adminSummary.tokens?.total || adminUsage.total_tokens || 1)) * 100
                    )})
                  </span>
                </div>
                <div className="flex justify-between items-center p-3 bg-surface-hover rounded-lg border border-border-default">
                  <span className="text-sm text-text-secondary">Avg Tokens per User</span>
                  <span className="text-sm font-medium text-text-primary">
                    {formatNumber(
                      (adminSummary.tokens?.total || adminUsage.total_tokens || 0) / (users.length || 1)
                    )}
                  </span>
                </div>
              </div>
            </div>
          </div>
        );

      case 'latency':
        return (
          <div className="space-y-6">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="bg-surface-hover rounded-xl p-4 border border-border-default">
                <h4 className="text-xs font-medium text-text-secondary mb-1">Avg Latency</h4>
                <p className="text-2xl font-bold text-text-primary">
                  {formatLatency(adminSummary.latency?.average)}
                </p>
              </div>
              <div className="bg-surface-hover rounded-xl p-4 border border-border-default">
                <h4 className="text-xs font-medium text-text-secondary mb-1">Min Latency</h4>
                <p className="text-2xl font-bold text-text-primary">
                  {formatLatency(adminSummary.latency?.min)}
                </p>
              </div>
              <div className="bg-surface-hover rounded-xl p-4 border border-border-default">
                <h4 className="text-xs font-medium text-text-secondary mb-1">Max Latency</h4>
                <p className="text-2xl font-bold text-text-primary">
                  {formatLatency(adminSummary.latency?.max)}
                </p>
              </div>
              <div className="bg-surface-hover rounded-xl p-4 border border-border-default">
                <h4 className="text-xs font-medium text-text-secondary mb-1">P95 Latency</h4>
                <p className="text-2xl font-bold text-text-primary">
                  {formatLatency(adminSummary.latency?.p95)}
                </p>
              </div>
            </div>
            <div className="bg-accent-blue/10 rounded-xl p-4 border border-accent-blue/20">
              <h3 className="text-sm font-semibold text-text-primary mb-2">Highest User</h3>
              <p className="text-sm text-text-secondary">Per-user latency breakdown not available in current metrics</p>
            </div>
            <div>
              <h3 className="text-sm font-semibold text-text-primary mb-3">Latency Statistics</h3>
              <div className="space-y-2">
                <div className="flex justify-between items-center p-3 bg-surface-hover rounded-lg border border-border-default">
                  <span className="text-sm text-text-secondary">Total Calls</span>
                  <span className="text-sm font-medium text-text-primary">
                    {formatNumber(adminSummary.llm_calls?.total || adminUsage.total_calls || 0)}
                  </span>
                </div>
                <div className="flex justify-between items-center p-3 bg-surface-hover rounded-lg border border-border-default">
                  <span className="text-sm text-text-secondary">Average Response Time</span>
                  <span className="text-sm font-medium text-text-primary">
                    {formatLatency(adminSummary.latency?.average)}
                  </span>
                </div>
              </div>
            </div>
          </div>
        );

      case 'alerts':
        // Find user with most alerts if available
        const alertsByUser: { [key: string]: number } = {};
        if (alerts?.recent_alerts) {
          alerts.recent_alerts.forEach((alert: any) => {
            const userId = alert.user_id || 'unknown';
            alertsByUser[userId] = (alertsByUser[userId] || 0) + 1;
          });
        }
        const highestAlertUser = Object.keys(alertsByUser).length > 0
          ? Object.entries(alertsByUser).sort((a, b) => b[1] - a[1])[0]
          : null;
        const highestAlertUserInfo = highestAlertUser ? getUserInfo(highestAlertUser[0]) : null;
        
        return (
          <div className="space-y-6">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="bg-surface-hover rounded-xl p-4 border border-border-default">
                <h4 className="text-xs font-medium text-text-secondary mb-1">Active Alerts</h4>
                <p className="text-2xl font-bold text-text-primary">
                  {formatNumber(alerts?.status?.active_alerts || 0)}
                </p>
              </div>
              <div className="bg-surface-hover rounded-xl p-4 border border-border-default">
                <h4 className="text-xs font-medium text-text-secondary mb-1">Total Alerts</h4>
                <p className="text-2xl font-bold text-text-primary">
                  {formatNumber(alerts?.status?.total_alerts || 0)}
                </p>
              </div>
              <div className="bg-surface-hover rounded-xl p-4 border border-border-default">
                <h4 className="text-xs font-medium text-text-secondary mb-1">Resolved</h4>
                <p className="text-2xl font-bold text-text-primary">
                  {formatNumber(alerts?.status?.resolved_alerts || 0)}
                </p>
              </div>
              <div className="bg-surface-hover rounded-xl p-4 border border-border-default">
                <h4 className="text-xs font-medium text-text-secondary mb-1">By Severity</h4>
                <p className="text-2xl font-bold text-text-primary">
                  {formatNumber(Object.keys(alerts?.status?.by_severity || {}).length)}
                </p>
              </div>
            </div>
            {highestAlertUserInfo && highestAlertUser && (
              <div className="bg-accent-blue/10 rounded-xl p-4 border border-accent-blue/20">
                <h3 className="text-sm font-semibold text-text-primary mb-2">Highest User</h3>
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-base font-medium text-text-primary">{highestAlertUserInfo.email}</p>
                    <p className="text-xs text-text-secondary mt-1">{highestAlertUserInfo.name}</p>
                  </div>
                  <div className="text-right">
                    <p className="text-lg font-bold text-accent-blue">{formatNumber(highestAlertUser[1])} alerts</p>
                  </div>
                </div>
              </div>
            )}
            {alerts?.recent_alerts && alerts.recent_alerts.length > 0 && (
              <div>
                <h3 className="text-sm font-semibold text-text-primary mb-3">Recent Alerts</h3>
                <div className="space-y-2 max-h-96 overflow-y-auto">
                  {alerts.recent_alerts.slice(0, 10).map((alert: any, idx: number) => (
                    <div key={idx} className="p-3 bg-surface-hover rounded-lg border border-border-default">
                      <div className="flex justify-between items-start">
                        <div className="flex-1">
                          <p className="text-sm font-medium text-text-primary">{alert.type || 'Alert'}</p>
                          <p className="text-xs text-text-secondary mt-1">{alert.message || alert.description || '—'}</p>
                          <p className="text-xs text-text-tertiary mt-1">
                            {alert.timestamp ? new Date(alert.timestamp).toLocaleString() : '—'}
                          </p>
                        </div>
                        <span className={`text-xs font-medium px-2 py-1 rounded ${
                          alert.severity === 'critical' ? 'bg-red-500/20 text-red-500' :
                          alert.severity === 'warning' ? 'bg-yellow-500/20 text-yellow-500' :
                          'bg-blue-500/20 text-blue-500'
                        }`}>
                          {alert.severity || 'info'}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        );

      case 'errors':
        return (
          <div className="space-y-6">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="bg-surface-hover rounded-xl p-4 border border-border-default">
                <h4 className="text-xs font-medium text-text-secondary mb-1">Error Rate</h4>
                <p className="text-2xl font-bold text-text-primary">
                  {formatPercentage(
                    adminSummary.llm_calls?.failed && adminSummary.llm_calls?.total
                      ? (adminSummary.llm_calls.failed / adminSummary.llm_calls.total) * 100
                      : 0
                  )}
                </p>
              </div>
              <div className="bg-surface-hover rounded-xl p-4 border border-border-default">
                <h4 className="text-xs font-medium text-text-secondary mb-1">Failed Calls</h4>
                <p className="text-2xl font-bold text-text-primary">
                  {formatNumber(adminSummary.llm_calls?.failed || adminUsage.failed_calls || 0)}
                </p>
              </div>
              <div className="bg-surface-hover rounded-xl p-4 border border-border-default">
                <h4 className="text-xs font-medium text-text-secondary mb-1">Successful Calls</h4>
                <p className="text-2xl font-bold text-text-primary">
                  {formatNumber(adminSummary.llm_calls?.successful || adminUsage.successful_calls || 0)}
                </p>
              </div>
              <div className="bg-surface-hover rounded-xl p-4 border border-border-default">
                <h4 className="text-xs font-medium text-text-secondary mb-1">Success Rate</h4>
                <p className="text-2xl font-bold text-text-primary">
                  {formatPercentage(
                    ((adminSummary.llm_calls?.successful || adminUsage.successful_calls || 0) / 
                     (adminSummary.llm_calls?.total || adminUsage.total_calls || 1)) * 100
                  )}
                </p>
              </div>
            </div>
            <div>
              <h3 className="text-sm font-semibold text-text-primary mb-3">Error Statistics</h3>
              <div className="space-y-2">
                <div className="flex justify-between items-center p-3 bg-surface-hover rounded-lg border border-border-default">
                  <span className="text-sm text-text-secondary">Total Calls</span>
                  <span className="text-sm font-medium text-text-primary">
                    {formatNumber(adminSummary.llm_calls?.total || adminUsage.total_calls || 0)}
                  </span>
                </div>
                <div className="flex justify-between items-center p-3 bg-surface-hover rounded-lg border border-border-default">
                  <span className="text-sm text-text-secondary">Failed Calls</span>
                  <span className="text-sm font-medium text-text-primary">
                    {formatNumber(adminSummary.llm_calls?.failed || adminUsage.failed_calls || 0)}
                  </span>
                </div>
                <div className="flex justify-between items-center p-3 bg-surface-hover rounded-lg border border-border-default">
                  <span className="text-sm text-text-secondary">Success Rate</span>
                  <span className="text-sm font-medium text-text-primary">
                    {formatPercentage(
                      ((adminSummary.llm_calls?.successful || adminUsage.successful_calls || 0) / 
                       (adminSummary.llm_calls?.total || adminUsage.total_calls || 1)) * 100
                    )}
                  </span>
                </div>
              </div>
            </div>
          </div>
        );

      case 'guardrails':
        return (
          <div className="space-y-6">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="bg-surface-hover rounded-xl p-4 border border-border-default">
                <h4 className="text-xs font-medium text-text-secondary mb-1">Total Blocks</h4>
                <p className="text-2xl font-bold text-text-primary">
                  {formatNumber(adminMetrics?.guardrails?.blocks || 0)}
                </p>
              </div>
              <div className="bg-surface-hover rounded-xl p-4 border border-border-default">
                <h4 className="text-xs font-medium text-text-secondary mb-1">Block Rate</h4>
                <p className="text-2xl font-bold text-text-primary">
                  {formatPercentage(
                    (adminMetrics?.guardrails?.blocks || 0) / 
                    (adminSummary.llm_calls?.total || adminUsage.total_calls || 1) * 100
                  )}
                </p>
              </div>
            </div>
            <div className="bg-accent-blue/10 rounded-xl p-4 border border-accent-blue/20">
              <h3 className="text-sm font-semibold text-text-primary mb-2">Highest User</h3>
              <p className="text-sm text-text-secondary">Per-user guardrail breakdown not available in current metrics</p>
            </div>
            <div>
              <h3 className="text-sm font-semibold text-text-primary mb-3">Guardrail Statistics</h3>
              <div className="space-y-2">
                <div className="flex justify-between items-center p-3 bg-surface-hover rounded-lg border border-border-default">
                  <span className="text-sm text-text-secondary">Total Requests</span>
                  <span className="text-sm font-medium text-text-primary">
                    {formatNumber(adminSummary.llm_calls?.total || adminUsage.total_calls || 0)}
                  </span>
                </div>
                <div className="flex justify-between items-center p-3 bg-surface-hover rounded-lg border border-border-default">
                  <span className="text-sm text-text-secondary">Blocked Requests</span>
                  <span className="text-sm font-medium text-text-primary">
                    {formatNumber(adminMetrics?.guardrails?.blocks || 0)}
                  </span>
                </div>
                <div className="flex justify-between items-center p-3 bg-surface-hover rounded-lg border border-border-default">
                  <span className="text-sm text-text-secondary">Allowed Requests</span>
                  <span className="text-sm font-medium text-text-primary">
                    {formatNumber(
                      (adminSummary.llm_calls?.total || adminUsage.total_calls || 0) - 
                      (adminMetrics?.guardrails?.blocks || 0)
                    )}
                  </span>
                </div>
              </div>
            </div>
          </div>
        );

      case 'rag_quality':
        const ragSummary = ragQualityData?.summary || {};
        const ragDailyBreakdown = ragQualityData?.daily_breakdown || [];
        return (
          <div className="space-y-6">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="bg-surface-hover rounded-xl p-4 border border-border-default">
                <h4 className="text-xs font-medium text-text-secondary mb-1">Total Feedback</h4>
                <p className="text-2xl font-bold text-text-primary">
                  {formatNumber(ragSummary.total_feedback || 0)}
                </p>
              </div>
              <div className="bg-surface-hover rounded-xl p-4 border border-border-default">
                <h4 className="text-xs font-medium text-text-secondary mb-1">Thumbs Up</h4>
                <p className="text-2xl font-bold text-text-primary">
                  {formatNumber(ragSummary.thumbs_up || 0)}
                </p>
              </div>
              <div className="bg-surface-hover rounded-xl p-4 border border-border-default">
                <h4 className="text-xs font-medium text-text-secondary mb-1">Thumbs Down</h4>
                <p className="text-2xl font-bold text-text-primary">
                  {formatNumber(ragSummary.thumbs_down || 0)}
                </p>
              </div>
              <div className="bg-surface-hover rounded-xl p-4 border border-border-default">
                <h4 className="text-xs font-medium text-text-secondary mb-1">Positive Rate</h4>
                <p className="text-2xl font-bold text-text-primary">
                  {formatPercentage(ragSummary.positive_rate || 0)}
                </p>
              </div>
            </div>
            <div>
              <h3 className="text-sm font-semibold text-text-primary mb-3">RAG Quality Statistics</h3>
              <div className="space-y-2">
                <div className="flex justify-between items-center p-3 bg-surface-hover rounded-lg border border-border-default">
                  <span className="text-sm text-text-secondary">Total Feedback</span>
                  <span className="text-sm font-medium text-text-primary">
                    {formatNumber(ragSummary.total_feedback || 0)}
                  </span>
                </div>
                <div className="flex justify-between items-center p-3 bg-surface-hover rounded-lg border border-border-default">
                  <span className="text-sm text-text-secondary">Positive Feedback Rate</span>
                  <span className="text-sm font-medium text-text-primary">
                    {formatPercentage(ragSummary.positive_rate || 0)}
                  </span>
                </div>
                <div className="flex justify-between items-center p-3 bg-surface-hover rounded-lg border border-border-default">
                  <span className="text-sm text-text-secondary">Hallucination Rate</span>
                  <span className="text-sm font-medium text-text-primary">
                    {formatPercentage(ragSummary.hallucination_rate || 0)}
                  </span>
                </div>
              </div>
            </div>
            {ragDailyBreakdown.length > 0 && (
              <div>
                <h3 className="text-sm font-semibold text-text-primary mb-3">Daily Breakdown</h3>
                <div className="space-y-2 max-h-96 overflow-y-auto">
                  {ragDailyBreakdown.slice(0, 10).map((item: any, idx: number) => (
                    <div key={idx} className="p-3 bg-surface-hover rounded-lg border border-border-default">
                      <div className="flex justify-between items-center">
                        <span className="text-sm text-text-primary">
                          {new Date(item.date).toLocaleDateString('en-US', { 
                            year: 'numeric', 
                            month: 'short', 
                            day: 'numeric' 
                          })}
                        </span>
                        <div className="flex gap-4">
                          <span className="text-sm text-green-500">↑ {formatNumber(item.thumbs_up || 0)}</span>
                          <span className="text-sm text-red-500">↓ {formatNumber(item.thumbs_down || 0)}</span>
                          <span className="text-sm text-text-secondary">{formatPercentage(item.hallucination_rate || 0)}</span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        );

      default:
        return <div className="text-text-secondary">No details available</div>;
    }
  };

  const getTitle = () => {
    switch (metricType) {
      case 'cost': return 'Cost Details';
      case 'users': return 'Users Details';
      case 'queries': return 'Queries Details';
      case 'tokens': return 'Tokens Details';
      case 'latency': return 'Latency Details';
      case 'alerts': return 'Alerts Details';
      case 'errors': return 'Error Rate Details';
      case 'guardrails': return 'Guardrail Blocks Details';
      case 'rag_quality': return 'RAG Quality Details';
      default: return 'Metric Details';
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50" onClick={onClose}>
      <div
        className="bg-modal border border-border-default rounded-2xl shadow-xl max-w-4xl w-full max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="sticky top-0 bg-modal border-b border-border-default px-6 py-4 flex items-center justify-between">
          <h2 className="text-xl font-semibold text-text-primary">{getTitle()}</h2>
          <button
            onClick={onClose}
            className="p-2 rounded-lg hover:bg-surface-hover transition-colors text-text-secondary hover:text-text-primary"
            aria-label="Close"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
        <div className="p-6">
          {getModalContent()}
        </div>
      </div>
    </div>
  );
}

// Metric Detail Modal Component
interface MetricDetailModalProps {
  metricType: string;
  summary: any;
  usage: any;
  alerts?: any;
  onClose: () => void;
}

function MetricDetailModal({ metricType, summary, usage, alerts, onClose }: MetricDetailModalProps) {
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
    switch (metricType) {
      case 'tokens':
        return (
          <div className="space-y-6">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="bg-surface-hover rounded-xl p-4 border border-border-default">
                <h4 className="text-xs font-medium text-text-secondary mb-1">Total Tokens</h4>
                <p className="text-2xl font-bold text-text-primary">
                  {formatNumber(summary.tokens?.total || usage.total_tokens)}
                </p>
              </div>
              <div className="bg-surface-hover rounded-xl p-4 border border-border-default">
                <h4 className="text-xs font-medium text-text-secondary mb-1">Input Tokens</h4>
                <p className="text-2xl font-bold text-text-primary">
                  {formatNumber(summary.tokens?.input || usage.input_tokens)}
                </p>
              </div>
              <div className="bg-surface-hover rounded-xl p-4 border border-border-default">
                <h4 className="text-xs font-medium text-text-secondary mb-1">Output Tokens</h4>
                <p className="text-2xl font-bold text-text-primary">
                  {formatNumber(summary.tokens?.output || usage.output_tokens)}
                </p>
              </div>
              <div className="bg-surface-hover rounded-xl p-4 border border-border-default">
                <h4 className="text-xs font-medium text-text-secondary mb-1">Avg Tokens/Call</h4>
                <p className="text-2xl font-bold text-text-primary">
                  {formatNumber(
                    (summary.tokens?.total || usage.total_tokens) / (summary.llm_calls?.total || usage.total_calls || 1)
                  )}
                </p>
              </div>
            </div>
            <div>
              <h3 className="text-sm font-semibold text-text-primary mb-3">Token Breakdown</h3>
              <div className="space-y-2">
                <div className="flex justify-between items-center p-3 bg-surface-hover rounded-lg border border-border-default">
                  <span className="text-sm text-text-secondary">Input Tokens</span>
                  <span className="text-sm font-medium text-text-primary">
                    {formatNumber(summary.tokens?.input || usage.input_tokens)} (
                    {formatPercentage(
                      ((summary.tokens?.input || usage.input_tokens) / (summary.tokens?.total || usage.total_tokens || 1)) * 100
                    )})
                  </span>
                </div>
                <div className="flex justify-between items-center p-3 bg-surface-hover rounded-lg border border-border-default">
                  <span className="text-sm text-text-secondary">Output Tokens</span>
                  <span className="text-sm font-medium text-text-primary">
                    {formatNumber(summary.tokens?.output || usage.output_tokens)} (
                    {formatPercentage(
                      ((summary.tokens?.output || usage.output_tokens) / (summary.tokens?.total || usage.total_tokens || 1)) * 100
                    )})
                  </span>
                </div>
              </div>
            </div>
          </div>
        );

      case 'cost':
        return (
          <div className="space-y-6">
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
              <div className="bg-surface-hover rounded-xl p-4 border border-border-default">
                <h4 className="text-xs font-medium text-text-secondary mb-1">Total Cost</h4>
                <p className="text-2xl font-bold text-text-primary">
                  {formatCurrency(summary.costs?.total || usage.total_cost)}
                </p>
              </div>
              <div className="bg-surface-hover rounded-xl p-4 border border-border-default">
                <h4 className="text-xs font-medium text-text-secondary mb-1">Input Cost</h4>
                <p className="text-2xl font-bold text-text-primary">
                  {formatCurrency(summary.costs?.input || usage.input_cost)}
                </p>
              </div>
              <div className="bg-surface-hover rounded-xl p-4 border border-border-default">
                <h4 className="text-xs font-medium text-text-secondary mb-1">Output Cost</h4>
                <p className="text-2xl font-bold text-text-primary">
                  {formatCurrency(summary.costs?.output || usage.output_cost)}
                </p>
              </div>
            </div>
            <div>
              <h3 className="text-sm font-semibold text-text-primary mb-3">Cost Breakdown</h3>
              <div className="space-y-2">
                <div className="flex justify-between items-center p-3 bg-surface-hover rounded-lg border border-border-default">
                  <span className="text-sm text-text-secondary">Input Cost</span>
                  <span className="text-sm font-medium text-text-primary">
                    {formatCurrency(summary.costs?.input || usage.input_cost)}
                  </span>
                </div>
                <div className="flex justify-between items-center p-3 bg-surface-hover rounded-lg border border-border-default">
                  <span className="text-sm text-text-secondary">Output Cost</span>
                  <span className="text-sm font-medium text-text-primary">
                    {formatCurrency(summary.costs?.output || usage.output_cost)}
                  </span>
                </div>
                <div className="flex justify-between items-center p-3 bg-surface-hover rounded-lg border border-border-default">
                  <span className="text-sm text-text-secondary">Avg Cost per Call</span>
                  <span className="text-sm font-medium text-text-primary">
                    {formatCurrency(
                      (summary.costs?.total || usage.total_cost) / (summary.llm_calls?.total || usage.total_calls || 1)
                    )}
                  </span>
                </div>
              </div>
            </div>
          </div>
        );

      case 'latency':
        return (
          <div className="space-y-6">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="bg-surface-hover rounded-xl p-4 border border-border-default">
                <h4 className="text-xs font-medium text-text-secondary mb-1">Avg Latency</h4>
                <p className="text-2xl font-bold text-text-primary">
                  {formatLatency(summary.latency?.average)}
                </p>
              </div>
              <div className="bg-surface-hover rounded-xl p-4 border border-border-default">
                <h4 className="text-xs font-medium text-text-secondary mb-1">Min Latency</h4>
                <p className="text-2xl font-bold text-text-primary">
                  {formatLatency(summary.latency?.min)}
                </p>
              </div>
              <div className="bg-surface-hover rounded-xl p-4 border border-border-default">
                <h4 className="text-xs font-medium text-text-secondary mb-1">Max Latency</h4>
                <p className="text-2xl font-bold text-text-primary">
                  {formatLatency(summary.latency?.max)}
                </p>
              </div>
              <div className="bg-surface-hover rounded-xl p-4 border border-border-default">
                <h4 className="text-xs font-medium text-text-secondary mb-1">P95 Latency</h4>
                <p className="text-2xl font-bold text-text-primary">
                  {formatLatency(summary.latency?.p95)}
                </p>
              </div>
            </div>
            <div>
              <h3 className="text-sm font-semibold text-text-primary mb-3">Latency Statistics</h3>
              <div className="space-y-2">
                <div className="flex justify-between items-center p-3 bg-surface-hover rounded-lg border border-border-default">
                  <span className="text-sm text-text-secondary">Total Calls</span>
                  <span className="text-sm font-medium text-text-primary">
                    {formatNumber(summary.llm_calls?.total || usage.total_calls)}
                  </span>
                </div>
                <div className="flex justify-between items-center p-3 bg-surface-hover rounded-lg border border-border-default">
                  <span className="text-sm text-text-secondary">Average Response Time</span>
                  <span className="text-sm font-medium text-text-primary">
                    {formatLatency(summary.latency?.average)}
                  </span>
                </div>
              </div>
            </div>
          </div>
        );

      case 'cache':
        return (
          <div className="space-y-6">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="bg-surface-hover rounded-xl p-4 border border-border-default">
                <h4 className="text-xs font-medium text-text-secondary mb-1">Cache Hit Rate</h4>
                <p className="text-2xl font-bold text-text-primary">
                  {formatPercentage(
                    summary.cache?.hit_rate != null ? summary.cache.hit_rate * 100 : undefined
                  )}
                </p>
              </div>
              <div className="bg-surface-hover rounded-xl p-4 border border-border-default">
                <h4 className="text-xs font-medium text-text-secondary mb-1">Cache Hits</h4>
                <p className="text-2xl font-bold text-text-primary">
                  {formatNumber(summary.cache?.hits)}
                </p>
              </div>
              <div className="bg-surface-hover rounded-xl p-4 border border-border-default">
                <h4 className="text-xs font-medium text-text-secondary mb-1">Cache Misses</h4>
                <p className="text-2xl font-bold text-text-primary">
                  {formatNumber(summary.cache?.misses)}
                </p>
              </div>
              <div className="bg-surface-hover rounded-xl p-4 border border-border-default">
                <h4 className="text-xs font-medium text-text-secondary mb-1">Total Requests</h4>
                <p className="text-2xl font-bold text-text-primary">
                  {formatNumber((summary.cache?.hits || 0) + (summary.cache?.misses || 0))}
                </p>
              </div>
            </div>
            <div>
              <h3 className="text-sm font-semibold text-text-primary mb-3">Cache Performance</h3>
              <div className="space-y-2">
                <div className="flex justify-between items-center p-3 bg-surface-hover rounded-lg border border-border-default">
                  <span className="text-sm text-text-secondary">Cache Hits</span>
                  <span className="text-sm font-medium text-text-primary">
                    {formatNumber(summary.cache?.hits)} (
                    {formatPercentage(
                      ((summary.cache?.hits || 0) / ((summary.cache?.hits || 0) + (summary.cache?.misses || 0) || 1)) * 100
                    )})
                  </span>
                </div>
                <div className="flex justify-between items-center p-3 bg-surface-hover rounded-lg border border-border-default">
                  <span className="text-sm text-text-secondary">Cache Misses</span>
                  <span className="text-sm font-medium text-text-primary">
                    {formatNumber(summary.cache?.misses)} (
                    {formatPercentage(
                      ((summary.cache?.misses || 0) / ((summary.cache?.hits || 0) + (summary.cache?.misses || 0) || 1)) * 100
                    )})
                  </span>
                </div>
              </div>
            </div>
          </div>
        );

      case 'calls':
        return (
          <div className="space-y-6">
            <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
              <div className="bg-surface-hover rounded-xl p-4 border border-border-default">
                <h4 className="text-xs font-medium text-text-secondary mb-1">Total Calls</h4>
                <p className="text-2xl font-bold text-text-primary">
                  {formatNumber(summary.llm_calls?.total || usage.total_calls)}
                </p>
              </div>
              <div className="bg-surface-hover rounded-xl p-4 border border-border-default">
                <h4 className="text-xs font-medium text-text-secondary mb-1">Successful Calls</h4>
                <p className="text-2xl font-bold text-text-primary">
                  {formatNumber(summary.llm_calls?.successful || usage.successful_calls)}
                </p>
              </div>
              <div className="bg-surface-hover rounded-xl p-4 border border-border-default">
                <h4 className="text-xs font-medium text-text-secondary mb-1">Failed Calls</h4>
                <p className="text-2xl font-bold text-text-primary">
                  {formatNumber(summary.llm_calls?.failed || usage.failed_calls)}
                </p>
              </div>
            </div>
            <div>
              <h3 className="text-sm font-semibold text-text-primary mb-3">Call Statistics</h3>
              <div className="space-y-2">
                <div className="flex justify-between items-center p-3 bg-surface-hover rounded-lg border border-border-default">
                  <span className="text-sm text-text-secondary">Total API Calls</span>
                  <span className="text-sm font-medium text-text-primary">
                    {formatNumber(summary.llm_calls?.total || usage.total_calls)}
                  </span>
                </div>
                <div className="flex justify-between items-center p-3 bg-surface-hover rounded-lg border border-border-default">
                  <span className="text-sm text-text-secondary">Success Rate</span>
                  <span className="text-sm font-medium text-text-primary">
                    {formatPercentage(
                      ((summary.llm_calls?.successful || usage.successful_calls || 0) / (summary.llm_calls?.total || usage.total_calls || 1)) * 100
                    )}
                  </span>
                </div>
              </div>
            </div>
          </div>
        );

      case 'alerts':
        return (
          <div className="space-y-6">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="bg-surface-hover rounded-xl p-4 border border-border-default">
                <h4 className="text-xs font-medium text-text-secondary mb-1">Active Alerts</h4>
                <p className="text-2xl font-bold text-text-primary">
                  {formatNumber(alerts?.status?.active_alerts || 0)}
                </p>
              </div>
              <div className="bg-surface-hover rounded-xl p-4 border border-border-default">
                <h4 className="text-xs font-medium text-text-secondary mb-1">Total Alerts</h4>
                <p className="text-2xl font-bold text-text-primary">
                  {formatNumber(alerts?.status?.total_alerts || 0)}
                </p>
              </div>
              <div className="bg-surface-hover rounded-xl p-4 border border-border-default">
                <h4 className="text-xs font-medium text-text-secondary mb-1">Resolved</h4>
                <p className="text-2xl font-bold text-text-primary">
                  {formatNumber(alerts?.status?.resolved_alerts || 0)}
                </p>
              </div>
              <div className="bg-surface-hover rounded-xl p-4 border border-border-default">
                <h4 className="text-xs font-medium text-text-secondary mb-1">By Severity</h4>
                <p className="text-lg font-bold text-text-primary">
                  {Object.keys(alerts?.status?.by_severity || {}).length} types
                </p>
              </div>
            </div>
            {alerts?.recent_alerts && alerts.recent_alerts.length > 0 && (
              <div>
                <h3 className="text-sm font-semibold text-text-primary mb-3">Recent Alerts</h3>
                <div className="space-y-2 max-h-96 overflow-y-auto">
                  {alerts.recent_alerts.map((alert: any, idx: number) => (
                    <div key={idx} className="p-3 bg-surface-hover rounded-lg border border-border-default">
                      <div className="flex justify-between items-start">
                        <div className="flex-1">
                          <p className="text-sm font-medium text-text-primary">{alert.type || 'Alert'}</p>
                          <p className="text-xs text-text-secondary mt-1">{alert.message || alert.description}</p>
                          <p className="text-xs text-text-tertiary mt-1">
                            {alert.timestamp ? new Date(alert.timestamp).toLocaleString() : '—'}
                          </p>
                        </div>
                        <span className={`text-xs font-medium px-2 py-1 rounded ${
                          alert.severity === 'critical' ? 'bg-red-500/20 text-red-500' :
                          alert.severity === 'warning' ? 'bg-yellow-500/20 text-yellow-500' :
                          'bg-blue-500/20 text-blue-500'
                        }`}>
                          {alert.severity || 'info'}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        );

      default:
        return <div className="text-text-secondary">No details available</div>;
    }
  };

  const getTitle = () => {
    switch (metricType) {
      case 'tokens': return 'Token Details';
      case 'cost': return 'Cost Details';
      case 'latency': return 'Latency Details';
      case 'cache': return 'Cache Performance';
      case 'calls': return 'API Call Details';
      case 'alerts': return 'Alerts Details';
      default: return 'Metric Details';
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/50" onClick={onClose}>
      <div
        className="bg-modal border border-border-default rounded-2xl shadow-xl max-w-4xl w-full max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="sticky top-0 bg-modal border-b border-border-default px-6 py-4 flex items-center justify-between">
          <h2 className="text-xl font-semibold text-text-primary">{getTitle()}</h2>
          <button
            onClick={onClose}
            className="p-2 rounded-lg hover:bg-surface-hover transition-colors text-text-secondary hover:text-text-primary"
            aria-label="Close"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
        <div className="p-6">
          {getModalContent()}
        </div>
      </div>
    </div>
  );
}

export default function AnalyticsDashboardPage() {
  const { getToken } = useAuth();
  const [mounted, setMounted] = useState(false);
  const [authLoaded, setAuthLoaded] = useState(false);
  const [isAdmin, setIsAdmin] = useState<boolean | null>(null);
  const [myMetrics, setMyMetrics] = useState<any>(null);
  const [adminMetrics, setAdminMetrics] = useState<any>(null);
  const [users, setUsers] = useState<any[]>([]);
  const [alerts, setAlerts] = useState<any>(null);
  const [tokenConsumption, setTokenConsumption] = useState<any>(null);
  const [costTracking, setCostTracking] = useState<any>(null);
  const [latencyData, setLatencyData] = useState<any>(null);
  const [recentQueries, setRecentQueries] = useState<any[]>([]);
  const [userBreakdown, setUserBreakdown] = useState<any>(null);
  const [ragQualityData, setRagQualityData] = useState<any>(null);
  const [loading, setLoading] = useState(false);
  const [adminLoading, setAdminLoading] = useState(false);
  const [adminError, setAdminError] = useState<string | null>(null);
  const [selectedMetric, setSelectedMetric] = useState<string | null>(null);
  const [selectedAdminMetric, setSelectedAdminMetric] = useState<string | null>(null);

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

  // Fetch alerts status
  const fetchAlerts = useCallback(async () => {
    if (!getToken) return;
    
    try {
      apiClient.setTokenGetter(getToken);
      const alertsData = await apiClient.getAlertsStatus();
      setAlerts(alertsData);
    } catch (error: any) {
      console.error('[ANALYTICS] Failed to fetch alerts:', error);
    }
  }, [getToken]);

  // Fetch admin aggregate metrics
  const fetchAdminMetrics = useCallback(async () => {
    if (!getToken) return;
    
    setAdminLoading(true);
    setAdminError(null);
    try {
      apiClient.setTokenGetter(getToken);
      
      // Fetch main metrics first (critical)
      let metrics = null;
      try {
        metrics = await apiClient.getAggregateMetrics(30);
        setAdminMetrics(metrics);
      } catch (error: any) {
        console.error('[ANALYTICS] Failed to fetch main admin metrics:', error);
        // Check for connection errors
        const isConnectionError = 
          error?.code === 'ECONNREFUSED' || 
          error?.code === 'ERR_CONNECTION_REFUSED' ||
          error?.message?.includes('CONNECTION_REFUSED') ||
          error?.message?.includes('Network Error') ||
          (!error?.response && error?.request);
        
        if (isConnectionError) {
          setAdminError('Cannot connect to the backend server. Please ensure the API server is running on port 8000.');
        } else {
          setAdminError(error?.response?.data?.detail || error?.message || 'Failed to load admin metrics');
        }
        // Still try to load other data
      }
      
      // Fetch other data in parallel (non-critical, can fail individually)
      const [usersData, tokenData, costData, latencyDashboard, tokenDataByUser, costDataByUser, ragQualityData] = await Promise.all([
        apiClient.listAllUsers().catch((err) => {
          console.error('[ANALYTICS] Failed to fetch users:', err);
          return { users: [], total: 0 };
        }),
        apiClient.getTokenConsumption(30, 'feature').catch((err) => {
          console.error('[ANALYTICS] Failed to fetch token consumption:', err);
          return null;
        }),
        apiClient.getCostTracking(30, false).catch((err) => {
          console.error('[ANALYTICS] Failed to fetch cost tracking:', err);
          return null;
        }),
        apiClient.getLatencyDashboard(30).catch((err) => {
          console.error('[ANALYTICS] Failed to fetch latency dashboard:', err);
          return null;
        }),
        (async () => {
          // Calculate days from 1st of current month to today for monthly reset
          const now = new Date();
          const firstOfMonth = new Date(now.getFullYear(), now.getMonth(), 1);
          const daysFromFirstOfMonth = Math.ceil((now.getTime() - firstOfMonth.getTime()) / (1000 * 60 * 60 * 24));
          const daysToFetch = Math.max(1, daysFromFirstOfMonth); // At least 1 day
          return apiClient.getTokenConsumption(daysToFetch, 'user').catch((err) => {
            console.error('[ANALYTICS] Failed to fetch token consumption by user:', err);
            return null;
          });
        })(),
        apiClient.getCostTracking(30, true).catch((err) => {
          console.error('[ANALYTICS] Failed to fetch cost tracking by user:', err);
          return null;
        }),
        apiClient.getRagQuality(30).catch((err) => {
          console.error('[ANALYTICS] Failed to fetch RAG quality:', err);
          return null;
        }),
      ]);
      
      setUsers(usersData.users || []);
      setTokenConsumption(tokenData);
      setCostTracking(costData);
      setLatencyData(latencyDashboard);
      
      // Store user breakdown data
      setUserBreakdown({
        tokens: tokenDataByUser,
        cost: costDataByUser,
      });
      
      // Store RAG quality data
      setRagQualityData(ragQualityData);
      
      // Extract recent queries from metrics if available
      if (metrics?.recent_queries) {
        setRecentQueries(metrics.recent_queries);
      } else if (metrics?.queries?.recent) {
        setRecentQueries(metrics.queries.recent);
      }
      
      // If we got metrics, clear any previous errors
      if (metrics) {
        setAdminError(null);
      }
    } catch (error: any) {
      console.error('[ANALYTICS] Unexpected error fetching admin metrics:', error);
      // Set error if main metrics failed
      setAdminError(error?.response?.data?.detail || error?.message || 'Failed to load admin metrics');
    } finally {
      setAdminLoading(false);
    }
  }, [getToken]);

  // Fetch individual user metrics
  const fetchMyMetrics = useCallback(async () => {
    if (!getToken) return;
    
    setLoading(true);
    try {
      apiClient.setTokenGetter(getToken);
      const metrics = await apiClient.getMyMetrics(30);
      // Metrics fetched
      setMyMetrics(metrics);
    } catch (error: any) {
      console.error('[ANALYTICS] Failed to fetch user metrics:', error);
      console.error('[ANALYTICS] Error details:', error?.response?.data || error?.message);
    } finally {
      setLoading(false);
    }
  }, [getToken]);

  // Check if user is admin and fetch appropriate data
  useEffect(() => {
    const checkAdminAndFetchData = async () => {
      if (!authLoaded || !getToken) {
        return;
      }

      // Ensure token getter is set in API client
      apiClient.setTokenGetter(getToken);

      // Wait a bit for token to be fetched and verify it's available
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      // Try to get token to ensure it's ready
      try {
        const token = await getToken();
        if (!token) {
          console.warn('[ANALYTICS] Token not available yet');
          return;
        }
      } catch (tokenError) {
        console.warn('[ANALYTICS] Error getting token:', tokenError);
        return;
      }

      // Check if admin
      try {
        await apiClient.getAggregateMetrics(30, true);
        // Admin check succeeded - user is admin
        setIsAdmin(true);
        // Fetch admin data (errors will be handled by fetchAdminMetrics)
        await fetchAdminMetrics();
        await fetchAlerts();
      } catch (error: any) {
        if (error?.response?.status === 403) {
          // Not admin - fetch individual user metrics
          setIsAdmin(false);
          await fetchMyMetrics();
          await fetchAlerts();
        } else if (error?.response?.status === 401) {
          // Token issue - might need more time
          setTimeout(async () => {
            try {
              await apiClient.getAggregateMetrics(30, true);
              setIsAdmin(true);
              await fetchAdminMetrics();
              await fetchAlerts();
            } catch (retryError: any) {
              if (retryError?.response?.status === 403) {
                setIsAdmin(false);
                await fetchMyMetrics();
                await fetchAlerts();
              } else {
                // Other error - still might be admin, but data fetch failed
                setIsAdmin(true);
                setAdminError('Failed to verify admin status. Please refresh the page.');
              }
            }
          }, 2000);
        } else {
          // Network or other error - don't assume not admin
          // Could be a temporary issue, so we'll show an error state
          console.error('[ANALYTICS] Error checking admin status:', error);
          
          // Check for connection errors
          const isConnectionError = 
            error?.code === 'ECONNREFUSED' || 
            error?.code === 'ERR_CONNECTION_REFUSED' ||
            error?.message?.includes('CONNECTION_REFUSED') ||
            error?.message?.includes('Network Error') ||
            (!error?.response && error?.request);
          
          if (isConnectionError) {
            // Connection error - set admin to true but show error
            setIsAdmin(true);
            setAdminError('Cannot connect to the backend server. Please ensure the API server is running on port 8000.');
          } else {
            // Other error - don't set isAdmin to false
            // The user might still be admin, just having connection issues
          }
        }
      }
    };

    if (mounted && authLoaded && getToken) {
      checkAdminAndFetchData();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mounted, authLoaded, getToken, fetchAdminMetrics, fetchAlerts, fetchMyMetrics]);

  // Show loading
  if (isAdmin === null || (isAdmin === false && !myMetrics && loading) || (isAdmin === true && !adminMetrics && adminLoading && !adminError)) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-accent-blue mx-auto mb-4"></div>
          <p className="text-text-secondary">Loading...</p>
        </div>
      </div>
    );
  }

  // Show error state for admin dashboard
  if (isAdmin === true && adminError && !adminMetrics) {
    const isConnectionError = adminError.includes('Cannot connect to the backend server');
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-center max-w-md">
          <AlertTriangle className="w-12 h-12 text-yellow-500 mx-auto mb-4" />
          <h2 className="text-xl font-semibold text-text-primary mb-2">Failed to Load Dashboard</h2>
          <p className="text-text-secondary mb-4">{adminError}</p>
          {isConnectionError && (
            <div className="bg-surface-hover border border-border-default rounded-lg p-4 mb-4 text-left">
              <p className="text-sm font-medium text-text-primary mb-2">To start the backend server:</p>
              <ol className="text-xs text-text-secondary space-y-1 list-decimal list-inside">
                <li>Open a new terminal window</li>
                <li>Navigate to the project directory</li>
                <li>Run: <code className="bg-surface px-2 py-1 rounded">scripts\start_backend.bat</code> (Windows) or <code className="bg-surface px-2 py-1 rounded">./scripts/start_backend.sh</code> (Mac/Linux)</li>
                <li>Wait for the server to start on port 8000</li>
                <li>Then click Retry below</li>
              </ol>
            </div>
          )}
          <button
            onClick={() => {
              setAdminError(null);
              fetchAdminMetrics();
            }}
            className="px-4 py-2 rounded-lg bg-accent-blue text-white hover:bg-accent-blue/90 transition-colors"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  // Show admin dashboard
  if (isAdmin === true) {
    const adminSummary = adminMetrics?.metrics || {};
    const adminUsage = adminMetrics?.usage || {};
    // Get total users from users array length or from metrics
    const totalUsers = users.length > 0 ? users.length : (adminMetrics?.users?.total || 0);
    const errorRate = adminSummary.llm_calls?.failed && adminSummary.llm_calls?.total
      ? (adminSummary.llm_calls.failed / adminSummary.llm_calls.total) * 100
      : 0;
    const totalCost = adminSummary.costs?.total || adminUsage.total_cost || costTracking?.summary?.total_cost || 0;
    const totalAlerts = alerts?.status?.active_alerts || alerts?.status?.total_alerts || 0;
    
    // Debug logging removed for production
    
    return (
      <div className="h-full flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-semibold text-text-primary">Master Dashboard</h1>
            <p className="text-sm text-text-secondary mt-1">
              System-wide metrics and analytics
            </p>
          </div>
          <button
            onClick={() => {
              fetchAdminMetrics();
              fetchAlerts();
            }}
            disabled={adminLoading}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-surface-hover border border-border-default hover:bg-surface-hover/80 transition-colors disabled:opacity-50 disabled:cursor-not-allowed text-text-secondary hover:text-text-primary"
            title="Refresh metrics"
          >
            <span className="text-sm font-medium">Refresh</span>
          </button>
        </div>

        {/* Error banner if there's an error but we have partial data */}
        {adminError && adminMetrics && (
          <div className="mb-6 p-4 bg-yellow-500/10 border border-yellow-500/20 rounded-lg flex items-start gap-3">
            <AlertTriangle className="w-5 h-5 text-yellow-500 flex-shrink-0 mt-0.5" />
            <div className="flex-1">
              <p className="text-sm font-medium text-yellow-500 mb-1">Some data may be incomplete</p>
              <p className="text-xs text-text-secondary">{adminError}</p>
            </div>
            <button
              onClick={() => {
                setAdminError(null);
                fetchAdminMetrics();
              }}
              className="text-xs text-yellow-500 hover:text-yellow-400 underline"
            >
              Retry
            </button>
          </div>
        )}

        {/* KPI Cards Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-7 gap-4 mb-8">
          <KPICard
            title="Total Users"
            value={formatNumber(totalUsers)}
            icon={Users}
            subtext="Registered users"
          />
          <KPICard
            title="Total Cost"
            value={formatCurrency(totalCost)}
            trend={{
              value: 8.3,
              label: "vs last month"
            }}
            icon={DollarSign}
            subtext="Total spend"
            onClick={() => setSelectedAdminMetric('cost')}
          />
          <KPICard
            title="Total Tokens"
            value={formatNumber(adminSummary.tokens?.total || adminUsage.total_tokens || 0)}
            trend={{
              value: 8.3,
              label: "vs last month"
            }}
            icon={TrendingUp}
            subtext="Consumed"
            onClick={() => setSelectedAdminMetric('tokens')}
          />
          <KPICard
            title="Total Queries"
            value={formatNumber(adminSummary.llm_calls?.total || adminUsage.total_calls || 0)}
            trend={{
              value: 12.5,
              label: "vs last month"
            }}
            icon={Search}
            subtext="API calls"
            onClick={() => setSelectedAdminMetric('queries')}
          />
          <KPICard
            title="Avg Latency"
            value={formatLatency(adminSummary.latency?.average)}
            trend={{
              value: -3.1,
              label: "vs last month"
            }}
            icon={Clock}
            subtext="Response time"
            onClick={() => setSelectedAdminMetric('latency')}
          />
          <KPICard
            title="Total Alerts"
            value={formatNumber(totalAlerts)}
            icon={AlertCircle}
            subtext="Active alerts"
            onClick={() => setSelectedAdminMetric('alerts')}
          />
          <KPICard
            title="Guardrail Blocks"
            value={formatNumber(adminMetrics?.guardrails?.blocks || 0)}
            icon={Shield}
            subtext="Blocked requests"
            onClick={() => setSelectedAdminMetric('guardrails')}
          />
          <KPICard
            title="RAG Quality"
            value={(() => {
              // Calculate RAG quality from positive rate
              const summary = ragQualityData?.summary || {};
              const positiveRate = typeof summary.positive_rate === 'number' 
                ? summary.positive_rate 
                : typeof summary.positive_rate === 'string' 
                  ? parseFloat(summary.positive_rate) || 0 
                  : 0;
              const totalFeedback = typeof summary.total_feedback === 'number' 
                ? summary.total_feedback 
                : typeof summary.total_feedback === 'string' 
                  ? parseInt(summary.total_feedback) || 0 
                  : 0;
              
              console.log('[Overview] RAG Quality data:', { summary, positiveRate, totalFeedback });
              
              if (totalFeedback > 0) {
                // positiveRate is already 0-1, so multiply by 100
                return `${(positiveRate * 100).toFixed(1)}%`;
              }
              return '—';
            })()}
            icon={TrendingUp}
            subtext="Positive feedback rate"
            onClick={() => setSelectedAdminMetric('rag_quality')}
          />
        </div>

        {/* Session Overview Section */}
        <div className="mb-8">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-semibold text-text-primary">Session Overview</h2>
            <span className="text-xs text-text-tertiary bg-surface-hover px-2 py-1 rounded">
              Resets monthly (from 1st of current month)
            </span>
          </div>
          <div className="bg-surface rounded-2xl border border-border-default p-6">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Top 5 Users by Token Consumption */}
              <div>
                <h3 className="text-lg font-semibold text-text-primary mb-4">Top 5 Users (Highest Token Consumption)</h3>
                <div className="bg-surface-hover rounded-xl border border-border-default overflow-hidden">
                  <table className="w-full">
                    <thead className="bg-surface border-b border-border-default">
                      <tr>
                        <th className="px-4 py-3 text-left text-sm font-semibold text-text-primary">User</th>
                        <th className="px-4 py-3 text-right text-sm font-semibold text-text-primary">Tokens</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border-default">
                      {(() => {
                        // Get token consumption by user
                        const tokenBreakdown = userBreakdown?.tokens?.breakdown || [];
                        // Sort by total_tokens descending and take top 5
                        const topUsers = [...tokenBreakdown]
                          .sort((a: any, b: any) => (b.total_tokens || 0) - (a.total_tokens || 0))
                          .slice(0, 5);
                        
                        if (topUsers.length === 0) {
                          return (
                            <tr>
                              <td colSpan={2} className="px-4 py-8 text-center text-text-tertiary">
                                No token consumption data available
                              </td>
                            </tr>
                          );
                        }
                        
                        return topUsers.map((item: any, idx: number) => {
                          // Find user by ID (item.key is user_id)
                          const user = users.find((u: any) => u.id === item.key || u.clerk_user_id === item.key);
                          const userName = user 
                            ? (user.first_name && user.last_name 
                                ? `${user.first_name} ${user.last_name}` 
                                : user.email || user.username || 'Unknown User')
                            : item.key || 'Unknown User';
                          
                          return (
                            <tr key={idx}>
                              <td className="px-4 py-3 text-text-primary">
                                <div className="flex items-center gap-2">
                                  <span className="w-6 h-6 rounded-full bg-accent-blue/20 flex items-center justify-center text-xs font-semibold text-accent-blue">
                                    {idx + 1}
                                  </span>
                                  <span className="text-sm">{userName}</span>
                                </div>
                              </td>
                              <td className="px-4 py-3 text-right text-text-primary font-semibold">
                                {formatNumber(item.total_tokens || 0)}
                              </td>
                            </tr>
                          );
                        });
                      })()}
                    </tbody>
                  </table>
                </div>
              </div>

              {/* Bottom 5 Users by Token Consumption */}
              <div>
                <h3 className="text-lg font-semibold text-text-primary mb-4">Bottom 5 Users (Least Token Consumption)</h3>
                <div className="bg-surface-hover rounded-xl border border-border-default overflow-hidden">
                  <table className="w-full">
                    <thead className="bg-surface border-b border-border-default">
                      <tr>
                        <th className="px-4 py-3 text-left text-sm font-semibold text-text-primary">User</th>
                        <th className="px-4 py-3 text-right text-sm font-semibold text-text-primary">Tokens</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border-default">
                      {(() => {
                        // Get token consumption by user
                        const tokenBreakdown = userBreakdown?.tokens?.breakdown || [];
                        // Sort by total_tokens ascending and take bottom 5
                        const bottomUsers = [...tokenBreakdown]
                          .sort((a: any, b: any) => (a.total_tokens || 0) - (b.total_tokens || 0))
                          .slice(0, 5);
                        
                        if (bottomUsers.length === 0) {
                          return (
                            <tr>
                              <td colSpan={2} className="px-4 py-8 text-center text-text-tertiary">
                                No token consumption data available
                              </td>
                            </tr>
                          );
                        }
                        
                        return bottomUsers.map((item: any, idx: number) => {
                          // Find user by ID (item.key is user_id)
                          const user = users.find((u: any) => u.id === item.key || u.clerk_user_id === item.key);
                          const userName = user 
                            ? (user.first_name && user.last_name 
                                ? `${user.first_name} ${user.last_name}` 
                                : user.email || user.username || 'Unknown User')
                            : item.key || 'Unknown User';
                          
                          return (
                            <tr key={idx}>
                              <td className="px-4 py-3 text-text-primary">
                                <div className="flex items-center gap-2">
                                  <span className="w-6 h-6 rounded-full bg-accent-blue/20 flex items-center justify-center text-xs font-semibold text-accent-blue">
                                    {idx + 1}
                                  </span>
                                  <span className="text-sm">{userName}</span>
                                </div>
                              </td>
                              <td className="px-4 py-3 text-right text-text-primary font-semibold">
                                {formatNumber(item.total_tokens || 0)}
                              </td>
                            </tr>
                          );
                        });
                      })()}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Usage Charts Section */}
        <div className="mb-8">
          <h2 className="text-xl font-semibold text-text-primary mb-4">Usage Charts</h2>
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Token Consumption Chart */}
            <div className="bg-surface rounded-2xl border border-border-default p-6">
              <h3 className="text-lg font-semibold text-text-primary mb-4">Token Consumption Trend</h3>
              <div className="h-64">
                {(() => {
                  // Debug: log the token consumption data structure
                  // Token consumption chart data
                  
                  // Use actual backend data - check multiple possible structures
                  let chartData: any[] | null = null;
                  
                  // Check for daily_breakdown first
                  if (tokenConsumption?.daily_breakdown && Array.isArray(tokenConsumption.daily_breakdown)) {
                    if (tokenConsumption.daily_breakdown.length > 0) {
                      chartData = tokenConsumption.daily_breakdown;
                      // Found token data
                    }
                  }
                  
                  // Check for alternative data structures
                  if (!chartData) {
                    if (tokenConsumption?.trend && Array.isArray(tokenConsumption.trend) && tokenConsumption.trend.length > 0) {
                      chartData = tokenConsumption.trend;
                    } else if (tokenConsumption?.daily && Array.isArray(tokenConsumption.daily) && tokenConsumption.daily.length > 0) {
                      chartData = tokenConsumption.daily;
                    }
                  }
                  
                  if (chartData && Array.isArray(chartData) && chartData.length > 0) {
                    const valueKey = 'tokens';
                    return (
                      <Line
                        data={prepareChartData(
                          chartData,
                          valueKey,
                          'Total Tokens',
                          '#FBBC04'
                        )}
                        options={chartOptions}
                      />
                    );
                  }
                  
                  return (
                    <div className="h-full flex items-center justify-center text-text-tertiary">
                      No token data available
                    </div>
                  );
                })()}
              </div>
            </div>

            {/* Cost Trend Chart */}
            <div className="bg-surface rounded-2xl border border-border-default p-6">
              <h3 className="text-lg font-semibold text-text-primary mb-4">Cost Trend</h3>
              <div className="h-64">
                {(() => {
                  // Cost tracking chart data
                  
                  // Use actual backend data - check multiple possible structures
                  let chartData: any[] | null = null;
                  
                  // Check for daily_breakdown first
                  if (costTracking?.daily_breakdown && Array.isArray(costTracking.daily_breakdown)) {
                    if (costTracking.daily_breakdown.length > 0) {
                      chartData = costTracking.daily_breakdown;
                      // Found cost data
                    }
                  }
                  
                  // Check for alternative data structures
                  if (!chartData) {
                    if (costTracking?.trend && Array.isArray(costTracking.trend) && costTracking.trend.length > 0) {
                      chartData = costTracking.trend;
                    } else if (costTracking?.daily && Array.isArray(costTracking.daily) && costTracking.daily.length > 0) {
                      chartData = costTracking.daily;
                    }
                  }
                  
                  if (chartData && Array.isArray(chartData) && chartData.length > 0) {
                    const valueKey = 'cost';
                    return (
                      <Line
                        data={prepareChartData(
                          chartData,
                          valueKey,
                          'Total Cost ($)',
                          '#34A853'
                        )}
                        options={chartOptionsWithCurrency}
                      />
                    );
                  }
                  
                  return (
                    <div className="h-full flex items-center justify-center text-text-tertiary">
                      No cost data available
                    </div>
                  );
                })()}
              </div>
            </div>

            {/* Total Queries Trend Chart */}
            <div className="bg-surface rounded-2xl border border-border-default p-6">
              <h3 className="text-lg font-semibold text-text-primary mb-4">Total Queries Trend</h3>
              <div className="h-64">
                {(() => {
                  // Queries chart data
                  
                  // Use actual call counts from token consumption daily breakdown only
                  let chartData: any[] | null = null;
                  
                  if (tokenConsumption?.daily_breakdown && Array.isArray(tokenConsumption.daily_breakdown) && tokenConsumption.daily_breakdown.length > 0) {
                    // Check if daily_breakdown includes calls field (from updated API)
                    chartData = tokenConsumption.daily_breakdown
                      .filter((item: any) => item.calls !== undefined && item.calls !== null)
                      .map((item: any) => ({
                        date: item.date,
                        total: item.calls,
                      }));
                    
                    if (chartData.length > 0) {
                      // Using call counts from daily breakdown
                    } else {
                      chartData = null;
                    }
                  }
                  
                  if (chartData && chartData.length > 0) {
                    // Use chart options with integer ticks for queries
                    const queriesChartOptions = {
                      ...chartOptions,
                      scales: {
                        ...chartOptions.scales,
                        y: {
                          ...chartOptions.scales.y,
                          beginAtZero: true,
                          ticks: {
                            ...chartOptions.scales.y.ticks,
                            stepSize: 1,
                            callback: function(value: any) {
                              // For queries, always show whole numbers
                              if (typeof value === 'number') {
                                return Math.round(value).toString();
                              }
                              return value;
                            },
                          },
                        },
                      },
                    };
                    
                    return (
                      <Bar
                        data={prepareChartData(
                          chartData,
                          'total',
                          'Total Queries',
                          '#1A73E8'
                        )}
                        options={queriesChartOptions}
                      />
                    );
                  }
                  
                  return (
                    <div className="h-full flex items-center justify-center text-text-tertiary">
                      No query trend data available
                    </div>
                  );
                })()}
              </div>
            </div>

            {/* Alerts Trend Chart */}
            <div className="bg-surface rounded-2xl border border-border-default p-6">
              <h3 className="text-lg font-semibold text-text-primary mb-4">Alerts Trend</h3>
              <div className="h-64">
                {(() => {
                  // Alerts chart data
                  
                  let chartData: any[] = [];
                  
                  // Try to generate alerts trend from recent alerts (aggregate - all users)
                  if (alerts?.recent_alerts && alerts.recent_alerts.length > 0) {
                    const alertsByDate: { [key: string]: number } = {};
                    alerts.recent_alerts.forEach((alert: any) => {
                      if (alert.timestamp) {
                        const date = new Date(alert.timestamp);
                        const dateKey = date.toISOString().split('T')[0];
                        alertsByDate[dateKey] = (alertsByDate[dateKey] || 0) + 1;
                      }
                    });
                    chartData = Object.entries(alertsByDate)
                      .map(([date, count]) => ({ date, count }))
                      .sort((a, b) => a.date.localeCompare(b.date));
                    // Generated alerts from recent alerts
                  }
                  
                  if (chartData && chartData.length > 0) {
                    return (
                      <Bar
                        data={prepareChartData(
                          chartData,
                          'count',
                          'Alerts',
                          '#EA4335'
                        )}
                        options={chartOptions}
                      />
                    );
                  }
                  
                  return (
                    <div className="h-full flex items-center justify-center text-text-tertiary">
                      No alerts data available
                    </div>
                  );
                })()}
              </div>
            </div>
          </div>
        </div>

        {/* Latency Graph Section */}
        <div className="mb-8">
          <h2 className="text-xl font-semibold text-text-primary mb-4">Latency Performance</h2>
          <div className="bg-surface rounded-2xl border border-border-default p-6">
            <h3 className="text-lg font-semibold text-text-primary mb-4">Average Latency Over Time</h3>
            <div className="h-80">
              {(() => {
                // Latency chart data
                
                // Use actual backend data only - no synthetic data generation
                let chartData: any[] | null = 
                  (latencyData?.daily_breakdown && Array.isArray(latencyData.daily_breakdown) && latencyData.daily_breakdown.length > 0)
                    ? latencyData.daily_breakdown
                    : null;
                
                if (!chartData) {
                  // No latency data available
                }
                
                if (chartData && Array.isArray(chartData) && chartData.length > 0) {
                  // Determine the correct value key from the data structure
                  const valueKey = chartData[0]?.avg_latency_ms !== undefined ? 'avg_latency_ms' :
                                  chartData[0]?.average !== undefined ? 'average' :
                                  chartData[0]?.latency !== undefined ? 'latency' : 'average';
                  
                  // Using latency chart data
                  return (
                    <Line
                      data={prepareChartData(
                        chartData,
                        valueKey,
                        'Avg Latency (ms)',
                        '#EA4335'
                      )}
                      options={chartOptions}
                    />
                  );
                }
                
                return (
                  <div className="h-full flex items-center justify-center text-text-tertiary">
                    No latency data available
                  </div>
                );
              })()}
            </div>
          </div>
        </div>

        {/* Recent Activity Section */}
        <div className="mb-8">
          <h2 className="text-xl font-semibold text-text-primary mb-4">Recent Activity</h2>
          <div className="bg-surface rounded-2xl border border-border-default p-6">
            <h3 className="text-lg font-semibold text-text-primary mb-4">Last 10 Users by Login Time</h3>
            <div className="bg-surface-hover rounded-xl border border-border-default overflow-hidden">
              <table className="w-full">
                <thead className="bg-surface border-b border-border-default">
                  <tr>
                    <th className="px-4 py-3 text-left text-sm font-semibold text-text-primary">User</th>
                    <th className="px-4 py-3 text-left text-sm font-semibold text-text-primary">Email</th>
                    <th className="px-4 py-3 text-left text-sm font-semibold text-text-primary">Role</th>
                    <th className="px-4 py-3 text-right text-sm font-semibold text-text-primary">Last Login</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border-default">
                  {(() => {
                    // Sort users by last_sign_in_at (most recent first) and take top 10
                    const recentUsers = [...users]
                      .filter((u: any) => u.last_sign_in_at) // Only users who have logged in
                      .sort((a: any, b: any) => {
                        const timeA = a.last_sign_in_at ? new Date(a.last_sign_in_at).getTime() : 0;
                        const timeB = b.last_sign_in_at ? new Date(b.last_sign_in_at).getTime() : 0;
                        return timeB - timeA; // Most recent first
                      })
                      .slice(0, 10);
                    
                    if (recentUsers.length === 0) {
                      return (
                        <tr>
                          <td colSpan={4} className="px-4 py-8 text-center text-text-tertiary">
                            No recent login activity available
                          </td>
                        </tr>
                      );
                    }
                    
                    return recentUsers.map((user: any, idx: number) => {
                      const userName = user.first_name && user.last_name 
                        ? `${user.first_name} ${user.last_name}` 
                        : user.username || user.email || 'Unknown User';
                      
                      const formatLoginTime = (timestamp: string | null | undefined) => {
                        if (!timestamp) return '—';
                        try {
                          const date = new Date(timestamp);
                          const now = new Date();
                          const diffMs = now.getTime() - date.getTime();
                          const diffMins = Math.floor(diffMs / 60000);
                          const diffHours = Math.floor(diffMs / 3600000);
                          const diffDays = Math.floor(diffMs / 86400000);
                          
                          if (diffMins < 1) return 'Just now';
                          if (diffMins < 60) return `${diffMins} min${diffMins > 1 ? 's' : ''} ago`;
                          if (diffHours < 24) return `${diffHours} hour${diffHours > 1 ? 's' : ''} ago`;
                          if (diffDays < 7) return `${diffDays} day${diffDays > 1 ? 's' : ''} ago`;
                          
                          // For older dates, show formatted date
                          return date.toLocaleDateString('en-US', { 
                            month: 'short', 
                            day: 'numeric', 
                            year: date.getFullYear() !== now.getFullYear() ? 'numeric' : undefined 
                          });
                        } catch {
                          return '—';
                        }
                      };
                      
                      return (
                        <tr key={user.id || user.clerk_user_id || idx}>
                          <td className="px-4 py-3 text-text-primary">
                            <div className="flex items-center gap-2">
                              <span className="w-6 h-6 rounded-full bg-accent-blue/20 flex items-center justify-center text-xs font-semibold text-accent-blue">
                                {idx + 1}
                              </span>
                              <span className="text-sm font-medium">{userName}</span>
                            </div>
                          </td>
                          <td className="px-4 py-3 text-text-secondary text-sm">{user.email || '—'}</td>
                          <td className="px-4 py-3">
                            <span className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
                              user.role === 'admin' 
                                ? 'bg-purple-500/20 text-purple-500 border border-purple-500/30' 
                                : 'bg-blue-500/20 text-blue-500 border border-blue-500/30'
                            }`}>
                              {user.role || 'user'}
                            </span>
                          </td>
                          <td className="px-4 py-3 text-right text-text-secondary text-sm">
                            {formatLoginTime(user.last_sign_in_at)}
                          </td>
                        </tr>
                      );
                    });
                  })()}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        {/* Admin Metric Detail Modal */}
        {selectedAdminMetric && (
          <AdminMetricDetailModal
            metricType={selectedAdminMetric}
            adminMetrics={adminMetrics}
            adminSummary={adminSummary}
            adminUsage={adminUsage}
            users={users}
            alerts={alerts}
            userBreakdown={userBreakdown}
            ragQualityData={ragQualityData}
            onClose={() => setSelectedAdminMetric(null)}
          />
        )}
      </div>
    );
  }

  // Show individual user dashboard
  const summary = myMetrics?.summary || {};
  const usage = myMetrics?.usage || {};
  
  // Debug: log the response to see structure
  if (myMetrics && !summary.tokens && !usage.total_tokens) {
    // User metrics loaded
  }

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-semibold text-text-primary">My Dashboard</h1>
          <p className="text-sm text-text-secondary mt-1">
            Your usage metrics and statistics
          </p>
        </div>
        <button
          onClick={() => {
            fetchMyMetrics();
            fetchAlerts();
          }}
          disabled={loading}
          className="flex items-center gap-2 px-4 py-2 rounded-lg bg-surface-hover border border-border-default hover:bg-surface-hover/80 transition-colors disabled:opacity-50 disabled:cursor-not-allowed text-text-secondary hover:text-text-primary"
          title="Refresh metrics"
        >
          <span className="text-sm font-medium">Refresh</span>
        </button>
      </div>

      {/* Metrics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4 mb-8">
        <button
          onClick={() => setSelectedMetric('tokens')}
          className="bg-surface rounded-xl p-4 border border-border-default hover:border-accent-blue transition-colors text-left cursor-pointer"
        >
          <div className="flex items-center gap-2 mb-1">
            <TrendingUp className="w-4 h-4 text-text-secondary" />
            <h4 className="text-xs font-medium text-text-secondary">Total Tokens</h4>
          </div>
          <p className="text-2xl font-bold text-text-primary">
            {formatNumber(summary.tokens?.total || usage.total_tokens)}
          </p>
        </button>
        <button
          onClick={() => setSelectedMetric('cost')}
          className="bg-surface rounded-xl p-4 border border-border-default hover:border-accent-blue transition-colors text-left cursor-pointer"
        >
          <div className="flex items-center gap-2 mb-1">
            <DollarSign className="w-4 h-4 text-text-secondary" />
            <h4 className="text-xs font-medium text-text-secondary">Total Cost</h4>
          </div>
          <p className="text-2xl font-bold text-text-primary">
            {formatCurrency(summary.costs?.total || usage.total_cost)}
          </p>
        </button>
        <button
          onClick={() => setSelectedMetric('latency')}
          className="bg-surface rounded-xl p-4 border border-border-default hover:border-accent-blue transition-colors text-left cursor-pointer"
        >
          <div className="flex items-center gap-2 mb-1">
            <Clock className="w-4 h-4 text-text-secondary" />
            <h4 className="text-xs font-medium text-text-secondary">Avg Latency</h4>
          </div>
          <p className="text-2xl font-bold text-text-primary">
            {formatLatency(summary.latency?.average)}
          </p>
        </button>
        <button
          onClick={() => setSelectedMetric('cache')}
          className="bg-surface rounded-xl p-4 border border-border-default hover:border-accent-blue transition-colors text-left cursor-pointer"
        >
          <div className="flex items-center gap-2 mb-1">
            <Database className="w-4 h-4 text-text-secondary" />
            <h4 className="text-xs font-medium text-text-secondary">Cache Hit %</h4>
          </div>
          <p className="text-2xl font-bold text-text-primary">
            {formatPercentage(
              summary.cache?.hit_rate != null ? summary.cache.hit_rate * 100 : undefined
            )}
          </p>
        </button>
        <button
          onClick={() => setSelectedMetric('calls')}
          className="bg-surface rounded-xl p-4 border border-border-default hover:border-accent-blue transition-colors text-left cursor-pointer"
        >
          <div className="flex items-center gap-2 mb-1">
            <Phone className="w-4 h-4 text-text-secondary" />
            <h4 className="text-xs font-medium text-text-secondary">Total Calls</h4>
          </div>
          <p className="text-2xl font-bold text-text-primary">
            {formatNumber(summary.llm_calls?.total || usage.total_calls)}
          </p>
        </button>
        <button
          onClick={() => setSelectedMetric('alerts')}
          className="bg-surface rounded-xl p-4 border border-border-default hover:border-accent-blue transition-colors text-left cursor-pointer"
        >
          <div className="flex items-center gap-2 mb-1">
            <AlertCircle className="w-4 h-4 text-text-secondary" />
            <h4 className="text-xs font-medium text-text-secondary">Active Alerts</h4>
          </div>
          <p className="text-2xl font-bold text-text-primary">
            {formatNumber(alerts?.status?.active_alerts || 0)}
          </p>
        </button>
      </div>

      {/* Endpoint Usage */}
      {myMetrics?.endpoints && myMetrics.endpoints.length > 0 ? (
        <div className="bg-surface rounded-2xl border border-border-default p-6">
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
                      width: `${Math.min((endpoint.total_tokens / (summary.tokens?.total || usage.total_tokens || 1)) * 100, 100)}%`,
                    }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      ) : (
        <div className="bg-surface rounded-2xl border border-border-default p-6">
          <p className="text-text-secondary text-center py-8">No endpoint usage data available</p>
        </div>
      )}

      {/* Metric Detail Modal */}
      {selectedMetric && (
        <MetricDetailModal
          metricType={selectedMetric}
          summary={summary}
          usage={usage}
          alerts={alerts}
          onClose={() => setSelectedMetric(null)}
        />
      )}
    </div>
  );
}
