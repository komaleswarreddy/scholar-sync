'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { Home, BookOpen, BarChart3, FolderOpen, CalendarDays, Lightbulb } from 'lucide-react';
import { isProblemSolverEnabled } from '@/lib/feature-flags';

const baseItems = [
  { href: '/home', icon: Home, label: 'Home' },
  { href: '/library', icon: BookOpen, label: 'Library' },
  ...(isProblemSolverEnabled
    ? [{ href: '/problem-solver', icon: Lightbulb, label: 'Problem Solver' } as const]
    : []),
  { href: '/study-planner', icon: CalendarDays, label: 'Study Plan' },
  { href: '/analytics', icon: BarChart3, label: 'Analytics' },
  { href: '/assets', icon: FolderOpen, label: 'Assets' },
] as const;

export function HomeMobileNav() {
  const pathname = usePathname();

  const isActive = (href: string) => {
    if (pathname === href) return true;
    if (href === '/library' && pathname.startsWith('/library')) return true;
    if (href === '/assets' && pathname.startsWith('/assets')) return true;
    if (href === '/study-planner' && pathname.startsWith('/study-planner')) return true;
    if (href === '/problem-solver' && pathname.startsWith('/problem-solver')) return true;
    return false;
  };

  return (
    <nav className="md:hidden flex gap-2 overflow-x-auto pb-3 mb-5 -mx-1 px-1">
      {baseItems.map(({ href, icon: Icon, label }) => (
        <Link
          key={href}
          href={href}
          className={`flex items-center gap-1.5 px-3 py-2 rounded-full text-xs font-medium whitespace-nowrap border ${
            isActive(href)
              ? 'bg-brand-surface border-brand-primary/30 text-brand-primary'
              : 'border-border-default text-text-secondary'
          }`}
        >
          <Icon className="w-3.5 h-3.5" strokeWidth={1.75} />
          {label}
        </Link>
      ))}
    </nav>
  );
}
