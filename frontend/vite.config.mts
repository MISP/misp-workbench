import { fileURLToPath, URL } from "node:url";

import { defineConfig, type Plugin } from "vite";
import vue from "@vitejs/plugin-vue";
import vueJsx from "@vitejs/plugin-vue-jsx";

// Pivotick's dropdown styles pass a literal colour where a custom property
// name is expected (`dropdown-item-variant(#00000000, ...)`), so its built
// stylesheet contains `var(rgba(0, 0, 0, 0))`. Browsers just drop the
// declaration, but Vite 8 minifies CSS with lightningcss, which rejects it and
// fails the production build. Unwrap `var(<literal colour>)` to the colour
// itself until upstream fixes it (still present in pivotick v3.0.0).
// See https://github.com/MISP/misp-workbench/issues/496
function fixPivotickCss(): Plugin {
  return {
    name: "fix-pivotick-css",
    enforce: "pre",
    transform(code, id) {
      if (!id.split("?")[0].endsWith("/submodules/pivotick/dist/pivotick.css"))
        return null;
      return {
        code: code.replace(
          /var\(\s*((?:rgba?|hsla?)\([^()]*\)|#[0-9a-fA-F]{3,8})\s*\)/g,
          "$1",
        ),
        map: null,
      };
    },
  };
}

// https://vitejs.dev/config/
export default defineConfig({
  build: {
    outDir: "dist",
    emptyOutDir: true,
  },
  plugins: [fixPivotickCss(), vue(), vueJsx()],
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
