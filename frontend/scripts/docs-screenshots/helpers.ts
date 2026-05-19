import { Page, Locator } from "@playwright/test";
import fs from "node:fs";
import path from "node:path";
import { SCREENSHOTS_DIR } from "./fixtures";

export type CaptureTarget = Page | Locator;

/**
 * Write a PNG to docs/screenshots/<feature>/<name>.png.
 * Creates the feature directory if missing. Disables animations to keep
 * captures byte-stable across runs.
 */
export async function capture(
  target: CaptureTarget,
  feature: string,
  name: string,
  options: { fullPage?: boolean } = {},
): Promise<void> {
  const featureDir = path.join(SCREENSHOTS_DIR, feature);
  fs.mkdirSync(featureDir, { recursive: true });
  const filePath = path.join(featureDir, `${name}.png`);

  await target.screenshot({
    path: filePath,
    animations: "disabled",
    caret: "hide",
    scale: "device",
    fullPage: options.fullPage ?? false,
  });
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
