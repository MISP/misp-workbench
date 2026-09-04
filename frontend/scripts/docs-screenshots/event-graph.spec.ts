import { test, expect, Page } from "@playwright/test";
import { applyTheme, capture, pinForCapture } from "./helpers";
import { EVENT_UUIDS } from "./fixtures";

const FEATURE = "event-graph";

const EVENT_UUID = EVENT_UUIDS.emotetChain;

/**
 * The graph is a force simulation: nodes drift until it cools, and the view
 * refits itself once it settles. Screenshots taken before then differ run to
 * run, so each capture waits for the layout to stop moving.
 *
 * Settling is judged from the rendered node positions rather than a fixed
 * sleep - the simulation's own cooling time varies with node count.
 */
async function waitForGraph(page: Page, expectedNodes: number) {
  const nodes = page.locator(".pivotick-canvas .pivotick svg g.pvt-node");
  await expect(nodes).toHaveCount(expectedNodes, { timeout: 20_000 });

  let previous = "";
  await expect
    .poll(
      async () => {
        const current = await nodes.evaluateAll((els) =>
          els.map((el) => el.getAttribute("transform")).join("|"),
        );
        const settled = current === previous;
        previous = current;
        return settled;
      },
      { timeout: 20_000, intervals: [500] },
    )
    .toBe(true);
}

async function openGraph(page: Page) {
  await page.goto(`/events/${EVENT_UUID}/graph`);
  await expect(page.locator('[data-tab-panel="graph"]')).toBeVisible();
}

/** The graph card, so a capture frames the toolbar with the canvas. */
function graphCard(page: Page) {
  return page.locator('[data-tab-panel="graph"] .card');
}

async function selectViewMode(page: Page, label: string) {
  await page.getByRole("button", { name: label, exact: true }).click();
}

test.describe("Event graph screenshots", () => {
  test("1 — event view tabs", async ({ page }) => {
    await applyTheme(page);
    await page.goto(`/events/${EVENT_UUID}`);
    await expect(page.locator('[data-tab-panel="overview"]')).toBeVisible();

    // The tab strip with its counts, plus the title block above it.
    await expect(
      page.getByRole("button", { name: /Attributes/ }).locator(".badge"),
    ).toHaveText("9");
    await pinForCapture(page);

    await capture(page, FEATURE, "misp-workbench-1_event-graph-tabs", {
      fullPage: false,
    });
  });

  test("2 — detailed view", async ({ page }) => {
    await applyTheme(page);
    await openGraph(page);
    await waitForGraph(page, 15);
    await pinForCapture(page);

    await capture(
      graphCard(page),
      FEATURE,
      "misp-workbench-2_event-graph-detailed",
    );
  });

  test("3 — grouped view", async ({ page }) => {
    await applyTheme(page);
    await openGraph(page);
    await waitForGraph(page, 15);

    await selectViewMode(page, "Grouped");
    // Every parent's attributes and tags collapse behind one summary node
    // apiece, so 15 nodes become the event, its three objects and their
    // summaries.
    await waitForGraph(page, 9);
    await pinForCapture(page);

    await capture(
      graphCard(page),
      FEATURE,
      "misp-workbench-3_event-graph-grouped",
    );
  });

  test("4 — relations view", async ({ page }) => {
    await applyTheme(page);
    await openGraph(page);
    await waitForGraph(page, 15);

    await selectViewMode(page, "Relations");
    // Only what takes part in an object reference: the three objects, no
    // event root, no tags, no standalone attributes.
    await waitForGraph(page, 3);
    await expect(page.getByText("contains")).toBeVisible();
    await expect(page.getByText("communicates-with")).toBeVisible();
    await pinForCapture(page);

    await capture(
      graphCard(page),
      FEATURE,
      "misp-workbench-4_event-graph-relations",
    );
  });
});
