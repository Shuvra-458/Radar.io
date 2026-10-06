import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const BACKEND = process.env.VITE_BACKEND_URL ?? "http://backend:8000";

export default defineConfig({
    plugins: [react()],
    server: {
        port: 5173,
        strictPort: true,
        proxy: {
            "/analyze": { target: BACKEND, changeOrigin: true },
            "/health": { target: BACKEND, changeOrigin: true },
        },
    },
});
