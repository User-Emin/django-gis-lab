import { defineConfig } from "vite";

// Dev: Vite op 5180, /api gaat via een proxy naar Django op 8700 (geen CORS nodig).
export default defineConfig({
  server: {
    host: "127.0.0.1",
    port: 5180,
    strictPort: true,
    proxy: { "/api": "http://127.0.0.1:8700" },
  },
});
