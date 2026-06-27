import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Dev server proxies /api to the FastAPI backend (default port 8000).
// `base: "./"` makes the built dist work when served by FastAPI at "/".
export default defineConfig({
  plugins: [react()],
  base: "./",
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: process.env.BACKEND_URL || "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },
});
