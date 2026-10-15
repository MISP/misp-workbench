import { test, expect } from "@playwright/test";
import { applyTheme, capture, pinForCapture } from "./helpers";

const FEATURE = "navigation";

test.describe("Navigation screenshots", () => {
  test.beforeEach(async ({ page }) => {
    await applyTheme(page);
  });

  test("1 — a category's menu, its section highlighted", async ({ page }) => {
    // Only the navbar and the open menu: the page under it isn't the point.
    await page.setViewportSize({ width: 1400, height: 380 });
    await page.goto("/indicators");
    await page.locator("#nav-intel").click();
    await expect(page.locator(".app-mega-menu.show")).toBeVisible();
    await page.locator(".app-mega-item.active").hover();
    await pinForCapture(page);

    await capture(page, FEATURE, "misp-workbench-1_navigation_menu");
  });

  test("2 — quick switcher", async ({ page }) => {
    await page.setViewportSize({ width: 1400, height: 700 });
    await page.goto("/explore");
    await page.keyboard.press("Control+k");
    const switcher = page.locator(".switcher");
    await expect(switcher).toBeVisible();
    await switcher.locator("input").fill("ex");
    await expect(switcher.locator(".switcher-item").first()).toBeVisible();
    await pinForCapture(page);

    await capture(
      switcher,
      FEATURE,
      "misp-workbench-2_navigation_quick-switcher",
    );
  });

  test("3 — mobile menu", async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto("/feeds");
    await page.getByRole("button", { name: "Open menu" }).click();
    const menu = page.locator("#mobileMenu");
    await expect(menu).toHaveClass(/show/);
    await pinForCapture(page);

    await capture(menu, FEATURE, "misp-workbench-3_navigation_mobile");
  });
});
