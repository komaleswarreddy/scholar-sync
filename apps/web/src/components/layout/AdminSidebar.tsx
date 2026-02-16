'use client';

import { usePathname, useRouter } from 'next/navigation';
import { useEffect } from 'react';
import {
  LayoutDashboard,
  Users,
  FileText,
  Search,
  BarChart3,
  Bot,
  Shield,
  Network,
  DollarSign,
  Bell,
  FileSearch,
} from 'lucide-react';

interface MenuItem {
  label: string;
  path: string;
  icon: React.ComponentType<{ className?: string }>;
}

const menuItems: MenuItem[] = [
  { label: 'Overview', path: '/analytics', icon: LayoutDashboard },
  { label: 'Users', path: '/analytics/users', icon: Users },
  { label: 'Documents', path: '/analytics/documents', icon: FileText },
  { label: 'Queries', path: '/analytics/queries', icon: Search },
  { label: 'RAG Metrics', path: '/analytics/rag-metrics', icon: BarChart3 },
  { label: 'Agents', path: '/analytics/agents', icon: Bot },
  { label: 'Guardrails', path: '/analytics/guardrails', icon: Shield },
  { label: 'Endpoints', path: '/analytics/endpoints', icon: Network },
  { label: 'Cost & Tokens', path: '/analytics/cost-tokens', icon: DollarSign },
  { label: 'Alerts', path: '/analytics/alerts', icon: Bell },
  { label: 'Logs', path: '/analytics/logs', icon: FileSearch },
];

interface AdminSidebarProps {
  onNavigate?: () => void;
  isAdmin?: boolean;
}

export function AdminSidebar({ onNavigate, isAdmin = false }: AdminSidebarProps) {
  const pathname = usePathname();
  const router = useRouter();

  // Close sidebar on mobile when route changes
  useEffect(() => {
    if (onNavigate && window.innerWidth < 1024) {
      onNavigate();
    }
  }, [pathname, onNavigate]);

  const handleNavigation = (path: string) => {
    router.push(path);
    // Close sidebar on mobile after navigation
    if (window.innerWidth < 1024 && onNavigate) {
      onNavigate();
    }
  };

  return (
    <aside className="w-64 bg-surface border-r border-border-default flex flex-col h-full overflow-y-auto">
      {/* Sidebar Header */}
      <div className="h-14 border-b border-border-default flex items-center px-6 flex-shrink-0 lg:hidden">
        <h2 className="text-sm font-semibold text-text-primary">Admin Dashboard</h2>
      </div>

      {/* Navigation Menu */}
      <nav className="flex-1 px-3 py-4 space-y-1">
        {menuItems
          .filter((item) => {
            // For non-admin users, only show Overview
            if (!isAdmin && item.path !== '/analytics') {
              return false;
            }
            return true;
          })
          .map((item) => {
          const Icon = item.icon;
          const isActive = pathname === item.path || 
            (item.path !== '/analytics' && pathname?.startsWith(item.path));
          
          return (
            <button
              key={item.path}
              onClick={() => handleNavigation(item.path)}
              className={`
                w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium
                transition-all duration-150
                ${
                  isActive
                    ? 'bg-accent-blue/10 text-accent-blue border border-accent-blue/20 shadow-sm'
                    : 'text-text-secondary hover:bg-surface-hover hover:text-text-primary border border-transparent'
                }
              `}
              aria-current={isActive ? 'page' : undefined}
            >
              <Icon className={`w-5 h-5 flex-shrink-0 ${isActive ? 'text-accent-blue' : ''}`} />
              <span className="truncate">{item.label}</span>
            </button>
          );
        })}
      </nav>
    </aside>
  );
}
