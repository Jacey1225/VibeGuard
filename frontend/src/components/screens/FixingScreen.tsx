import { useMemo } from "react";
import type { VibecheckState } from "../../hooks/useVibecheckFlow";
import { splitSnippet, sliceAround } from "../../utils/snippet";
import { FixCard, type FixBlockData } from "../fixing/FixCard";
import { CheckCircleFilledIcon, SpinnerIcon } from "../icons";

interface FixingScreenProps {
  state: VibecheckState;
}

/** Screen 3: simulated fix-in-progress stack, one card per queued finding, then a validate step. */
export function FixingScreen({ state }: FixingScreenProps) {
  const stageH = state.stageH;
  const codeRows = Math.max(3, Math.floor((stageH - 96) / 22));

  const fixSteps = useMemo(() => state.implementSteps.filter((s) => s.kind === "fix"), [state.implementSteps]);
  const runningFixIdx = fixSteps.findIndex((s) => s.status === "running");
  const lastDoneFixIdx = fixSteps.reduce((acc, s, i) => (s.status === "done" ? i : acc), -1);
  const focusFixIdx = runningFixIdx !== -1 ? runningFixIdx : Math.max(0, lastDoneFixIdx);

  const blocks: FixBlockData[] = useMemo(
    () =>
      fixSteps.map((step) => {
        const snip = splitSnippet(step.findingId!);
        const finding = state.findings.find((f) => f.id === step.findingId);
        const done = step.status === "done";
        const running = step.status === "running";
        const sliced = sliceAround(snip, Math.max(2, codeRows - 4));
        return {
          title: finding?.title ?? "",
          num: snip.flag.num,
          origText: snip.flag.text,
          fixedText: snip.fixedLine,
          beforeLines: sliced.beforeLines,
          afterLines: sliced.afterLines,
          done,
          running,
          caption: done ? snip.doneSummary : snip.working,
        };
      }),
    [fixSteps, state.findings, codeRows],
  );

  const validateStep = state.implementSteps.find((s) => s.kind === "validate") ?? { status: "pending" as const };
  const validateDone = validateStep.status === "done";
  const validateRunning = validateStep.status === "running";
  const doneFixCount = fixSteps.filter((s) => s.status === "done").length;

  return (
    <div style={{ flex: 1, minHeight: 0, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: "clamp(12px, 2vh, 24px)" }}>
      <div style={{ flexShrink: 0, display: "flex", flexDirection: "column", alignItems: "center", gap: 6, textAlign: "center" }}>
        <span style={{ fontSize: 11.5, fontWeight: 700, letterSpacing: "0.22em", textTransform: "uppercase", color: "#35E0C8" }}>Step 4 — fixing</span>
        <h1 style={{ margin: 0, fontSize: "clamp(21px, min(2.8vw, 4.4vh), 38px)", fontWeight: 700, letterSpacing: "-0.03em", lineHeight: 1.05 }}>
          {state.implementDone ? "All done. Checking nothing else broke…" : `Fixing ${Math.min(doneFixCount + 1, fixSteps.length)} of ${fixSteps.length}`}
        </h1>
      </div>

      <div style={{ position: "relative", width: "100%", maxWidth: 940, flex: 1, minHeight: 0 }}>
        {blocks.map((data, i) => (
          <FixCard key={i} data={data} distanceFromFocus={i - focusFixIdx} />
        ))}
      </div>

      <div style={{ flexShrink: 0, display: "flex", alignItems: "center", gap: 18, flexWrap: "wrap", justifyContent: "center" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 9 }}>
          {fixSteps.map((s, i) => (
            <div
              key={i}
              title={`Fix ${i + 1} of ${fixSteps.length}`}
              style={{
                width: i === focusFixIdx ? 30 : 18,
                height: 5,
                borderRadius: 3,
                background: s.status === "done" ? "#35E0C8" : s.status === "running" ? "rgba(53,224,200,0.7)" : "rgba(255,255,255,0.16)",
                transition: "all 0.22s ease",
              }}
            />
          ))}
        </div>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 11,
            padding: "12px 22px",
            borderRadius: 999,
            background: validateDone ? "rgba(53,224,200,0.08)" : "rgba(255,255,255,0.035)",
            border: `1px solid ${validateDone ? "rgba(53,224,200,0.35)" : "rgba(255,255,255,0.1)"}`,
            transition: "all 0.22s ease",
          }}
        >
          {validateDone && <CheckCircleFilledIcon size={17} />}
          {validateRunning && <SpinnerIcon size={16} style={{ animation: "vc-spin 0.8s linear infinite" }} />}
          <span
            style={{
              fontSize: 15,
              fontWeight: validateRunning || validateDone ? 700 : 500,
              color: validateDone ? "#7FF0E0" : validateRunning ? "#FFFFFF" : "rgba(255,255,255,0.4)",
            }}
          >
            {validateDone ? "Checked — your app still works exactly as before" : validateRunning ? "Making sure nothing else broke…" : "Safety check waiting"}
          </span>
        </div>
      </div>
    </div>
  );
}
