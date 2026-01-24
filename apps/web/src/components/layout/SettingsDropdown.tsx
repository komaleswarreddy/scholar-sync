'use client';

import { useState, useRef, useEffect } from 'react';
import { Settings } from 'lucide-react';
import { useTheme } from '@/contexts/ThemeContext';
import { Button } from '../ui/Button';

export function SettingsDropdown() {
  const { theme, toggleTheme } = useTheme();
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Close dropdown when clicking outside
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

  const handleThemeToggle = () => {
    toggleTheme();
  };

  return (
    <div className="relative" ref={dropdownRef}>
      <Button
        variant="ghost"
        size="sm"
        onClick={() => setIsOpen(!isOpen)}
        className="p-2 relative"
        title="Settings"
        aria-label="Open settings menu"
        aria-expanded={isOpen}
        aria-haspopup="true"
      >
        <Settings className="w-4 h-4" />
      </Button>

      {isOpen && (
        <div className="absolute right-0 top-full mt-2 w-64 bg-modal border border-border-default rounded-xl shadow-lg z-50 overflow-hidden">
          <div className="p-4">
            {/* Theme Section */}
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium text-text-primary">Theme</span>
              <div className="flex items-center gap-2">
                <button
                  onClick={handleThemeToggle}
                  className={`
                    relative inline-flex h-6 w-11 items-center rounded-full transition-colors
                    ${theme === 'dark' ? 'bg-accent-blue' : 'bg-surface-hover'}
                    focus:outline-none focus:ring-2 focus:ring-accent-blue focus:ring-offset-2 focus:ring-offset-background
                  `}
                  role="switch"
                  aria-checked={theme === 'dark'}
                  aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} theme`}
                >
                  <span
                    className={`
                      inline-block h-4 w-4 transform rounded-full bg-background transition-transform
                      ${theme === 'dark' ? 'translate-x-6' : 'translate-x-1'}
                    `}
                  />
                </button>
                <span className="text-xs text-text-secondary">
                  {theme === 'dark' ? 'Dark' : 'Light'}
                </span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
