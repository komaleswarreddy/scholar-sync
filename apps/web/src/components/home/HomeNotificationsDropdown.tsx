'use client';

import { useEffect, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import { BarChart3, Bell, Target } from 'lucide-react';
import { FOCUS_SESSION_URL } from '@/lib/home-mock-data';

const notificationItems = [
  {
    id: 'focus-session',
    label: 'Focus session',
    href: FOCUS_SESSION_URL,
    icon: Target,
  },
  {
    id: 'test-analytics',
    label: 'Test Analytics',
    href: '/analytics',
    icon: BarChart3,
  },
] as const;

export function HomeNotificationsDropdown() {
  const router = useRouter();
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isOpen]);

  useEffect(() => {
    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape' && isOpen) {
        setIsOpen(false);
      }
    };

    document.addEventListener('keydown', handleEscape);
    return () => {
      document.removeEventListener('keydown', handleEscape);
    };
  }, [isOpen]);

  const handleSelect = (href: string) => {
    setIsOpen(false);
    router.push(href);
  };

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        type="button"
        onClick={() => setIsOpen((open) => !open)}
        className="relative p-2 rounded-full text-[var(--color-home-text-muted)] hover:text-[var(--color-brand-text)] hover:bg-[var(--color-brand-surface)] transition-colors"
        aria-label="Notifications"
        aria-expanded={isOpen}
        aria-haspopup="menu"
      >
        <Bell className="w-5 h-5" strokeWidth={1.75} />
        <span className="absolute top-1 right-1 min-w-[16px] h-4 px-1 rounded-full bg-[var(--color-brand-text)] text-white text-[10px] font-bold flex items-center justify-center">
          {notificationItems.length}
        </span>
      </button>

      {isOpen && (
        <div
          className="home-notifications-dropdown"
          role="menu"
          aria-label="Notifications"
        >
          <p className="home-notifications-dropdown-title">Notifications</p>
          <ul className="home-notifications-dropdown-list">
            {notificationItems.map(({ id, label, href, icon: Icon }) => (
              <li key={id}>
                <button
                  type="button"
                  role="menuitem"
                  onClick={() => handleSelect(href)}
                  className="home-notifications-dropdown-item"
                >
                  <span className="home-notifications-dropdown-icon">
                    <Icon className="w-4 h-4" strokeWidth={1.75} />
                  </span>
                  <span>{label}</span>
                </button>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
