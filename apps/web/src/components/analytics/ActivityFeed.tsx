/**
 * Activity Feed Component
 * 
 * Displays a vertical activity feed with latest events.
 * Supports auto-refresh, loading states, and routing to logs page.
 */

'use client';

import { useState, useEffect, useMemo } from 'react';
import { useRouter } from 'next/navigation';
import { Clock, User, FileText, Search, Bot, Shield, AlertTriangle, XCircle, CheckCircle } from 'lucide-react';

export interface ActivityItem {
  id: string;
  timestamp: string;
  eventType: 'user_login' | 'document_uploaded' | 'document_indexed' | 'query_executed' | 'agent_run' | 'guardrail_block' | 'api_error' | 'alert_triggered';
  module: string;
  userName: string;
  description: string;
  status: 'success' | 'warning' | 'error' | 'blocked';
}

interface ActivityFeedProps {
  items?: ActivityItem[];
  maxItems?: number;
  autoRefresh?: boolean;
  refreshInterval?: number;
  showViewAllButton?: boolean;
  viewAllRoute?: string;
  className?: string;
}

// Event type configuration
const eventTypeConfig = {
  user_login: { label: 'Login', icon: User, color: 'text-blue-500' },
  document_uploaded: { label: 'Upload', icon: FileText, color: 'text-green-500' },
  document_indexed: { label: 'Index', icon: FileText, color: 'text-purple-500' },
  query_executed: { label: 'Query', icon: Search, color: 'text-cyan-500' },
  agent_run: { label: 'Agent', icon: Bot, color: 'text-indigo-500' },
  guardrail_block: { label: 'Guardrail', icon: Shield, color: 'text-red-500' },
  api_error: { label: 'Error', icon: XCircle, color: 'text-red-500' },
  alert_triggered: { label: 'Alert', icon: AlertTriangle, color: 'text-yellow-500' },
};

// Status badge configuration
const statusConfig = {
  success: { label: 'Success', className: 'bg-green-500/20 text-green-500 border-green-500/30' },
  warning: { label: 'Warning', className: 'bg-yellow-500/20 text-yellow-500 border-yellow-500/30' },
  error: { label: 'Error', className: 'bg-red-500/20 text-red-500 border-red-500/30' },
  blocked: { label: 'Blocked', className: 'bg-orange-500/20 text-orange-500 border-orange-500/30' },
};

// Generate mock data
const generateMockActivities = (count: number): ActivityItem[] => {
  const eventTypes: ActivityItem['eventType'][] = [
    'user_login',
    'document_uploaded',
    'document_indexed',
    'query_executed',
    'agent_run',
    'guardrail_block',
    'api_error',
    'alert_triggered',
  ];
  
  const modules = ['Auth', 'Documents', 'RAG', 'API', 'Guardrails', 'Monitoring'];
  const users = ['John Doe', 'Jane Smith', 'Bob Johnson', 'Alice Williams', 'Charlie Brown'];
  const statuses: ActivityItem['status'][] = ['success', 'warning', 'error', 'blocked'];
  
  const descriptions = {
    user_login: ['User logged in successfully', 'User session started', 'Authentication successful'],
    document_uploaded: ['Document uploaded', 'File processed', 'New document added'],
    document_indexed: ['Document indexed', 'Vector embeddings created', 'Indexing completed'],
    query_executed: ['Query processed', 'Search executed', 'LLM call completed'],
    agent_run: ['Agent task started', 'Agent execution completed', 'Workflow triggered'],
    guardrail_block: ['Content blocked by guardrail', 'Policy violation detected', 'Request blocked'],
    api_error: ['API request failed', 'Connection error', 'Timeout occurred'],
    alert_triggered: ['Threshold exceeded', 'Anomaly detected', 'Alert condition met'],
  };
  
  const activities: ActivityItem[] = [];
  const now = Date.now();
  
  for (let i = 0; i < count; i++) {
    const eventType = eventTypes[Math.floor(Math.random() * eventTypes.length)];
    const status = statuses[Math.floor(Math.random() * statuses.length)];
    const module = modules[Math.floor(Math.random() * modules.length)];
    const userName = users[Math.floor(Math.random() * users.length)];
    const eventDescriptions = descriptions[eventType];
    const description = eventDescriptions[Math.floor(Math.random() * eventDescriptions.length)];
    
    // Generate timestamp within last 24 hours, more recent items first
    const hoursAgo = (i * 24) / count + Math.random() * 2;
    const timestamp = new Date(now - hoursAgo * 60 * 60 * 1000).toISOString();
    
    activities.push({
      id: `activity-${i}`,
      timestamp,
      eventType,
      module,
      userName,
      description,
      status,
    });
  }
  
  return activities.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());
};

// Loading skeleton component
const ActivitySkeleton = () => (
  <div className="space-y-3">
    {[...Array(5)].map((_, i) => (
      <div key={i} className="animate-pulse">
        <div className="flex items-start gap-3 p-3 bg-surface-hover rounded-lg border border-border-default">
          <div className="w-8 h-8 rounded-full bg-border-default"></div>
          <div className="flex-1 space-y-2">
            <div className="h-4 bg-border-default rounded w-3/4"></div>
            <div className="h-3 bg-border-default rounded w-1/2"></div>
            <div className="h-3 bg-border-default rounded w-1/4"></div>
          </div>
          <div className="w-16 h-6 bg-border-default rounded"></div>
        </div>
      </div>
    ))}
  </div>
);

export default function ActivityFeed({
  items: externalItems,
  maxItems = 10,
  autoRefresh = true,
  refreshInterval = 15000,
  showViewAllButton = true,
  viewAllRoute = '/dashboard/logs',
  className = '',
}: ActivityFeedProps) {
  const router = useRouter();
  const [items, setItems] = useState<ActivityItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshKey, setRefreshKey] = useState(0);
  
  // Generate or use provided items
  useEffect(() => {
    if (externalItems) {
      setItems(externalItems);
      setLoading(false);
    } else {
      // No external items provided - show empty state instead of mock data
      setItems([]);
      setLoading(false);
    }
  }, [externalItems, refreshKey]);
  
  // Auto-refresh simulation
  useEffect(() => {
    if (!autoRefresh || externalItems) return;
    
    const interval = setInterval(() => {
      setRefreshKey(prev => prev + 1);
    }, refreshInterval);
    
    return () => clearInterval(interval);
  }, [autoRefresh, refreshInterval, externalItems]);
  
  // Get sorted and limited items
  const displayItems = useMemo(() => {
    const sorted = [...items].sort(
      (a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime()
    );
    return sorted.slice(0, maxItems);
  }, [items, maxItems]);
  
  // Format timestamp
  const formatTimestamp = (timestamp: string) => {
    const date = new Date(timestamp);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);
    
    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
  };
  
  const handleViewAll = () => {
    router.push(viewAllRoute);
  };
  
  return (
    <div className={`bg-surface rounded-2xl border border-border-default ${className}`}>
      <div className="p-6">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-text-primary">Recent Activity</h3>
          {autoRefresh && !externalItems && (
            <span className="text-xs text-text-tertiary flex items-center gap-1">
              <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
              Auto-refresh
            </span>
          )}
        </div>
        
        {loading ? (
          <ActivitySkeleton />
        ) : displayItems.length === 0 ? (
          <div className="text-center py-8 text-text-tertiary">
            <p>No activity data available</p>
            <p className="text-xs mt-2">Activity feed will display real events when available</p>
          </div>
        ) : (
          <div className="space-y-2 max-h-[600px] overflow-y-auto pr-2">
            {displayItems.map((item) => {
              const eventConfig = eventTypeConfig[item.eventType];
              const EventIcon = eventConfig.icon;
              const statusBadge = statusConfig[item.status];
              
              return (
                <div
                  key={item.id}
                  className="flex items-start gap-3 p-3 bg-surface-hover rounded-lg border border-border-default hover:bg-surface-hover/80 transition-colors group"
                >
                  {/* Event Icon */}
                  <div className={`flex-shrink-0 w-8 h-8 rounded-full bg-surface flex items-center justify-center ${eventConfig.color}`}>
                    <EventIcon className="w-4 h-4" />
                  </div>
                  
                  {/* Content */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-start justify-between gap-2 mb-1">
                      <div className="flex items-center gap-2 flex-wrap">
                        <span className="text-xs font-medium px-2 py-0.5 rounded bg-surface border border-border-default text-text-secondary">
                          {eventConfig.label}
                        </span>
                        <span className="text-xs text-text-tertiary">•</span>
                        <span className="text-xs text-text-tertiary">{item.module}</span>
                        <span className="text-xs text-text-tertiary">•</span>
                        <span className="text-xs text-text-secondary">{item.userName}</span>
                      </div>
                    </div>
                    
                    <p className="text-sm text-text-primary mb-1 line-clamp-1">
                      {item.description}
                    </p>
                    
                    <div className="flex items-center gap-2 mt-1">
                      <div className="flex items-center gap-1 text-xs text-text-tertiary">
                        <Clock className="w-3 h-3" />
                        <span>{formatTimestamp(item.timestamp)}</span>
                      </div>
                    </div>
                  </div>
                  
                  {/* Status Badge */}
                  <div className="flex-shrink-0">
                    <span className={`text-xs font-medium px-2 py-1 rounded border ${statusBadge.className}`}>
                      {statusBadge.label}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        )}
        
        {/* View All Button */}
        {showViewAllButton && displayItems.length > 0 && (
          <div className="mt-4 pt-4 border-t border-border-default">
            <button
              onClick={handleViewAll}
              className="w-full px-4 py-2 text-sm font-medium text-text-secondary hover:text-text-primary bg-surface-hover hover:bg-surface-hover/80 rounded-lg border border-border-default transition-colors"
            >
              View All Logs
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
