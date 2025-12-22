/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './templates/**/*.html',
    './node_modules/flowbite/**/*.js'
  ],
  darkMode: 'class',
  theme: {
    // Golden Ratio (1.618) Typography Scale with 18px base
    fontSize: {
      'xs': ['10px', { lineHeight: '1.5' }],
      'sm': ['14px', { lineHeight: '1.5' }],
      'base': ['18px', { lineHeight: '1.6' }],
      'lg': ['29px', { lineHeight: '1.3' }],
      'xl': ['47px', { lineHeight: '1.15' }],
      '2xl': ['76px', { lineHeight: '1.05' }],
      // Additional sizes for flexibility
      '2xs': ['11px', { lineHeight: '1.5' }],
      'md': ['23px', { lineHeight: '1.4' }],
    },
    extend: {
      fontFamily: {
        // Headers - Roboto Condensed
        'heading': ['"Roboto Condensed"', 'Arial Narrow', 'sans-serif'],
        // Body copy - Roboto Mono
        'body': ['"Roboto Mono"', 'ui-monospace', 'monospace'],
        // Sans fallback
        'sans': ['"Roboto Mono"', 'ui-monospace', 'monospace'],
      },
      colors: {
        // Multicam Brand Colors (from Flowbite theme generator)
        brand: {
          50: '#f8f7f7',
          100: '#eeedec',
          200: '#e0dcd7',
          300: '#d2c6b6',
          400: '#bdab93',
          500: '#a88f71',
          600: '#8e7657',
          700: '#756148',
          800: '#594936',
          900: '#3f3427',
          950: '#28221b',
        },
        // Primary uses brand colors
        primary: {
          50: '#f8f7f7',
          100: '#eeedec',
          200: '#e0dcd7',
          300: '#d2c6b6',
          400: '#bdab93',
          500: '#a88f71',
          600: '#8e7657',
          700: '#756148',
          800: '#594936',
          900: '#3f3427',
          950: '#28221b',
        },
        // Original Multicam palette for accents
        multicam: {
          sand: '#C4B396',
          olive: '#5C5844',
          brown: '#6B5C4A',
          green: '#4A5442',
          tan: '#D4C5A9',
        },
        // Status colors - full scales
        success: {
          50: '#ecfdf5',
          100: '#d1fae5',
          200: '#a7f3d0',
          300: '#6ee7b7',
          400: '#34d399',
          500: '#10b981',
          600: '#059669',
          700: '#047857',
          800: '#065f46',
          900: '#064e3b',
        },
        warning: {
          50: '#fffbeb',
          100: '#fef3c7',
          200: '#fde68a',
          300: '#fcd34d',
          400: '#fbbf24',
          500: '#f59e0b',
          600: '#d97706',
          700: '#b45309',
          800: '#92400e',
          900: '#78350f',
        },
        error: {
          50: '#fef2f2',
          100: '#fee2e2',
          200: '#fecaca',
          300: '#fca5a5',
          400: '#f87171',
          500: '#ef4444',
          600: '#dc2626',
          700: '#b91c1c',
          800: '#991b1b',
          900: '#7f1d1d',
        },
        info: {
          50: '#eff6ff',
          100: '#dbeafe',
          200: '#bfdbfe',
          300: '#93c5fd',
          400: '#60a5fa',
          500: '#3b82f6',
          600: '#2563eb',
          700: '#1d4ed8',
          800: '#1e40af',
          900: '#1e3a8a',
        },
      },
      // Border radius - larger, more rounded (matching Flowbite theme)
      borderRadius: {
        'none': '0px',
        'sm': '8px',
        'DEFAULT': '16px',
        'md': '16px',
        'lg': '20px',
        'xl': '24px',
        '2xl': '32px',
        '3xl': '40px',
        'full': '9999px',
      },
      // Border width
      borderWidth: {
        'DEFAULT': '2px',
        '0': '0px',
        '1': '1px',
        '2': '2px',
        '3': '3px',
        '4': '4px',
      },
      // Spacing adjustments
      spacing: {
        '18': '4.5rem',
        '88': '22rem',
        '128': '32rem',
      },
    },
  },
  plugins: [
    require('flowbite/plugin')
  ],
}

