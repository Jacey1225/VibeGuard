import { useMemo } from "react";
import type { VibecheckState } from "../../hooks/useVibecheckFlow";
import { useVibecheckFlow } from "../../hooks/useVibecheckFlow";
import { SEVERITY } from "../../data/fixtures";
import { sortFindingsBySeverity } from "../../utils/severity";
import { splitSnippet, sliceAround } from "../../utils/snippet";
import { FindingCard, type AnnotatedFinding } from "../findings/FindingCard";
import { FindingDots } from "../findings/FindingDots";
import { RealFindingsPanel } from "../findings/RealFindingsPanel";
import { WarningIcon, SpinnerIcon } from "../icons";

type Actions = ReturnType<typeof useVibecheckFlow>["actions"];

interface FindingsScreenProps {
  state: VibecheckState;
  actions: Actions;
}

/** Screen 2: reviewable stack of findings, worst-first, with Fix/Skip decisions. */
export function FindingsScreen({ state, actions }: FindingsScreenProps) {
  const stageH = state.stageH;
  const compact = stageH < 430;
  const codeRows = Math.max(3, Math.floor((stageH - 96) / 22));

  const sortedFindings = useMemo(() => sortFindingsBySeverity(state.findings), [state.findings]);
  const findingsCount = sortedFindings.length;
  const activeIndex = Math.max(0, Math.min(findingsCount - 1, state.activeFindingIndex));

  const annotated: AnnotatedFinding[] = useMemo(
    () =>
      sortedFindings.map((finding, i) => {
        const snip = splitSnippet(finding.id);
        const sliced = sliceAround(snip, codeRows - 1);
        return {
          finding,
          file: snip.file,
          fixSummary: snip.fixSummary,
          positionLabel: `${i + 1} of ${findingsCount}`,
          beforeLines: sliced.beforeLines,
          afterLines: sliced.afterLines,
          flag: snip.flag,
        };
      }),
    [sortedFindings, codeRows, findingsCount],
  );

  const queuedCount = state.findings.filter((f) => f.status === "queued").length;
  const noneQueued = queuedCount === 0;
  const skippedSerious = state.findings.filter((f) => f.status === "skipped" && f.severity === "high");

  const dotColorFor = (i: number) => {
    const f = sortedFindings[i];
    if (f.status === "queued") return "#35E0C8";
    if (f.status === "skipped") return "rgba(255,255,255,0.3)";
    return SEVERITY[f.severity].color;
  };

  if (state.realFindings.length > 0) {
    return <RealFindingsPanel state={state} actions={actions} />;
  }

  // A brief window right after an OAuth-redirect restore lands here
  // (screen 2) but before its findings have been re-fetched --
  // realFindings is still empty at that instant, which would otherwise
  // fall through to the fixture demo panel below.
  if (state.sessionRestoring) {
    return (
      <div style={{ flex: 1, minHeight: 0, display: "flex", alignItems: "center", justifyContent: "center", gap: 14 }}>
        <SpinnerIcon size={22} style={{ animation: "vc-spin 0.8s linear infinite" }} />
        <span style={{ fontSize: 15, color: "rgba(255,255,255,0.55)" }}>Resuming your check…</span>
      </div>
    );
  }

  return (
    <div style={{ flex: 1, minHeight: 0, display: "flex", flexDirection: "column", gap: 12, padding: "clamp(10px, 1.8vh, 20px) 0 clamp(6px, 1vh, 12px)" }}>
      <div style={{ flexShrink: 0, display: "flex", alignItems: "center", justifyContent: "space-between", gap: 20, flexWrap: "wrap" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 16, flexWrap: "wrap" }}>
          <span style={{ fontSize: 11.5, fontWeight: 700, letterSpacing: "0.22em", textTransform: "uppercase", color: "#35E0C8" }}>STEP 3</span>
          <span style={{ fontSize: 14.5, color: "rgba(255,255,255,0.55)" }}>
            {`${findingsCount} problems found · ${queuedCount} set to fix`}
          </span>
        </div>
        <button
          onClick={actions.approveFixes}
          disabled={noneQueued}
          style={
            noneQueued
              ? { background: "rgba(255,255,255,0.07)", color: "rgba(255,255,255,0.35)", border: "1px solid rgba(255,255,255,0.12)", height: 50, padding: "0 26px", borderRadius: 18, fontSize: 15.5, fontWeight: 700, cursor: "not-allowed", whiteSpace: "nowrap", fontFamily: "inherit" }
              : { background: "#35E0C8", color: "#04120F", border: "none", height: 50, padding: "0 28px", borderRadius: 18, fontSize: 15.5, fontWeight: 700, cursor: "pointer", whiteSpace: "nowrap", fontFamily: "inherit", transition: "all 0.13s ease" }
          }
        >
          {noneQueued ? "Pick at least one" : `Fix ${queuedCount} now`}
        </button>
      </div>

      {skippedSerious.length > 0 && (
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
            animation: "vc-fade-in 0.2s ease",
          }}
        >
          <WarningIcon size={19} style={{ flexShrink: 0 }} />
          <span style={{ fontSize: 14.5, color: "#FFD9D3", lineHeight: 1.4 }}>
            {skippedSerious.length === 1
              ? `You skipped a serious problem: ${skippedSerious[0].title.toLowerCase()}. We'd strongly recommend fixing this one.`
              : `You skipped ${skippedSerious.length} serious problems. We'd strongly recommend fixing them.`}
          </span>
        </div>
      )}

      <div ref={actions.setStageRef} style={{ position: "relative", flex: 1, minHeight: 0 }}>
        <div ref={actions.setScrollRef} onScroll={actions.handleFindingScroll} className="vc-noscroll" style={{ height: "100%", overflowY: "auto" }}>
          <div style={{ height: `${findingsCount * stageH}px`, position: "relative" }}>
            <div style={{ position: "sticky", top: 0, height: `${stageH}px` }}>
              <div style={{ position: "relative", width: "100%", height: "100%" }}>
                {annotated.map((data, i) => (
                  <FindingCard
                    key={data.finding.id}
                    data={data}
                    distanceFromActive={i - activeIndex}
                    compact={compact}
                    onFix={() => actions.setFindingStatus(data.finding.id, data.finding.status === "queued" ? "pending" : "queued", i)}
                    onSkip={() => actions.setFindingStatus(data.finding.id, data.finding.status === "skipped" ? "pending" : "skipped", i)}
                  />
                ))}
              </div>
            </div>
          </div>
        </div>
        <FindingDots count={findingsCount} activeIndex={activeIndex} colorFor={dotColorFor} onSelect={actions.scrollToFinding} labelPrefix="Problem" />
      </div>
    </div>
  );
}
