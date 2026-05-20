import { Page, Locator, test } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";
import { SCREENSHOTS_DIR } from "./fixtures";

export type CaptureTarget = Page | Locator;
type Theme = "light" | "dark";

function currentTheme(): Theme {
  const meta = test.info().project.metadata as { theme?: string } | undefined;
  return meta?.theme === "dark" ? "dark" : "light";
}

/**
 * Write a PNG to docs/screenshots/<feature>/<name>.png (light theme) or
 * <name>-dark.png (dark theme). The dark variant pairs with the mkdocs-
 * material `#only-light` / `#only-dark` image suffix convention so the doc
 * shows the right one based on the reader's selected palette.
 */
export async function capture(
  target: CaptureTarget,
  feature: string,
  name: string,
  options: { fullPage?: boolean } = {},
): Promise<void> {
  const featureDir = path.join(SCREENSHOTS_DIR, feature);
  fs.mkdirSync(featureDir, { recursive: true });
  const suffix = currentTheme() === "dark" ? "-dark" : "";
  const filePath = path.join(featureDir, `${name}${suffix}.png`);

  await target.screenshot({
    path: filePath,
    animations: "disabled",
    caret: "hide",
    scale: "device",
    fullPage: options.fullPage ?? false,
  });
}

/**
 * Install an init script that sets the app's theme (light/dark) before any
 * page script runs. Reads the theme from the current project's metadata, so
 * the `screenshots-light` / `screenshots-dark` projects capture the same
 * specs against their respective palettes.
 *
 * Call this in beforeEach BEFORE page.goto().
 */
export async function applyTheme(page: Page): Promise<void> {
  const theme = currentTheme();
  await page.addInitScript((t: string) => {
    localStorage.setItem("theme", t);
    document.documentElement.setAttribute("data-bs-theme", t);
  }, theme);
}

/**
 * Stylesheet that mutes blinking carets, transitions and animations during
 * captures so consecutive runs produce identical PNGs.
 */
export async function pinForCapture(page: Page): Promise<void> {
  await page.addStyleTag({
    content: `
      *, *::before, *::after {
        animation-duration: 0s !important;
        animation-delay: 0s !important;
        transition-duration: 0s !important;
        transition-delay: 0s !important;
        caret-color: transparent !important;
      }
    `,
  });
}
