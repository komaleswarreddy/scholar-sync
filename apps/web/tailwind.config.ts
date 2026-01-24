import type { Config } from 'tailwindcss';

const config: Config = {
  content: [
    './src/pages/**/*.{js,ts,jsx,tsx,mdx}',
    './src/components/**/*.{js,ts,jsx,tsx,mdx}',
    './src/app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        // Design Tokens using CSS variables for theme switching
        // Backgrounds
        background: 'var(--color-background)',
        surface: 'var(--color-surface)',
        'surface-hover': 'var(--color-surface-hover)',
        modal: 'var(--color-modal)',
        
        // Borders
        'border-default': 'var(--color-border-default)',
        'border-active': 'var(--color-border-active)',
        
        // Typography
        'text-primary': 'var(--color-text-primary)',
        'text-secondary': 'var(--color-text-secondary)',
        'text-tertiary': 'var(--color-text-tertiary)',
        
        // Accents
        'accent-blue': 'var(--color-accent-blue)',
        'accent-green': 'var(--color-accent-green)',
        'citation-badge': 'var(--color-citation-badge)',
      },
      fontFamily: {
        sans: ['var(--font-inter)', 'Google Sans', 'Inter', 'system-ui', 'sans-serif'],
      },
      fontSize: {
        // Design spec typography scale
        'xs': ['12px', { lineHeight: '16px', letterSpacing: '0' }],      // Metadata, Citations
        'sm': ['14px', { lineHeight: '20px', letterSpacing: '0' }],      // Sidebar items, Input text
        'base': ['16px', { lineHeight: '24px', letterSpacing: '0' }],    // Chat body, General reading
        'lg': ['18px', { lineHeight: '28px', letterSpacing: '0' }],      // Card Titles
        'xl': ['20px', { lineHeight: '28px', letterSpacing: '0' }],     // Section Headers
        '2xl': ['24px', { lineHeight: '32px', letterSpacing: '0' }],    // Welcome Message
      },
      letterSpacing: {
        'tight': '-0.01em',
        'normal': '0',
        'wide': '0.01em',
      },
      borderRadius: {
        'lg': '8px',      // Small buttons (design spec)
        'xl': '12px',     // Cards, Modals (design spec)
        '2xl': '16px',    // Chat bubbles (design spec)
        '3xl': '24px',    // Large containers (used for main layout)
      },
      spacing: {
        // Standard Tailwind spacing scale is used throughout
        // Common values: 1 (4px), 2 (8px), 3 (12px), 4 (16px), 6 (24px), 8 (32px)
        // Fractional values (1.5, 2.5) are valid Tailwind classes and used for fine-tuning
      },
      screens: {
        // Standard Tailwind breakpoints
        'sm': '640px',   // Small devices (tablets)
        'md': '768px',   // Medium devices (small laptops)
        'lg': '1024px',  // Large devices (laptops)
        'xl': '1280px',  // Extra large devices (desktops)
        '2xl': '1536px', // 2X large devices (large desktops)
      },
    },
  },
  plugins: [],
};

export default config;

