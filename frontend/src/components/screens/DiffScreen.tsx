import { useMemo } from "react";
import type { VibecheckState } from "../../hooks/useVibecheckFlow";
import { useVibecheckFlow } from "../../hooks/useVibecheckFlow";
import { splitSnippet, sliceAround } from "../../utils/snippet";
import { DiffCard, type DiffBlockData } from "../diff/DiffCard";
import { FindingDots } from "../findings/FindingDots";
import { RealRemediationReviewScreen } from "./RealRemediationReviewScreen";

type Actions = ReturnType<typeof useVibecheckFlow>["actions"];

interface DiffScreenProps {
  state: VibecheckState;
  actions: Actions;
}

/** Screen 4: before/after diff review for every fix that was applied, then "send". Real-findings path renders RealRemediationReviewScreen instead. */
export function DiffScreen({ state, actions }: DiffScreenProps) {
  const stageH = state.stageH;
  const compact = stageH < 430;
  const codeRows = Math.max(3, Math.floor((stageH - 96) / 22));

  const queuedFindings = useMemo(() => state.findings.filter((f) => f.status === "queued"), [state.findings]);
  const queuedCount = queuedFindings.length;
  const activeIndex = Math.max(0, Math.min(Math.max(0, queuedCount - 1), state.activeDiffIndex));

  const blocks: DiffBlockData[] = useMemo(
    () =>
      queuedFindings.map((f, i) => {
        const snip = splitSnippet(f.id);
        const sliced = sliceAround(snip, codeRows - 2);
        return {
          title: f.title,
          file: snip.file,
          fixSummary: snip.doneSummary,
          positionLabel: `Change ${i + 1} of ${queuedCount}`,
          beforeLines: sliced.beforeLines,
          afterLines: sliced.afterLines,
          minusText: snip.flag.text,
          plusText: snip.fixedLine,
        };
      }),
    [queuedFindings, codeRows, queuedCount],
  );

  if (state.realFindings.length > 0) {
    return <RealRemediationReviewScreen state={state} actions={actions} />;
  }

  return (
    <div style={{ flex: 1, minHeight: 0, display: "flex", flexDirection: "column", gap: 12, padding: "clamp(10px, 1.8vh, 20px) 0 clamp(6px, 1vh, 12px)" }}>
      <div style={{ flexShrink: 0, display: "flex", alignItems: "center", justifyContent: "space-between", gap: 20, flexWrap: "wrap" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 16, flexWrap: "wrap" }}>
          <span style={{ fontSize: 11.5, fontWeight: 700, letterSpacing: "0.22em", textTransform: "uppercase", color: "#35E0C8" }}>Step 5 — what changed</span>
          <span style={{ fontSize: 14.5, color: "rgba(255,255,255,0.55)" }}>
            {queuedCount === 1 ? "1 fix ready to send" : `${queuedCount} fixes ready to send`}
          </span>
        </div>
        <button
          onClick={actions.openPR}
          style={{
            flexShrink: 0,
            whiteSpace: "nowrap",
            background: "#35E0C8",
            color: "#04120F",
            border: "none",
            height: 52,
            padding: "0 30px",
            borderRadius: 18,
            fontSize: 16,
            fontWeight: 700,
            cursor: "pointer",
            fontFamily: "inherit",
            transition: "background 0.15s ease, transform 0.12s ease",
          }}
        >
          Send these changes
        </button>
      </div>

      <div ref={actions.setStageRef} style={{ position: "relative", flex: 1, minHeight: 0 }}>
        <div ref={actions.setDiffScrollRef} onScroll={actions.handleDiffScroll} className="vc-noscroll" style={{ height: "100%", overflowY: "auto" }}>
          <div style={{ height: `${Math.max(1, blocks.length) * stageH}px`, position: "relative" }}>
            <div style={{ position: "sticky", top: 0, height: `${stageH}px` }}>
              <div style={{ position: "relative", width: "100%", height: "100%" }}>
                {blocks.map((data, i) => (
                  <DiffCard key={i} data={data} distanceFromActive={i - activeIndex} compact={compact} />
                ))}
              </div>
            </div>
          </div>
        </div>
        <FindingDots count={blocks.length} activeIndex={activeIndex} colorFor={() => "#35E0C8"} onSelect={actions.scrollToDiff} labelPrefix="Change" />
      </div>
    </div>
  );
}
