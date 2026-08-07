import { useMemo } from "react";
import type { VibecheckState, RealFindingSeverity } from "../../hooks/useVibecheckFlow";
import { useVibecheckFlow } from "../../hooks/useVibecheckFlow";
import { RealFindingCard } from "./RealFindingCard";
import { WarningIcon } from "../icons";

type Actions = ReturnType<typeof useVibecheckFlow>["actions"];

interface RealFindingsPanelProps {
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

/** Screen 2 (real-data path): every finding from an actual VibeGuard scan, worst-first, each selectable with a live file preview. */
export function RealFindingsPanel({ state, actions }: RealFindingsPanelProps) {
  const { owner, repo } = useMemo(() => {
    const parts = state.sourceLabel.replace("https://github.com/", "").split("/");
    return { owner: parts[0] ?? "", repo: parts[1] ?? "" };
  }, [state.sourceLabel]);

  const sorted = useMemo(
    () => [...state.realFindings].sort((a, b) => SEVERITY_RANK[a.severity] - SEVERITY_RANK[b.severity]),
    [state.realFindings],
  );

  // Selection lives in shared flow state (state.selectedFindingIds,
  // defaulted to "all findings selected" when the findings were fetched)
  // rather than panel-local state, so it composes with
  // actions.startRemediation -- see useVibecheckFlow.ts.
  const selected = state.selectedFindingIds;
  const selectedCount = selected.size;
  const totalCount = sorted.length;
  const canProceed = selectedCount > 0 && !state.remediationLoading;

  return (
    <div style={{ flex: 1, minHeight: 0, display: "flex", flexDirection: "column", gap: 16, padding: "clamp(10px, 1.8vh, 20px) 0 clamp(6px, 1vh, 12px)" }}>
      <div style={{ flexShrink: 0, display: "flex", alignItems: "center", justifyContent: "space-between", gap: 20, flexWrap: "wrap" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 16, flexWrap: "wrap" }}>
          <span style={{ fontSize: 11.5, fontWeight: 700, letterSpacing: "0.22em", textTransform: "uppercase", color: "#35E0C8" }}>STEP 3</span>
          <span style={{ fontSize: 14.5, color: "rgba(255,255,255,0.55)" }}>
            {totalCount === 1 ? "1 problem found" : `${totalCount} problems found`} in {owner}/{repo}
          </span>
          <span
            style={{
              fontSize: 13,
              fontWeight: 700,
              color: "#35E0C8",
              background: "rgba(53,224,200,0.12)",
              border: "1px solid rgba(53,224,200,0.32)",
              borderRadius: 999,
              padding: "5px 14px",
              whiteSpace: "nowrap",
            }}
          >
            {selectedCount}/{totalCount} Fixes to Resolve
          </span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 10, flexShrink: 0 }}>
          <button
            onClick={actions.resetFlow}
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
            Check Another App
          </button>
          <button
            onClick={actions.startRemediation}
            disabled={!canProceed}
            title={state.sessionToken ? undefined : "Signs you in with GitHub first"}
            style={
              canProceed
                ? {
                    flexShrink: 0,
                    whiteSpace: "nowrap",
                    background: "#35E0C8",
                    color: "#04120F",
                    border: "none",
                    height: 46,
                    padding: "0 24px",
                    borderRadius: 16,
                    fontSize: 14.5,
                    fontWeight: 700,
                    cursor: "pointer",
                    fontFamily: "inherit",
                    transition: "background 0.13s ease",
                  }
                : {
                    flexShrink: 0,
                    whiteSpace: "nowrap",
                    background: "rgba(255,255,255,0.07)",
                    color: "rgba(255,255,255,0.35)",
                    border: "1px solid rgba(255,255,255,0.12)",
                    height: 46,
                    padding: "0 24px",
                    borderRadius: 16,
                    fontSize: 14.5,
                    fontWeight: 700,
                    cursor: "not-allowed",
                    fontFamily: "inherit",
                  }
            }
          >
            {state.remediationLoading
              ? "Generating fixes…"
              : state.sessionToken
                ? `Fix ${selectedCount} now`
                : `Sign in & fix ${selectedCount}`}
          </button>
        </div>
      </div>

      {state.remediationError && (
        <div
          style={{
            flexShrink: 0,
            display: "flex",
            alignItems: "center",
            gap: 12,
            background: "rgba(255,107,90,0.12)",
            border: "1px solid rgba(255,107,90,0.4)",
            borderRadius: 18,
            padding: "12px 18px",
          }}
        >
          <WarningIcon size={19} style={{ flexShrink: 0 }} />
          <span style={{ fontSize: 14.5, color: "#FFD9D3", lineHeight: 1.4 }}>{state.remediationError}</span>
        </div>
      )}

      <div className="vc-noscroll" style={{ flex: 1, minHeight: 0, overflowY: "auto", display: "flex", flexDirection: "column", gap: 14 }}>
        {sorted.map((finding) => (
          <RealFindingCard
            key={finding.id}
            finding={finding}
            repoId={state.repoId}
            checked={selected.has(finding.id)}
            onToggle={() => actions.toggleFindingSelection(finding.id)}
          />
        ))}
      </div>
    </div>
  );
}
