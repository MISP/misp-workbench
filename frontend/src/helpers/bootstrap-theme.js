import { onBeforeUnmount, onMounted, readonly, ref } from "vue";

/**
 * The Bootstrap theme currently in force, as a reactive `"light" | "dark"`.
 *
 * The app switches themes by swapping `data-bs-theme` on `<html>`. Anything
 * that reads a colour once - a canvas, a graph node baked at build time -
 * has to be told when that happens, which is what this watches for.
 */
export function readBootstrapTheme() {
  return document.documentElement.getAttribute("data-bs-theme") === "dark"
    ? "dark"
    : "light";
}

export function useBootstrapTheme() {
  const theme = ref(readBootstrapTheme());

  let observer = null;

  onMounted(() => {
    observer = new MutationObserver(() => {
      const next = readBootstrapTheme();

      if (next !== theme.value) {
        theme.value = next;
      }
    });
    observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ["data-bs-theme"],
    });
  });

  onBeforeUnmount(() => {
    observer?.disconnect();
    observer = null;
  });

  return readonly(theme);
}
