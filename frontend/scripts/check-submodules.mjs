// Fails early, with the fix spelled out, when the frontend's git submodules
// were never checked out. Without this, a plain `git clone` gets as far as
// `npm ci` in submodules/pivotick and dies with an npm usage error about a
// missing package-lock.json, which says nothing about submodules.
// See https://github.com/MISP/misp-workbench/issues/496
import { existsSync } from "node:fs";
import { fileURLToPath } from "node:url";

const required = [
  "submodules/pivotick/package-lock.json",
  "submodules/pivotick-graph-transformer/packages/core/src/index.ts",
];

const root = fileURLToPath(new URL("..", import.meta.url));
const missing = required.filter((path) => !existsSync(root + path));

if (missing.length) {
  console.error(
    [
      "",
      "The frontend's git submodules are not checked out. Missing:",
      ...missing.map((path) => `  frontend/${path}`),
      "",
      "From the repository root, run:",
      "",
      "  git submodule update --init",
      "",
      "then build again.",
      "",
    ].join("\n"),
  );
  process.exit(1);
}
