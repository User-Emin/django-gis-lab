import { defineConfig } from "vite";

// Dev: Vite op 5180, /api gaat via een proxy naar Django op 8700 (geen CORS nodig).
// Build (`npm run build`): naar de static-map van Django. `base` is de URL waaronder Django die
// bestanden serveert (STATIC_URL + "app/"); `manifest` laat Django de gehashte bestandsnamen vinden.
export default defineConfig(({ command }) => ({
  base: command === "build" ? "/static/app/" : "/",
  build: {
    outDir: "../kaart/static/app",
    emptyOutDir: true,
    manifest: true,
    rollupOptions: { input: ["src/main.ts", "src/tekening.ts"] },
  },
  server: {
    host: "127.0.0.1",
    port: 5180,
    strictPort: true,
    proxy: { "/api": "http://127.0.0.1:8700" },
  },
}));
