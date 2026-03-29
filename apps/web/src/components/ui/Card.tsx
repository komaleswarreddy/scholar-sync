/**
 * Card Component
 * 
 * Reusable card component for Studio items and other content.
 */

import { ReactNode } from 'react';

interface CardProps {
  children: ReactNode;
  className?: string;
  hover?: boolean;
  onClick?: () => void;
  /** Native tooltip when hovering (e.g. why a card is disabled) */
  title?: string;
}

export function Card({ children, className = '', hover = false, onClick, title }: CardProps) {
  const baseStyles = 'bg-surface border border-transparent rounded-2xl p-3 transition-all duration-200';
  const hoverStyles = hover ? 'group cursor-pointer hover:bg-surface-hover hover:border-border-default active:scale-[0.98]' : '';
  
  return (
    <div
      className={`${baseStyles} ${hoverStyles} ${className}`}
      onClick={onClick}
      title={title}
    >
      {children}
    </div>
  );
}

