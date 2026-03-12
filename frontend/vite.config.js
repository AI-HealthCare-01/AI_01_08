import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const apiProxy = process.env.VITE_API_PROXY || "http://127.0.0.1:8002";

export default defineConfig(({ command }) => ({
  // Use root base in dev to avoid double-prefixing paths.
  base: command === "serve" ? "/" : "/auth-demo/app/",
  plugins: [react()],
  server: {
    port: 5173,
    strictPort: true,
    proxy: {
      "/api": {
        target: apiProxy,
        changeOrigin: true
      }
    }
  },
  build: {
    outDir: "../app/ui/auth-demo",
    emptyOutDir: true
  }
}));
