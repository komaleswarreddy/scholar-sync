/**
 * Input Component
 * 
 * Reusable input field following design tokens.
 */

import { InputHTMLAttributes } from 'react';

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  // Additional props can be added here
}

export function Input({ className = '', ...props }: InputProps) {
  return (
    <input
      className={`
        flex-1 
        bg-surface 
        border 
        border-border-default 
        rounded-full 
        px-4 
        py-2.5 
        text-text-primary 
        placeholder-text-tertiary 
        focus:outline-none 
        focus:border-border-active
        transition-colors
        ${className}
      `}
      {...props}
    />
  );
}

