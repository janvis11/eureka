/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        sans: ['"Space Grotesk"', 'system-ui', 'sans-serif']
      },
      colors: {
        charcoal: '#0A0A0A'
      }
    }
  },
  plugins: []
};

