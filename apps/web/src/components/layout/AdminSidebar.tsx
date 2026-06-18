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
  GitBranch,
  GraduationCap,
} from 'lucide-react';

interface MenuItem {
  label: string;
  path: string;
  icon: React.ComponentType<{ className?: string }>;
}

const menuItems: MenuItem[] = [
  { label: 'Overview', path: '/admin/users', icon: LayoutDashboard },
  { label: 'Users', path: '/admin/users', icon: Users },
  { label: 'Documents', path: '/admin/documents', icon: FileText },
  { label: 'NCERT Global', path: '/admin/ncert-global', icon: GraduationCap },
  { label: 'Queries', path: '/admin/queries', icon: Search },
  { label: 'RAG Metrics', path: '/admin/rag-metrics', icon: BarChart3 },
  { label: 'Agents', path: '/admin/agents', icon: Bot },
  { label: 'Guardrails', path: '/admin/guardrails', icon: Shield },
  { label: 'Endpoints', path: '/admin/endpoints', icon: Network },
  { label: 'Cost & Tokens', path: '/admin/cost-tokens', icon: DollarSign },
  { label: 'Alerts', path: '/admin/alerts', icon: Bell },
  { label: 'Logs', path: '/admin/logs', icon: FileSearch },
  { label: 'Pipeline', path: '/admin/pipeline', icon: GitBranch },
];

interface AdminSidebarProps {
  onNavigate?: () => void;
}

export function AdminSidebar({ onNavigate }: AdminSidebarProps) {
  const pathname = usePathname();
  const router = useRouter();

  useEffect(() => {
    if (onNavigate && window.innerWidth < 1024) {
      onNavigate();
    }
  }, [pathname, onNavigate]);

  const handleNavigation = (path: string) => {
    router.push(path);
    if (window.innerWidth < 1024 && onNavigate) {
      onNavigate();
    }
  };

  return (
    <aside className="w-64 bg-surface border-r border-border-default flex flex-col h-full overflow-y-auto">
      <div className="h-14 border-b border-border-default flex items-center px-6 flex-shrink-0 lg:hidden">
        <h2 className="text-sm font-semibold text-text-primary">Admin Dashboard</h2>
      </div>

      <nav className="flex-1 px-3 py-4 space-y-1">
        {menuItems.map((item) => {
          const Icon = item.icon;
          const isOverview = item.path === '/admin/users' && item.label === 'Overview';
          const isActive =
            pathname === item.path ||
            (isOverview && pathname === '/admin') ||
            (!isOverview && item.path !== '/admin/users' && pathname?.startsWith(item.path));

          return (
            <button
              key={`${item.label}-${item.path}`}
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
