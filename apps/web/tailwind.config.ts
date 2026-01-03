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
        // Material Design 3 Dark Mode (NotebookLM)
        google: {
          dark: '#131314',
        },
        'surface-google': '#1E1F20',
        'surface-highlight': '#28292A',
        
        // Backgrounds
        background: '#131314',
        surface: '#1E1F20',
        'surface-hover': '#28292A',
        modal: '#1E1F20',
        
        // Borders
        'border-default': '#2D2D2D',
        'border-active': '#3D3D3D',
        
        // Typography
        'text-primary': '#E3E3E3',
        'text-secondary': '#C4C7C5',
        'text-tertiary': '#9AA0A6',
        
        // Accents
        'accent-blue': '#A8C7FA',
        'accent-green': '#C4EED0',
        'citation-badge': '#2D2D2D',
      },
      fontFamily: {
        sans: ['Google Sans', 'Inter', 'system-ui', 'sans-serif'],
      },
      borderRadius: {
        'lg': '8px',
        'xl': '12px',
        '2xl': '16px',
        '3xl': '24px',
      },
    },
  },
  plugins: [],
};

export default config;

