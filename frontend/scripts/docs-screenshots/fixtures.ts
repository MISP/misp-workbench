import path from "node:path";

/**
 * Mirrors api/app/cli/__main__.py:DOCS_USER_EMAIL / DOCS_USER_PASSWORD.
 * Keep in sync if the seed command's defaults change.
 */
export const DOCS_USER = {
  email: "admin@admin.test",
  password: "admin",
};

export const SCREENSHOTS_DIR = path.resolve(
  __dirname,
  "..",
  "..",
  "..",
  "docs",
  "screenshots",
);

export const EVENT_UUIDS = {
  cobaltStrike: "a1f30000-0001-4001-8000-000000000001",
  wannacry: "a1f30000-0001-4001-8000-000000000002",
  phishing: "a1f30000-0001-4001-8000-000000000003",
};

export const HUNT_NAMES = {
  opensearch: "IP and domain indicators",
  cpe: "Microsoft Exchange Server vulnerabilities",
  mitre: "MITRE ATT&CK — Spearphishing Attachment (T1566.001)",
  rulezet: "Detection rules for CVE-2024-3400",
};
