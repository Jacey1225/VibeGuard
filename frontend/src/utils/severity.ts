import type { Finding, Severity } from "../types";

const SEVERITY_RANK: Record<Severity, number> = { high: 0, medium: 1, low: 2 };

/**
 * Sorts findings worst-first (high, then medium, then low), with a stable
 * secondary key (id) so tie order never depends on incidental array order.
 */
export function sortFindingsBySeverity(findings: readonly Finding[]): Finding[] {
  return [...findings].sort((a, b) => {
    const rankDiff = SEVERITY_RANK[a.severity] - SEVERITY_RANK[b.severity];
    return rankDiff !== 0 ? rankDiff : a.id - b.id;
  });
}

export function filterByStatus(findings: readonly Finding[], status: Finding["status"]): Finding[] {
  return findings.filter((f) => f.status === status);
}
