/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        matrix: {
          green: '#9fb943',      // Primary text - olive green
          darkgreen: '#5a8662',  // Secondary text - muted sage
          glow: '#b6c89f',       // Highlights/accents - pale sage
          dim: '#345530',        // Borders/muted elements - forest green
          bg: '#262d1e',         // Card backgrounds - very dark green
        }
      },
      fontFamily: {
        mono: ['JetBrains Mono', 'Fira Code', 'Monaco', 'Consolas', 'monospace'],
      },
      boxShadow: {
        'matrix': '0 0 10px rgba(159, 185, 67, 0.3)',
        'matrix-lg': '0 0 20px rgba(159, 185, 67, 0.4)',
      },
    },
  },
  plugins: [],
}
