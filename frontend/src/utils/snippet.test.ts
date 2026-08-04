import { describe, expect, it } from "vitest";
import { mapContextLine, sliceAround, splitSnippet } from "./snippet";

describe("splitSnippet", () => {
  it("splits fixture 1 around its flagged line", () => {
    const snip = splitSnippet(1);
    expect(snip.file).toBe("src/lib/db.js");
    expect(snip.flag.num).toBe(14);
    expect(snip.flag.text).toBe("  'sbp_service_role_51f9a3c2'");
    expect(snip.before.at(-1)?.num).toBe(13);
    expect(snip.after[0]?.num).toBe(15);
  });
});

describe("mapContextLine", () => {
  it("replaces an empty line's text with a non-breaking space so it still renders", () => {
    expect(mapContextLine({ num: 3, text: "" })).toEqual({ num: 3, text: " " });
  });

  it("leaves non-empty text untouched", () => {
    expect(mapContextLine({ num: 3, text: "const x = 1" })).toEqual({ num: 3, text: "const x = 1" });
  });
});

describe("sliceAround", () => {
  it("trims before/after context down to the given row budget", () => {
    const snip = splitSnippet(1);
    const sliced = sliceAround(snip, 4);
    expect(sliced.beforeLines.length + sliced.afterLines.length).toBeLessThanOrEqual(4);
    expect(sliced.beforeLines.length).toBeGreaterThan(0);
  });

  it("never asks for more lines than the snippet actually has", () => {
    const snip = splitSnippet(3);
    const sliced = sliceAround(snip, 50);
    expect(sliced.beforeLines.length).toBeLessThanOrEqual(snip.before.length);
    expect(sliced.afterLines.length).toBeLessThanOrEqual(snip.after.length);
  });

  it("always keeps at least one row of context even for a budget of zero or less", () => {
    const snip = splitSnippet(2);
    const sliced = sliceAround(snip, 0);
    expect(sliced.beforeLines.length).toBeGreaterThanOrEqual(1);
  });
});
