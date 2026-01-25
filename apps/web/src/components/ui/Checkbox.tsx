/**
 * Checkbox Component
 * 
 * Custom checkbox following design tokens.
 */

import { InputHTMLAttributes } from 'react';

interface CheckboxProps extends Omit<InputHTMLAttributes<HTMLInputElement>, 'type'> {
  // Additional props can be added here
}

export function Checkbox({ className = '', ...props }: CheckboxProps) {
  return (
    <input
      type="checkbox"
      className={`
        w-4 h-4 
        rounded 
        border-border-default 
        bg-surface 
        text-accent-blue 
        focus:ring-2 
        focus:ring-accent-blue 
        focus:ring-offset-0 
        cursor-pointer
        ${className}
      `}
      {...props}
    />
  );
}




