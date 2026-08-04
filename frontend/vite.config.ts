import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  preview: {
    host: true,
    // Vite 6+ blocks preview-server requests by Host header unless
    // explicitly allowed (DNS-rebinding protection) -- needed to serve
    // traffic from Render's *.onrender.com domain instead of localhost.
    allowedHosts: [".onrender.com"],
  },
});
