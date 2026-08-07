import { useMemo } from "react";
import type { RealFindingSeverity, VibecheckState } from "../../hooks/useVibecheckFlow";
import { useVibecheckFlow } from "../../hooks/useVibecheckFlow";
import { SnippetFindingCard } from "./SnippetFindingCard";
import { CheckCircleFilledIcon } from "../icons";

type Actions = ReturnType<typeof useVibecheckFlow>["actions"];

interface SnippetFindingsPanelProps {
  state: VibecheckState;
  actions: Actions;
}

const SEVERITY_RANK: Record<RealFindingSeverity, number> = {
  critical: 0,
  high: 1,
  medium: 2,
  low: 3,
  info: 4,
};

/**
 * Screen 2 (snippet-scan path): every finding from a real, GitHub-free
 * `POST /snippets` -> `POST /snippets/{id}/scan` scan, worst-first, each
 * with its own fix-submission control. No selection/checkbox and no bulk
 * "fix now" step -- unlike `RealFindingsPanel` there's no batch remediation
 * call this feeds, since each fix is submitted independently per finding.
 */
export function SnippetFindingsPanel({ state, actions }: SnippetFindingsPanelProps) {
  const sorted = useMemo(
    () => [...state.snippetFindings].sort((a, b) => SEVERITY_RANK[a.severity] - SEVERITY_RANK[b.severity]),
    [state.snippetFindings],
  );
  const totalCount = sorted.length;

  return (
    <div style={{ flex: 1, minHeight: 0, display: "flex", flexDirection: "column", gap: 16, padding: "clamp(10px, 1.8vh, 20px) 0 clamp(6px, 1vh, 12px)" }}>
      <div style={{ flexShrink: 0, display: "flex", alignItems: "center", justifyContent: "space-between", gap: 20, flexWrap: "wrap" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 16, flexWrap: "wrap" }}>
          <span style={{ fontSize: 11.5, fontWeight: 700, letterSpacing: "0.22em", textTransform: "uppercase", color: "#35E0C8" }}>STEP 3</span>
          <span style={{ fontSize: 14.5, color: "rgba(255,255,255,0.55)" }}>
            {totalCount === 1 ? "1 problem found" : `${totalCount} problems found`} in pasted code
          </span>
        </div>
        <button
          onClick={actions.resetSnippetFlow}
          style={{
            flexShrink: 0,
            whiteSpace: "nowrap",
            background: "rgba(255,255,255,0.07)",
            color: "rgba(255,255,255,0.85)",
            border: "1px solid rgba(255,255,255,0.16)",
            height: 46,
            padding: "0 22px",
            borderRadius: 16,
            fontSize: 14.5,
            fontWeight: 700,
            cursor: "pointer",
            fontFamily: "inherit",
            transition: "background 0.13s ease",
          }}
        >
          Scan Another Snippet
        </button>
      </div>

      {totalCount === 0 ? (
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            gap: 10,
            borderRadius: 18,
            padding: "22px 18px",
            background: "rgba(255,255,255,0.05)",
          }}
        >
          <CheckCircleFilledIcon size={20} />
          <span style={{ fontSize: 15, color: "rgba(255,255,255,0.8)" }}>No vulnerabilities found in this snippet.</span>
        </div>
      ) : (
        <div className="vc-noscroll" style={{ flex: 1, minHeight: 0, overflowY: "auto", display: "flex", flexDirection: "column", gap: 14 }}>
          {sorted.map((finding) => (
            <SnippetFindingCard
              key={finding.id}
              finding={finding}
              snippetContent={state.snippetContent}
              snippetId={state.snippetId ?? ""}
            />
          ))}
        </div>
      )}
    </div>
  );
}
