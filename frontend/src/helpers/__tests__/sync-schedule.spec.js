// @vitest-environment node
import { describe, expect, it } from "vitest";
import { describeSyncSchedule } from "@/helpers/sync-schedule";

describe("describeSyncSchedule", () => {
  it.each([
    [0, "manually"],
    [null, "manually"],
    [15, "every 15 minutes"],
    [60, "hourly"],
    [360, "every 6 hours"],
    [1440, "daily"],
    [2880, "every 2 days"],
    [10080, "weekly"],
    [90, "every 90 minutes"],
  ])("%s minutes reads %s", (minutes, words) => {
    expect(describeSyncSchedule(minutes)).toBe(words);
  });
});
