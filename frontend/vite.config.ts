import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
const rawBase = process.env.VITE_BASE || "/";
const base = rawBase.endsWith("/") ? rawBase : `${rawBase}/`;
export default defineConfig({
  base,
  plugins: [react()],
  server: { port: 5173, proxy: { "/api": "http://127.0.0.1:5000" } },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: "./src/test/setup.ts",
  },
});
