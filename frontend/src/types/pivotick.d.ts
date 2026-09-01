/**
 * Pivotick is built from the pinned submodule (see `npm run build:pivotick`)
 * and resolved through the `pivotick` alias in vite.config.mts.
 *
 * Upstream type-checks with `noEmit: true`, so its build produces no `.d.ts`
 * files and there are no types to re-use. These shorthand declarations keep
 * the imports resolvable; everything comes through untyped. Replace them with
 * the real declarations once upstream emits them.
 *
 * Exports: `Pivotick`, `Node`, `Edge`, `UIComponent`, `ColorPaletteMapper`.
 * API reference: https://pivotick.github.io/Pivotick/
 */
declare module "pivotick";
declare module "pivotick/dist/pivotick.css";
