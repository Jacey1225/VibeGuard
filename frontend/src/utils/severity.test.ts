import { describe, expect, it } from "vitest";
import { filterByStatus, sortFindingsBySeverity } from "./severity";
import type { Finding, Severity } from "../types";

function makeFinding(id: number, severity: Severity, status: Finding["status"] = "pending"): Finding {
  return { id, severity, title: `finding ${id}`, plain: "", status };
}

describe("sortFindingsBySeverity", () => {
  it("orders high before medium before low", () => {
    const findings = [makeFinding(1, "low"), makeFinding(2, "high"), makeFinding(3, "medium")];
    const sorted = sortFindingsBySeverity(findings);
    expect(sorted.map((f) => f.severity)).toEqual(["high", "medium", "low"]);
  });

  it("breaks ties deterministically by id, regardless of input order", () => {
    const findings = [makeFinding(5, "high"), makeFinding(2, "high"), makeFinding(9, "high")];
    const sorted = sortFindingsBySeverity(findings);
    expect(sorted.map((f) => f.id)).toEqual([2, 5, 9]);
  });

  it("does not mutate the input array", () => {
    const findings = [makeFinding(1, "low"), makeFinding(2, "high")];
    const copy = [...findings];
    sortFindingsBySeverity(findings);
    expect(findings).toEqual(copy);
  });

  it("stays correctly ordered on a large, shuffled fixture", () => {
    const severities: Severity[] = ["high", "medium", "low"];
    const findings: Finding[] = Array.from({ length: 500 }, (_, i) =>
      makeFinding(i, severities[(i * 37) % 3]),
    );
    const sorted = sortFindingsBySeverity(findings);
    const rank: Record<Severity, number> = { high: 0, medium: 1, low: 2 };
    for (let i = 1; i < sorted.length; i++) {
      expect(rank[sorted[i - 1].severity]).toBeLessThanOrEqual(rank[sorted[i].severity]);
      if (sorted[i - 1].severity === sorted[i].severity) {
        expect(sorted[i - 1].id).toBeLessThan(sorted[i].id);
      }
    }
  });
});

describe("filterByStatus", () => {
  it("returns only findings matching the given status", () => {
    const findings = [makeFinding(1, "high", "queued"), makeFinding(2, "medium", "pending"), makeFinding(3, "low", "queued")];
    expect(filterByStatus(findings, "queued").map((f) => f.id)).toEqual([1, 3]);
  });

  it("returns an empty array when nothing matches", () => {
    const findings = [makeFinding(1, "high", "pending")];
    expect(filterByStatus(findings, "skipped")).toEqual([]);
  });
});
