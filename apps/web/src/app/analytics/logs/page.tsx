/**
 * Logs Page
 * 
 * Admin page for viewing system logs.
 */

'use client';

import { useEffect, useState, useRef } from 'react';
import { useAuth } from '@clerk/nextjs';
import { apiClient } from '@/lib/api-client';
import { Search, Loader2, AlertCircle, Info, CheckCircle2, XCircle, Database } from 'lucide-react';
import { Input } from '@/components/ui/Input';

interface LogEntry {
  timestamp: string;
  event_type: string;
  user: string;
  message: string;
  level?: string;
}

export default function LogsPage() {
  const { getToken } = useAuth();
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [filterType, setFilterType] = useState<string>('all');
  const scrollContainerRef = useRef<HTMLDivElement>(null);

  // Fetch real logs from backend
  useEffect(() => {
    const fetchLogs = async () => {
      if (!getToken) return;
      
      setLoading(true);
      setError(null);
      
      try {
        apiClient.setTokenGetter(getToken);
        const data = await apiClient.getLogs(7, 1000, filterType !== 'all' ? filterType : undefined);
        
        // Transform backend logs to LogEntry format
        const logEntries: LogEntry[] = (data.logs || []).map((log: any) => ({
          timestamp: log.timestamp || log.created_at || new Date().toISOString(),
          event_type: log.event_type || 'info',
          user: log.user || log.user_id || 'system',
          message: log.message || log.detail || 'System event',
          level: log.level || 'info',
        }));
        
        setLogs(logEntries);
      } catch (err: any) {
        console.error('[Logs] Failed to fetch logs:', err);
        setError(err?.message || 'Failed to load logs');
      } finally {
        setLoading(false);
      }
    };

    fetchLogs();
  }, [getToken, filterType]);

  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp);
    return date.toLocaleString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  };

  const getEventTypeIcon = (eventType: string) => {
    switch (eventType) {
      case 'error':
        return <XCircle className="w-4 h-4 text-red-500" />;
      case 'success':
        return <CheckCircle2 className="w-4 h-4 text-green-500" />;
      case 'warning':
        return <AlertCircle className="w-4 h-4 text-yellow-500" />;
      case 'cache':
        return <Database className="w-4 h-4 text-purple-500" />;
      default:
        return <Info className="w-4 h-4 text-blue-500" />;
    }
  };

  const getEventTypeColor = (eventType: string) => {
    switch (eventType) {
      case 'error':
        return 'bg-red-500/10 text-red-500 border-red-500/20';
      case 'success':
        return 'bg-green-500/10 text-green-500 border-green-500/20';
      case 'warning':
        return 'bg-yellow-500/10 text-yellow-500 border-yellow-500/20';
      case 'cache':
        return 'bg-purple-500/10 text-purple-500 border-purple-500/20';
      default:
        return 'bg-blue-500/10 text-blue-500 border-blue-500/20';
    }
  };

  const filteredLogs = logs.filter(log => {
    const matchesSearch = searchQuery === '' ||
      log.message.toLowerCase().includes(searchQuery.toLowerCase()) ||
      log.user.toLowerCase().includes(searchQuery.toLowerCase()) ||
      log.event_type.toLowerCase().includes(searchQuery.toLowerCase());
    
    const matchesFilter = filterType === 'all' || log.event_type === filterType;
    
    return matchesSearch && matchesFilter;
  });

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="w-8 h-8 animate-spin text-accent-blue mx-auto mb-4" />
          <p className="text-text-secondary">Loading logs...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="h-full">
        <div className="mb-6">
          <h1 className="text-2xl font-semibold text-text-primary">Logs</h1>
          <p className="text-sm text-text-secondary mt-1">
            View and search system logs
          </p>
        </div>
        <div className="bg-red-500/10 border border-red-500/20 rounded-xl p-6">
          <p className="text-red-500">{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      <div className="mb-6">
        <h1 className="text-2xl font-semibold text-text-primary">Logs</h1>
        <p className="text-sm text-text-secondary mt-1">
          View and search system logs
        </p>
      </div>

      {/* Filters */}
      <div className="mb-4 flex flex-col md:flex-row gap-4">
        <div className="relative flex-1">
          <Search className="absolute left-4 top-1/2 transform -translate-y-1/2 w-5 h-5 text-text-tertiary" />
          <Input
            type="text"
            placeholder="Search logs by message, user, or event type..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-12 pr-4"
          />
        </div>
        <select
          value={filterType}
          onChange={(e) => setFilterType(e.target.value)}
          className="bg-surface border border-border-default rounded-lg px-4 py-2 text-sm text-text-primary focus:outline-none focus:border-border-active"
        >
          <option value="all">All Event Types</option>
          <option value="query">Query</option>
          <option value="success">Success</option>
          <option value="error">Error</option>
          <option value="warning">Warning</option>
          <option value="info">Info</option>
          <option value="cache">Cache</option>
        </select>
      </div>

      {/* Logs Table - Scrollable */}
      <div 
        ref={scrollContainerRef}
        className="flex-1 bg-surface rounded-2xl border border-border-default overflow-hidden flex flex-col"
      >
        <div className="overflow-y-auto flex-1">
          <table className="w-full">
            <thead className="bg-surface-hover border-b border-border-default sticky top-0 z-10">
              <tr>
                <th className="px-6 py-3 text-left text-sm font-semibold text-text-primary">Timestamp</th>
                <th className="px-6 py-3 text-left text-sm font-semibold text-text-primary">Event Type</th>
                <th className="px-6 py-3 text-left text-sm font-semibold text-text-primary">User</th>
                <th className="px-6 py-3 text-left text-sm font-semibold text-text-primary">Message</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border-default">
              {filteredLogs.length === 0 ? (
                <tr>
                  <td colSpan={4} className="px-6 py-12 text-center text-text-secondary">
                    No logs found
                  </td>
                </tr>
              ) : (
                filteredLogs.map((log, idx) => (
                  <tr key={idx} className="hover:bg-surface-hover transition-colors">
                    <td className="px-6 py-3 text-text-secondary text-sm font-mono">
                      {formatTimestamp(log.timestamp)}
                    </td>
                    <td className="px-6 py-3">
                      <div className="flex items-center gap-2">
                        {getEventTypeIcon(log.event_type)}
                        <span className={`px-2 py-1 rounded text-xs font-medium border ${getEventTypeColor(log.event_type)}`}>
                          {log.event_type}
                        </span>
                      </div>
                    </td>
                    <td className="px-6 py-3 text-text-primary font-mono text-sm">{log.user}</td>
                    <td className="px-6 py-3 text-text-primary">{log.message}</td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
        
        {/* Footer with count */}
        <div className="px-6 py-3 border-t border-border-default bg-surface-hover">
          <p className="text-sm text-text-secondary">
            Showing {filteredLogs.length} of {logs.length} log entries
          </p>
        </div>
      </div>
    </div>
  );
}
