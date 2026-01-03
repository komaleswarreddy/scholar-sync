/**
 * Button Component
 * 
 * Reusable button with variants following design tokens.
 */

import { ButtonHTMLAttributes, ReactNode } from 'react';

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'ghost';
  size?: 'sm' | 'md' | 'lg';
  children: ReactNode;
}

export function Button({
  variant = 'primary',
  size = 'md',
  className = '',
  children,
  ...props
}: ButtonProps) {
  const baseStyles = 'rounded-full font-medium transition-all duration-200 focus:outline-none';
  
  const variants = {
    primary: 'bg-accent-blue text-background hover:opacity-90',
    secondary: 'bg-surface border border-border-default text-text-primary hover:bg-surface-hover',
    ghost: 'bg-transparent text-text-secondary hover:text-text-primary hover:bg-surface-hover',
  };
  
  const sizes = {
    sm: 'px-3 py-1.5 text-sm',
    md: 'px-4 py-2 text-base',
    lg: 'px-6 py-3 text-lg',
  };
  
  return (
    <button
      className={`${baseStyles} ${variants[variant]} ${sizes[size]} ${className}`}
      {...props}
    >
      {children}
    </button>
  );
}

