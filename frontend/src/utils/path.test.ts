import { describe, expect, it } from "vitest";
import { normalizeRelativePath } from "./path";

describe("normalizeRelativePath", () => {
  it("converts backslashes to forward slashes", () => {
    expect(normalizeRelativePath("src\\app\\main.py")).toBe("src/app/main.py");
  });

  it("leaves an already-forward-slash path unchanged", () => {
    expect(normalizeRelativePath("src/app/main.py")).toBe("src/app/main.py");
  });

  it("leaves a path with no separators unchanged", () => {
    expect(normalizeRelativePath("main.py")).toBe("main.py");
  });
});
