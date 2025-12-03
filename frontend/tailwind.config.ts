import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        surface: {
          DEFAULT: "#030305", // Deep Space Black
          glass: "rgba(20, 20, 20, 0.6)",
        },
        status: {
          success: "#00E676", // Neon Green
          error: "#FF3B30",   // Neon Red
          warning: "#FF9F0A", // Neon Orange
          ai: "#BD00FF",      // AI Purple
          live: "#FF3B30",    // Live Recording Red
        },
        text: {
          primary: "#FFFFFF",
          secondary: "rgba(255, 255, 255, 0.6)",
        }
      },
      backgroundImage: {
        'glass-gradient': 'linear-gradient(180deg, rgba(255, 255, 255, 0.08) 0%, rgba(255, 255, 255, 0.01) 100%)',
        'ai-gradient': 'linear-gradient(135deg, #BD00FF 0%, #00F0FF 100%)',
      },
      boxShadow: {
        'neon-green': '0 0 20px rgba(0, 230, 118, 0.3)',
        'neon-red': '0 0 20px rgba(255, 59, 48, 0.3)',
        'neon-ai': '0 0 30px rgba(189, 0, 255, 0.25)',
        'glass-edge': 'inset 0 1px 0 0 rgba(255, 255, 255, 0.1)',
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
      },
    },
  },
  plugins: [],
};
export default config;
