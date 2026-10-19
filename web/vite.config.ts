import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

// Em desenvolvimento (npm run dev), as chamadas /api vão para o backend Python.
// Por padrão ele roda em http://127.0.0.1:8001 (python run.py); mude com API_TARGET.
const apiTarget = process.env.API_TARGET ?? "http://127.0.0.1:8001";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: { "/api": apiTarget },
  },
  test: {
    environment: "node",
  },
});
