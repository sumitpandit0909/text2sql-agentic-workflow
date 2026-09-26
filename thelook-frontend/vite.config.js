import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      // Frontend calls /chat, /health directly; Vite proxies to your FastAPI backend
      // running on localhost:8000 during local dev, so no CORS config needed there.
      "/chat": "http://localhost:8000",
      "/health": "http://localhost:8000",
    },
  },
});
