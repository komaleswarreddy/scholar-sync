'use client';

import { usePathname, useRouter } from 'next/navigation';
import { ChevronLeft, ChevronRight, ClipboardList } from 'lucide-react';

interface MenuItem {
  label: string;
  path: string;
  icon: React.ComponentType<{ className?: string }>;
}

const menuItems: MenuItem[] = [
  { label: 'Exams', path: '/teacher/exams', icon: ClipboardList },
];

interface TeacherSidebarProps {
  collapsed?: boolean;
  onToggleCollapse?: () => void;
  onNavigate?: () => void;
}

export function TeacherSidebar({
  collapsed = false,
  onToggleCollapse,
  onNavigate,
}: TeacherSidebarProps) {
  const pathname = usePathname();
  const router = useRouter();

  const handleNavigation = (path: string) => {
    router.push(path);
    if (window.innerWidth < 1024 && onNavigate) {
      onNavigate();
    }
  };

  return (
    <aside
      className={`teacher-sidebar bg-surface border-r border-border-default flex flex-col h-full overflow-hidden transition-[width] duration-300 ease-in-out ${
        collapsed ? 'teacher-sidebar--collapsed w-[72px]' : 'w-64'
      }`}
      aria-label="Teacher navigation"
    >
      <div className="h-14 border-b border-border-default flex items-center flex-shrink-0 lg:hidden px-6">
        <h2 className="text-sm font-semibold text-text-primary">Teacher Portal</h2>
      </div>

      <nav className={`flex-1 py-4 space-y-1 overflow-y-auto ${collapsed ? 'px-2' : 'px-3'}`}>
        {menuItems.map((item) => {
          const Icon = item.icon;
          const isActive = pathname === item.path || pathname?.startsWith(`${item.path}/`);

          return (
            <button
              key={item.path}
              type="button"
              onClick={() => handleNavigation(item.path)}
              title={collapsed ? item.label : undefined}
              className={`
                w-full flex items-center rounded-lg text-sm font-medium
                transition-all duration-150
                ${collapsed ? 'justify-center px-2 py-2.5' : 'gap-3 px-3 py-2.5'}
                ${
                  isActive
                    ? 'bg-accent-blue/10 text-accent-blue border border-accent-blue/20 shadow-sm'
                    : 'text-text-secondary hover:bg-surface-hover hover:text-text-primary border border-transparent'
                }
              `}
              aria-current={isActive ? 'page' : undefined}
              aria-label={item.label}
            >
              <Icon className={`w-5 h-5 flex-shrink-0 ${isActive ? 'text-accent-blue' : ''}`} />
              {!collapsed && <span className="truncate">{item.label}</span>}
            </button>
          );
        })}
      </nav>

      {onToggleCollapse && (
        <div className={`hidden lg:flex border-t border-border-default p-2 ${collapsed ? 'justify-center' : ''}`}>
          <button
            type="button"
            onClick={onToggleCollapse}
            className={`flex items-center gap-2 rounded-lg text-text-secondary hover:bg-surface-hover hover:text-text-primary transition-colors ${
              collapsed ? 'p-2.5' : 'w-full px-3 py-2.5 text-sm font-medium'
            }`}
            aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
            aria-expanded={!collapsed}
          >
            {collapsed ? (
              <ChevronRight className="w-5 h-5" />
            ) : (
              <>
                <ChevronLeft className="w-5 h-5 flex-shrink-0" />
                <span className="truncate">Collapse</span>
              </>
            )}
          </button>
        </div>
      )}
    </aside>
  );
}
