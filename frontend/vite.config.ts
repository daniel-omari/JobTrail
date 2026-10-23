import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Dev only: Vite on :5173 forwards /api to the FastAPI backend on :8000.
// For the demo, `npm run build` outputs static files that FastAPI serves itself (one origin).
export default defineConfig({
  plugins: [react()],
  server: { host: "127.0.0.1", proxy: { "/api": "http://127.0.0.1:8000" } },
  build: { outDir: "dist", emptyOutDir: true, assetsInlineLimit: 0 },
});
