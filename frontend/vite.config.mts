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
      // pivotick-graph-transformer turns MISP-standard JSON into the
      // nodes/edges pivotick renders. Also a submodule, but unlike pivotick
      // it ships no build - Vite transpiles its TypeScript sources directly,
      // so these point at the package entries. `/misp` first, for the same
      // prefix-matching reason as the stylesheet above; `pivotick` itself
      // cannot swallow either, since a string alias only matches the exact
      // key or the key followed by a slash.
      "pivotick-transformer/misp": fileURLToPath(
        new URL(
          "./submodules/pivotick-graph-transformer/packages/misp/src/index.ts",
          import.meta.url,
        ),
      ),
      "pivotick-transformer": fileURLToPath(
        new URL(
          "./submodules/pivotick-graph-transformer/packages/core/src/index.ts",
          import.meta.url,
        ),
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
