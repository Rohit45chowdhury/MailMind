/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: { navy: { 900: '#0a1230', 800: '#0f1b45', 700: '#18275c' } },
      keyframes: {
        bob: { '0%,100%': { transform: 'translateY(0)' }, '50%': { transform: 'translateY(-10px)' } },
        load: { '0%': { transform: 'translateX(-100%)' }, '100%': { transform: 'translateX(250%)' } },
      },
      animation: { bob: 'bob 1.6s ease-in-out infinite', load: 'load 1.4s ease-in-out infinite' },
    },
  },
  plugins: [],
}
