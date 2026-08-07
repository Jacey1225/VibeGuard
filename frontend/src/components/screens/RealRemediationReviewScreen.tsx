import { useMemo } from "react";
import type { VibecheckState } from "../../hooks/useVibecheckFlow";
import { useVibecheckFlow } from "../../hooks/useVibecheckFlow";
import { normalizeRelativePath } from "../../utils/path";
import { RemediationCard } from "../remediation/RemediationCard";
import { WarningIcon } from "../icons";

type Actions = ReturnType<typeof useVibecheckFlow>["actions"];

interface RealRemediationReviewScreenProps {
  state: VibecheckState;
  actions: Actions;
}

/**
 * Screen 4 (real-data path): review and approve/reject each generated
 * remediation -- the real-data counterpart to DiffScreen. Remediation is
 * generated per findings-bearing *file* (`POST /repositories/{id}/remediate`
 * has no per-finding selection param), so this narrows the full result set
 * down to files that contain at least one of the user's selected findings
 * from the Decide screen, which is the closest honest match to "selected
 * findings" the backend's file-level granularity supports.
 */
export function RealRemediationReviewScreen({ state, actions }: RealRemediationReviewScreenProps) {
  const selectedPaths = useMemo(() => {
    const paths = new Set<string>();
    for (const finding of state.realFindings) {
      if (state.selectedFindingIds.has(finding.id)) paths.add(normalizeRelativePath(finding.relative_path));
    }
    return paths;
  }, [state.realFindings, state.selectedFindingIds]);

  const visible = useMemo(
    () => state.realRemediations.filter((r) => selectedPaths.size === 0 || selectedPaths.has(normalizeRelativePath(r.relative_path))),
    [state.realRemediations, selectedPaths],
  );

  const summary = state.remediationSummary;

  return (
    <div style={{ flex: 1, minHeight: 0, display: "flex", flexDirection: "column", gap: 12, padding: "clamp(10px, 1.8vh, 20px) 0 clamp(6px, 1vh, 12px)" }}>
      <div style={{ flexShrink: 0, display: "flex", alignItems: "center", justifyContent: "space-between", gap: 20, flexWrap: "wrap" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 16, flexWrap: "wrap" }}>
          <span style={{ fontSize: 11.5, fontWeight: 700, letterSpacing: "0.22em", textTransform: "uppercase", color: "#35E0C8" }}>Step 5 — review & decide</span>
          <span style={{ fontSize: 14.5, color: "rgba(255,255,255,0.55)" }}>
            {visible.length === 1 ? "1 fix ready for review" : `${visible.length} fixes ready for review`}
            {summary && summary.filesOverCap > 0 ? ` · ${summary.filesOverCap} file(s) skipped (over the per-remediation call cap)` : ""}
          </span>
        </div>
        <button
          onClick={actions.finishRemediationReview}
          style={{
            flexShrink: 0,
            whiteSpace: "nowrap",
            background: "#35E0C8",
            color: "#04120F",
            border: "none",
            height: 50,
            padding: "0 28px",
            borderRadius: 18,
            fontSize: 15.5,
            fontWeight: 700,
            cursor: "pointer",
            fontFamily: "inherit",
          }}
        >
          Done reviewing
        </button>
      </div>

      {state.remediationError && (
        <div style={{ flexShrink: 0, display: "flex", alignItems: "center", gap: 12, background: "rgba(255,107,90,0.12)", border: "1px solid rgba(255,107,90,0.4)", borderRadius: 18, padding: "12px 18px" }}>
          <WarningIcon size={19} style={{ flexShrink: 0 }} />
          <span style={{ fontSize: 14.5, color: "#FFD9D3", lineHeight: 1.4 }}>{state.remediationError}</span>
        </div>
      )}

      {visible.length === 0 ? (
        <div style={{ flex: 1, display: "flex", alignItems: "center", justifyContent: "center", color: "rgba(255,255,255,0.45)", fontSize: 15 }}>
          No fixes were generated for your selected findings' files.
        </div>
      ) : (
        <div className="vc-noscroll" style={{ flex: 1, minHeight: 0, overflowY: "auto", display: "flex", flexDirection: "column", gap: 14 }}>
          {visible.map((remediation) => (
            <RemediationCard
              key={remediation.id}
              remediation={remediation}
              deciding={state.decidingRemediationIds.has(remediation.id)}
              onApprove={() => actions.decideRemediation(remediation.id, "approve")}
              onReject={() => actions.decideRemediation(remediation.id, "reject")}
            />
          ))}
        </div>
      )}
    </div>
  );
}
