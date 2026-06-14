/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#f5f7ff',
          100: '#ebf0ff',
          200: '#d6e0ff',
          300: '#adc2ff',
          400: '#859eff',
          500: '#5c75ff', // Harmonious custom indigo primary color
          600: '#3d4eff',
          700: '#2430eb',
          850: '#151aa6',
          900: '#0f107a',
        }
      }
    },
  },
  plugins: [],
}
