'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  Home,
  BookOpen,
  BarChart3,
  FolderOpen,
  CalendarDays,
  Lightbulb,
} from 'lucide-react';
import { AppBrandLogo } from '@/components/layout/AppBrandLogo';
import { UserMenuDropdown } from '@/components/layout/UserMenuDropdown';
import { HomeNotificationsDropdown } from './HomeNotificationsDropdown';
import { useNotebookLeaveGuardOptional } from '@/contexts/NotebookLeaveGuardContext';
import { useTutorClass } from '@/contexts/TutorClassContext';
import { TUTOR_CLASS_OPTIONS } from '@/hooks/useTutorCatalog';
import { isProblemSolverEnabled } from '@/lib/feature-flags';

const baseNavItems = [
  { href: '/home', label: 'Home', icon: Home },
  { href: '/library', label: 'Library', icon: BookOpen },
  ...(isProblemSolverEnabled
    ? [{ href: '/problem-solver', label: 'Problem Solver', icon: Lightbulb } as const]
    : []),
  { href: '/study-planner', label: 'Study Plan', icon: CalendarDays },
  { href: '/analytics', label: 'Analytics', icon: BarChart3 },
  { href: '/assets', label: 'Assets', icon: FolderOpen },
] as const;

type HomeTopNavProps = {
  /** Library mock uses underline; home uses pill highlight */
  activeStyle?: 'pill' | 'underline';
  /** Hide class selector pill (Study Plan page only) */
  hideClassPill?: boolean;
};

export function HomeTopNav({ activeStyle = 'pill', hideClassPill = false }: HomeTopNavProps) {
  const pathname = usePathname();
  const leaveGuard = useNotebookLeaveGuardOptional();
  const { classNum, setClassNum } = useTutorClass();

  const handleNav = (href: string, event: React.MouseEvent) => {
    if (leaveGuard && href !== pathname) {
      event.preventDefault();
      leaveGuard.tryNavigate(href);
    }
  };

  const toggleClass = () => {
    const idx = TUTOR_CLASS_OPTIONS.indexOf(classNum);
    const next = TUTOR_CLASS_OPTIONS[(idx + 1) % TUTOR_CLASS_OPTIONS.length];
    setClassNum(next);
  };

  const isActive = (href: string) => {
    if (pathname === href) return true;
    if (href === '/library' && pathname.startsWith('/library')) return true;
    if (href === '/assets' && pathname.startsWith('/assets')) return true;
    if (href === '/home' && pathname.startsWith('/profile')) return true;
    if (href === '/study-planner' && pathname.startsWith('/study-planner')) return true;
    if (href === '/problem-solver' && pathname.startsWith('/problem-solver')) return true;
    if (
      href !== '/home' &&
      href !== '/library' &&
      href !== '/assets' &&
      href !== '/study-planner' &&
      pathname.startsWith(href)
    ) {
      return true;
    }
    return false;
  };

  return (
    <header className="home-top-nav">
      <div className="home-top-nav__start">
        <AppBrandLogo showDivider />

        <nav className="home-top-nav__links" aria-label="Main">
          {baseNavItems.map(({ href, label, icon: Icon }) => {
            const active = isActive(href);
            const linkClass =
              activeStyle === 'underline'
                ? active
                  ? 'home-top-nav__link home-top-nav__link--underline home-top-nav__link--active-underline'
                  : 'home-top-nav__link home-top-nav__link--underline'
                : active
                  ? 'home-top-nav__link home-top-nav__link--pill home-top-nav__link--active-pill'
                  : 'home-top-nav__link home-top-nav__link--pill';
            return (
              <Link
                key={href}
                href={href}
                className={linkClass}
                onClick={(event) => handleNav(href, event)}
              >
                <Icon className="w-4 h-4" strokeWidth={1.75} />
                {label}
              </Link>
            );
          })}
        </nav>
      </div>

      <div className="home-top-nav__end">
        {!hideClassPill && (
          <button
            type="button"
            className="home-top-nav__class hidden lg:flex"
            onClick={toggleClass}
            aria-label={`Class ${classNum}. Click to switch class.`}
          >
            <span className="home-top-nav__class-dot" aria-hidden />
            Class {classNum}
          </button>
        )}
        <HomeNotificationsDropdown />
        <UserMenuDropdown />
      </div>
    </header>
  );
}
