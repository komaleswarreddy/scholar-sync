/**
 * Alerts Page
 * 
 * Admin page for viewing and managing system alerts.
 */

'use client';

import { useEffect, useState } from 'react';
import { useAuth } from '@clerk/nextjs';
import { apiClient } from '@/lib/api-client';
import { Loader2, AlertTriangle, AlertCircle, XCircle, CheckCircle2, Filter, X } from 'lucide-react';
import { Button } from '@/components/ui/Button';

interface Alert {
  id?: string;
  alert_type?: string;
  severity?: string;
  message?: string;
  detail?: string;
  timestamp?: string;
  created_at?: string;
  user_id?: string;
  tenant_id?: string;
  resolved?: boolean;
}

export default function AlertsPage() {
  const { getToken } = useAuth();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [filterType, setFilterType] = useState<string>('all');
  const [filterSeverity, setFilterSeverity] = useState<string>('all');

  useEffect(() => {
    const fetchAlerts = async () => {
      if (!getToken) return;
      
      setLoading(true);
      setError(null);
      
      try {
        apiClient.setTokenGetter(getToken);
        const data = await apiClient.getAlertsStatus();
        setAlerts(data.alerts || []);
      } catch (err: any) {
        console.error('[Alerts] Failed to fetch alerts:', err);
        setError(err?.message || 'Failed to load alerts');
      } finally {
        setLoading(false);
      }
    };

    fetchAlerts();
    
    // Refresh alerts every 30 seconds
    const interval = setInterval(fetchAlerts, 30000);
    return () => clearInterval(interval);
  }, [getToken]);

  const formatTimestamp = (timestamp: string | undefined) => {
    if (!timestamp) return 'N/A';
    const date = new Date(timestamp);
    return date.toLocaleString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const getSeverityColor = (severity: string | undefined) => {
    switch (severity?.toLowerCase()) {
      case 'high':
        return 'bg-red-500/20 text-red-500 border-red-500/30';
      case 'medium':
        return 'bg-yellow-500/20 text-yellow-500 border-yellow-500/30';
      case 'low':
        return 'bg-blue-500/20 text-blue-500 border-blue-500/30';
      default:
        return 'bg-gray-500/20 text-gray-500 border-gray-500/30';
    }
  };

  const getSeverityIcon = (severity: string | undefined) => {
    switch (severity?.toLowerCase()) {
      case 'high':
        return <XCircle className="w-5 h-5 text-red-500" />;
      case 'medium':
        return <AlertTriangle className="w-5 h-5 text-yellow-500" />;
      case 'low':
        return <AlertCircle className="w-5 h-5 text-blue-500" />;
      default:
        return <AlertCircle className="w-5 h-5 text-gray-500" />;
    }
  };

  const handleMarkResolved = async (alertId: string | undefined) => {
    if (!alertId || !getToken) return;
    
    try {
      // In production, you'd have a markResolved endpoint
      // For now, we'll just update the local state
      setAlerts(alerts.map(alert => 
        alert.id === alertId ? { ...alert, resolved: true } : alert
      ));
    } catch (err) {
      console.error('[Alerts] Failed to mark alert as resolved:', err);
    }
  };

  const filteredAlerts = alerts.filter(alert => {
    let matchesType = filterType === 'all' || alert.alert_type === filterType;
    
    // Enhanced filtering for system alerts, failures, token spikes, and timeouts
    if (filterType === 'system') {
      matchesType = alert.alert_type === 'system' || 
                   alert.message?.toLowerCase().includes('system') ||
                   !alert.user_id; // System alerts typically don't have user_id
    } else if (filterType === 'failure') {
      matchesType = alert.alert_type === 'failure' || 
                   alert.message?.toLowerCase().includes('failed') ||
                   alert.message?.toLowerCase().includes('error');
    } else if (filterType === 'token_spike') {
      matchesType = alert.alert_type === 'token_spike' || 
                   alert.message?.toLowerCase().includes('token spike') ||
                   alert.message?.toLowerCase().includes('high token');
    } else if (filterType === 'timeout') {
      matchesType = alert.alert_type === 'timeout' || 
                   alert.message?.toLowerCase().includes('timeout') ||
                   alert.message?.toLowerCase().includes('timed out');
    } else if (filterType === 'cost_spike') {
      matchesType = alert.alert_type === 'cost_spike' || 
                   alert.message?.toLowerCase().includes('cost spike') ||
                   alert.message?.toLowerCase().includes('high cost');
    } else if (filterType === 'rate_limit') {
      matchesType = alert.alert_type === 'rate_limit' || 
                   alert.message?.toLowerCase().includes('rate limit') ||
                   alert.message?.toLowerCase().includes('quota');
    }
    
    const matchesSeverity = filterSeverity === 'all' || alert.severity?.toLowerCase() === filterSeverity.toLowerCase();
    return matchesType && matchesSeverity;
  });

  const activeAlerts = filteredAlerts.filter(a => !a.resolved);
  const resolvedAlerts = filteredAlerts.filter(a => a.resolved);

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-8 h-8 animate-spin text-accent-blue mx-auto mb-4" />
          <p className="text-text-secondary">Loading alerts...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="h-full">
        <div className="mb-6">
          <h1 className="text-2xl font-semibold text-text-primary">Alerts</h1>
          <p className="text-sm text-text-secondary mt-1">
            View and manage system alerts
          </p>
        </div>
        <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-6">
          <p className="text-red-500">{error}</p>
        </div>
      </div>
    );
  }

  // Enhanced alert types including system alerts, failures, token spikes, and timeouts
  const alertTypes = Array.from(new Set([
    ...alerts.map(a => a.alert_type).filter(Boolean),
    'system',
    'failure',
    'token_spike',
    'timeout',
    'cost_spike',
    'rate_limit',
  ]));

  return (
    <div className="h-full">
      <div className="mb-6">
        <h1 className="text-2xl font-semibold text-text-primary">Alerts</h1>
        <p className="text-sm text-text-secondary mt-1">
          View and manage system alerts
        </p>
      </div>

      {/* Statistics */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <div className="bg-surface rounded-xl border border-border-default p-5">
          <h3 className="text-sm font-medium text-text-secondary mb-2">Total Alerts</h3>
          <p className="text-3xl font-bold text-text-primary">{alerts.length}</p>
        </div>
        <div className="bg-surface rounded-xl border border-border-default p-5">
          <h3 className="text-sm font-medium text-text-secondary mb-2">Active</h3>
          <p className="text-3xl font-bold text-red-500">{activeAlerts.length}</p>
        </div>
        <div className="bg-surface rounded-xl border border-border-default p-5">
          <h3 className="text-sm font-medium text-text-secondary mb-2">Resolved</h3>
          <p className="text-3xl font-bold text-green-500">{resolvedAlerts.length}</p>
        </div>
        <div className="bg-surface rounded-xl border border-border-default p-5">
          <h3 className="text-sm font-medium text-text-secondary mb-2">High Severity</h3>
          <p className="text-3xl font-bold text-red-500">
            {alerts.filter(a => a.severity?.toLowerCase() === 'high').length}
          </p>
        </div>
      </div>

      {/* Filters */}
      <div className="mb-6 flex flex-col md:flex-row gap-4">
        <div className="flex items-center gap-2">
          <Filter className="w-5 h-5 text-text-secondary" />
          <span className="text-sm text-text-secondary">Filters:</span>
        </div>
        <select
          value={filterType}
          onChange={(e) => setFilterType(e.target.value)}
          className="bg-surface border border-border-default rounded-lg px-4 py-2 text-sm text-text-primary focus:outline-none focus:border-border-active"
        >
          <option value="all">All Types</option>
          <option value="system">System Alerts</option>
          <option value="failure">Failures</option>
          <option value="token_spike">Token Spikes</option>
          <option value="timeout">Timeouts</option>
          <option value="cost_spike">Cost Spikes</option>
          <option value="rate_limit">Rate Limits</option>
          {alertTypes.filter(type => !['system', 'failure', 'token_spike', 'timeout', 'cost_spike', 'rate_limit'].includes(type)).map(type => (
            <option key={type} value={type}>{type}</option>
          ))}
        </select>
        <select
          value={filterSeverity}
          onChange={(e) => setFilterSeverity(e.target.value)}
          className="bg-surface border border-border-default rounded-lg px-4 py-2 text-sm text-text-primary focus:outline-none focus:border-border-active"
        >
          <option value="all">All Severities</option>
          <option value="high">High</option>
          <option value="medium">Medium</option>
          <option value="low">Low</option>
        </select>
      </div>

      {/* Active Alerts */}
      {activeAlerts.length > 0 && (
        <div className="mb-6">
          <h2 className="text-lg font-semibold text-text-primary mb-4">Active Alerts ({activeAlerts.length})</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {activeAlerts.map((alert, idx) => (
              <div
                key={idx}
                className="bg-surface rounded-xl border border-border-default p-5 hover:border-border-active transition-colors"
              >
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-center gap-2">
                    {getSeverityIcon(alert.severity)}
                    <span className={`px-2 py-1 rounded text-xs font-medium border ${getSeverityColor(alert.severity)}`}>
                      {alert.severity || 'Unknown'}
                    </span>
                  </div>
                  {alert.alert_type && (
                    <span className="text-xs text-text-tertiary bg-surface-hover px-2 py-1 rounded">
                      {alert.alert_type}
                    </span>
                  )}
                </div>
                <p className="text-sm font-medium text-text-primary mb-2">
                  {alert.message || alert.detail || 'No message'}
                </p>
                <p className="text-xs text-text-tertiary mb-4">
                  {formatTimestamp(alert.timestamp || alert.created_at)}
                </p>
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => handleMarkResolved(alert.id)}
                  className="w-full"
                >
                  <CheckCircle2 className="w-4 h-4 mr-2" />
                  Mark Resolved
                </Button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Resolved Alerts */}
      {resolvedAlerts.length > 0 && (
        <div>
          <h2 className="text-lg font-semibold text-text-primary mb-4">Resolved Alerts ({resolvedAlerts.length})</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {resolvedAlerts.map((alert, idx) => (
              <div
                key={idx}
                className="bg-surface rounded-xl border border-border-default p-5 opacity-60"
              >
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <CheckCircle2 className="w-5 h-5 text-green-500" />
                    <span className="px-2 py-1 rounded text-xs font-medium border bg-green-500/20 text-green-500 border-green-500/30">
                      Resolved
                    </span>
                  </div>
                  {alert.alert_type && (
                    <span className="text-xs text-text-tertiary bg-surface-hover px-2 py-1 rounded">
                      {alert.alert_type}
                    </span>
                  )}
                </div>
                <p className="text-sm font-medium text-text-primary mb-2">
                  {alert.message || alert.detail || 'No message'}
                </p>
                <p className="text-xs text-text-tertiary">
                  {formatTimestamp(alert.timestamp || alert.created_at)}
                </p>
              </div>
            ))}
          </div>
        </div>
      )}

      {filteredAlerts.length === 0 && (
        <div className="bg-surface rounded-2xl border border-border-default p-12 text-center">
          <AlertCircle className="w-12 h-12 text-text-tertiary mx-auto mb-4" />
          <p className="text-text-secondary">No alerts found matching your filters</p>
        </div>
      )}

      {/* Alert User Session Table */}
      <div className="mt-8">
        <h2 className="text-lg font-semibold text-text-primary mb-4">Alert User Sessions</h2>
        <p className="text-sm text-text-secondary mb-4">
          Users and sessions associated with alerts related to token consumption, cost, or security issues
        </p>
        <div className="bg-surface rounded-2xl border border-border-default p-6">
          <div className="bg-surface-hover rounded-xl border border-border-default overflow-hidden">
            <table className="w-full">
              <thead className="bg-surface border-b border-border-default">
                <tr>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-text-primary">User ID</th>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-text-primary">Session ID</th>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-text-primary">Alert Type</th>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-text-primary">Severity</th>
                  <th className="px-4 py-3 text-left text-sm font-semibold text-text-primary">Message</th>
                  <th className="px-4 py-3 text-right text-sm font-semibold text-text-primary">Date</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border-default">
                <tr>
                  <td colSpan={6} className="px-4 py-8 text-center text-text-tertiary">
                    No alert user session data available yet. Data will appear here when alerts are triggered.
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
}
