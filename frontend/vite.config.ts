import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import { defineConfig } from "vite";

const API_TARGET = process.env.API_TARGET ?? "http://127.0.0.1:8000";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    fs: { allow: [".."] }, // the contract fixtures live in ../contracts
    proxy: {
      "/api": API_TARGET,
      "/health": API_TARGET,
    },
  },
});
