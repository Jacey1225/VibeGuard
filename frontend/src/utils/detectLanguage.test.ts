import { describe, expect, it } from "vitest";
import { detectLanguage } from "./detectLanguage";

describe("detectLanguage", () => {
  it("returns empty string for blank input", () => {
    expect(detectLanguage("   ")).toBe("");
  });

  it("detects JavaScript from a const declaration", () => {
    expect(detectLanguage("const x = createClient(url, key)")).toBe("JavaScript");
  });

  it("detects TypeScript from a type annotation", () => {
    expect(detectLanguage("function f(x: number): string { return String(x) }")).toBe("TypeScript");
  });

  it("detects Python from a def/import", () => {
    expect(detectLanguage("def handler():\n    import os\n    print('hi')")).toBe("Python");
  });

  it("detects SQL from a SELECT statement", () => {
    expect(detectLanguage("SELECT * FROM users WHERE id = 1")).toBe("SQL");
  });

  it("detects JSON from an object literal with quoted keys", () => {
    expect(detectLanguage('{"name": "vibeguard", "version": 1}')).toBe("JSON");
  });

  it("falls back to Code for unrecognized text", () => {
    expect(detectLanguage("just some plain words here")).toBe("Code");
  });
});
