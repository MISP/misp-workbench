import { fileURLToPath, URL } from "node:url";

import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import vueJsx from "@vitejs/plugin-vue-jsx";

// https://vitejs.dev/config/
export default defineConfig({
  build: {
    outDir: "dist",
    emptyOutDir: true,
  },
  plugins: [vue(), vueJsx()],
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
      // Pivotick ships no npm package, so it is built from the pinned
      // submodule by `npm run build:pivotick` and resolved from its output.
      // The ES entry re-exports a sibling chunk, so the whole dist has to
      // stay together. The stylesheet entry has to come first: a string alias
      // also matches `<key>/...`, so a leading `pivotick` would swallow it.
      "pivotick/dist/pivotick.css": fileURLToPath(
        new URL("./submodules/pivotick/dist/pivotick.css", import.meta.url),
      ),
      pivotick: fileURLToPath(
        new URL("./submodules/pivotick/dist/pivotick.es.js", import.meta.url),
      ),
    },
  },
  server: {
    port: 3001,
  },
  optimizeDeps: {
    include: ["tom-select"],
  },
});
