import { useMemo, useState } from "react";
import type { VibecheckState, RealFindingSeverity } from "../../hooks/useVibecheckFlow";
import { useVibecheckFlow } from "../../hooks/useVibecheckFlow";
import { RealFindingCard } from "./RealFindingCard";

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

  // Selection defaults to "all findings selected to fix" -- initialized once
  // from the findings this panel mounted with. The panel remounts fresh on
  // every new scan (App only renders it while screen === 2), so this never
  // goes stale against a later scan's findings.
  const [selected, setSelected] = useState<Set<number>>(() => new Set(sorted.map((f) => f.id)));

  const toggle = (id: number) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const selectedCount = selected.size;
  const totalCount = sorted.length;

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
      </div>

      <div className="vc-noscroll" style={{ flex: 1, minHeight: 0, overflowY: "auto", display: "flex", flexDirection: "column", gap: 14 }}>
        {sorted.map((finding) => (
          <RealFindingCard
            key={finding.id}
            finding={finding}
            owner={owner}
            repo={repo}
            checked={selected.has(finding.id)}
            onToggle={() => toggle(finding.id)}
          />
        ))}
      </div>
    </div>
  );
}
