import { execFileSync } from "node:child_process";

/**
 * Run before every Playwright invocation of the docs-screenshots suite —
 * single-spec or umbrella — to ensure the docs fixtures (events, hunts,
 * audit-log rows) are fresh.
 *
 * Why this is necessary specifically for audit-logs: the audit log feed is
 * sorted by `created_at` desc and only the first 25 rows render on page 1.
 * The seed command timestamps the four `_docs_fixture` audit entries at
 * 2/4/6/8 minutes ago, which keeps them at the top of page 1 regardless of
 * accumulated activity from prior test sessions. Without this hook the
 * umbrella `docs:screenshots` skips reseeding and the audit-logs spec
 * fails because the fixture rows have been pushed off page 1.
 *
 * Skippable via DOCS_SCREENSHOTS_SKIP_SEED=1 — useful when iterating on a
 * spec that doesn't touch fixture state and you want to save the ~3s
 * docker-exec round-trip.
 */
export default async function globalSetup() {
  if (process.env.DOCS_SCREENSHOTS_SKIP_SEED === "1") {
    console.log(
      "[docs-screenshots] DOCS_SCREENSHOTS_SKIP_SEED=1 — skipping seed",
    );
    return;
  }

  console.log("[docs-screenshots] Seeding docs fixtures…");
  // execFileSync with an args array — no shell interpolation, no injection
  // surface even if any of these args were ever made dynamic.
  try {
    execFileSync(
      "docker",
      [
        "compose",
        "exec",
        "api",
        "poetry",
        "run",
        "python",
        "-m",
        "app.cli",
        "seed-docs-fixtures",
      ],
      { stdio: "inherit" },
    );
  } catch (err) {
    console.error(
      "[docs-screenshots] Seed failed. Is the dev stack running? " +
        "Start it with `docker compose -f docker-compose.yml -f docker-compose.dev.yml --env-file=.env.dev up`",
    );
    throw err;
  }
}
