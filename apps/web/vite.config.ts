import { defineConfig } from "vite";
import uniPlugin from "@dcloudio/vite-plugin-uni";

const uni = (uniPlugin as unknown as { default?: typeof uniPlugin }).default ?? uniPlugin;

export default defineConfig({
  plugins: [uni()],
  server: {
    port: 5173,
    strictPort: false,
    proxy: {
      "/api": {
        target: process.env.EMOTION_TALK_API_BASE_URL ?? "http://127.0.0.1:8000",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ""),
      },
    },
  },
});
