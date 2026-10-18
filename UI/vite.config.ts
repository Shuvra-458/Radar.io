import { defineConfig, loadEnv } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig(({ mode }) => {
  
  const env = loadEnv(mode, process.cwd(), "");
  
 
  const BACKEND = env.VITE_BACKEND_URL || "http://backend:8000";

  return {
    plugins: [react()],
    server: {
      port: 5173,
      strictPort: true,
      proxy: {
        "/analyze": { target: BACKEND, changeOrigin: true },
        "/health": { target: BACKEND, changeOrigin: true },
      },
    },
  };
});