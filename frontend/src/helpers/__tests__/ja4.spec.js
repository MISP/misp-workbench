// @vitest-environment node
import { describe, expect, it } from "vitest";
import { couldBeJa4, detectJa4Variant } from "@/helpers/ja4";

const JA4 = "t13d1516h2_8daaf6152771_b186095e22b6";

// the same cases as api/app/tests/services/test_ja4.py
describe("detectJa4Variant", () => {
  it.each([
    [JA4, "JA4"],
    [`  ${JA4.toUpperCase()} `, "JA4"],
    ["q13d0310h3_55b375c5d22e_cd85d2d88918", "JA4"],
    ["t130200_1301_a56c5b993250", "JA4S"],
    ["ge11cn20enus_60ca1bd65281_ac95b44401d9_8df6a44f726c", "JA4H"],
    ["a373a9f83c6b_2bab15409345_7bf9a7bf7029", "JA4X"],
    ["c76s76_c71s59_c0s70", "JA4SSH"],
    ["4289_64", null],
    ["hello world", null],
    [JA4.slice(0, -1), null],
    ["t13d١516h2_8daaf6152771_b186095e22b6", null],
  ])("%s is %s", (value, variant) => {
    expect(detectJa4Variant(value)).toBe(variant);
  });
});

describe("couldBeJa4", () => {
  it.each([JA4, JA4.toUpperCase(), "4289_64", "1024_2-4-8-1-3_1460_4"])(
    "accepts %s",
    (value) => expect(couldBeJa4(value)).toBe(true),
  );

  it.each(["", "  ", `ja4=${JA4}`, `"${JA4}"`, "t13d 1516h2"])(
    "rejects %s",
    (value) => expect(couldBeJa4(value)).toBe(false),
  );
});
