import { useMemo } from "react";
import type { VibecheckState } from "../../hooks/useVibecheckFlow";
import type { RepositoryFile } from "../../hooks/useVibecheckFlow";
import { useVibecheckFlow } from "../../hooks/useVibecheckFlow";
import { FILES, SCAN_MESSAGES } from "../../data/fixtures";
import { detectLanguage } from "../../utils/detectLanguage";
import { FileIcon, SpinnerIcon } from "../icons";

type Actions = ReturnType<typeof useVibecheckFlow>["actions"];

interface ScanningScreenProps {
  state: VibecheckState;
  actions: Actions;
}

type FileScanStatus = "queued" | "scanning" | "done";

interface ScanSummary {
  total: number;
  critical: number;
  high: number;
  medium: number;
  low: number;
  info: number;
}

const SEVERITY_COLORS: Record<keyof Omit<ScanSummary, "total">, string> = {
  critical: "#FF5C5C",
  high: "#FFCE74",
  medium: "#FFE074",
  low: "#7FD8C4",
  info: "rgba(255,255,255,0.4)",
};

function parseScanSummary(scanResults: string): ScanSummary | null {
  const totalMatch = scanResults.match(/Total Issues Found:\s*(\d+)/i);
  if (!totalMatch) return null;
  const criticalMatch = scanResults.match(/Critical:\s*(\d+)/i);
  const highMatch = scanResults.match(/High:\s*(\d+)/i);
  const mediumMatch = scanResults.match(/Medium:\s*(\d+)/i);
  const lowMatch = scanResults.match(/Low:\s*(\d+)/i);
  const infoMatch = scanResults.match(/Info:\s*(\d+)/i);
  return {
    total: parseInt(totalMatch[1], 10),
    critical: criticalMatch ? parseInt(criticalMatch[1], 10) : 0,
    high: highMatch ? parseInt(highMatch[1], 10) : 0,
    medium: mediumMatch ? parseInt(mediumMatch[1], 10) : 0,
    low: lowMatch ? parseInt(lowMatch[1], 10) : 0,
    info: infoMatch ? parseInt(infoMatch[1], 10) : 0,
  };
}

/** Screen 1: animated per-file scan progress over actual files and display API results. */
export function ScanningScreen({ state, actions }: ScanningScreenProps) {
  const tick = state.pipelineTick;

  const activeFiles = useMemo(() => {
    if (state.attached && state.attachedFiles.length > 0) {
      return state.attachedFiles.filter((f) => !("isEllipsis" in f && f.isEllipsis));
    }
    const pastedLang = detectLanguage(state.codeInput) || "Code";
    return [{ name: pastedLang, language: pastedLang }];
  }, [state.attached, state.attachedFiles, state.codeInput]);

  const resultsReady = state.pipelineDone && !state.scanResultsLoading;

  const summary = useMemo(() => {
    if (!resultsReady || !state.scanResults) return null;
    return parseScanSummary(state.scanResults);
  }, [resultsReady, state.scanResults]);

  return (
    <div style={{ flex: 1, minHeight: 0, display: "flex", flexDirection: "column", justifyContent: "center", gap: "clamp(16px, 2.6vh, 32px)" }}>
      <div style={{ flexShrink: 0, display: "flex", flexDirection: "column", gap: 10 }}>
        <span style={{ flexShrink: 0, fontSize: 11.5, fontWeight: 700, letterSpacing: "0.22em", textTransform: "uppercase", color: "#35E0C8" }}>
          STEP 2
        </span>
        <h1 style={{ margin: 0, fontSize: "clamp(26px, min(3.2vw, 5vh), 44px)", fontWeight: 700, letterSpacing: "-0.03em", lineHeight: 1.05 }}>
          {resultsReady ? "Summary" : state.pipelineDone ? "Analyzing results…" : "Reading through your files…"}
        </h1>

        {state.pipelineDone && !resultsReady && (
          <div style={{ display: "flex", alignItems: "center", gap: 12, marginTop: 4, animation: "vc-fade-in 0.2s ease" }}>
            <SpinnerIcon size={20} />
            <span style={{ fontSize: 14.5, color: "rgba(255,255,255,0.55)" }}>
              Running the real VibeGuard scan — this can take a moment…
            </span>
          </div>
        )}

        {summary && (
          <div style={{ display: "flex", flexDirection: "column", gap: 12, marginTop: 6, animation: "vc-fade-in 0.25s ease" }}>
            <div style={{ display: "flex", alignItems: "baseline", gap: 12 }}>
              <span style={{ fontSize: "clamp(34px, 4vw, 54px)", fontWeight: 700, letterSpacing: "-0.04em", lineHeight: 1, color: summary.total > 0 ? "#FFCE74" : "#FFFFFF" }}>
                {summary.total}
              </span>
              <span style={{ fontSize: 15, color: "rgba(255,255,255,0.5)" }}>problems found</span>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 18, flexWrap: "wrap" }}>
              {(Object.keys(SEVERITY_COLORS) as Array<keyof Omit<ScanSummary, "total">>).map((key) => (
                <div key={key} style={{ display: "flex", alignItems: "center", gap: 7 }}>
                  <span style={{ width: 8, height: 8, borderRadius: "50%", background: SEVERITY_COLORS[key], flexShrink: 0 }} />
                  <span style={{ fontSize: 13.5, color: "rgba(255,255,255,0.7)" }}>
                    {key[0].toUpperCase() + key.slice(1)}: <span style={{ fontWeight: 700, color: "rgba(255,255,255,0.95)" }}>{summary[key]}</span>
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      <div
        style={{
          flexShrink: 0,
          display: "grid",
          gridTemplateColumns: `repeat(${activeFiles.length}, minmax(0, 1fr))`,
          gap: "clamp(10px, 1.4vw, 20px)",
          maxWidth: activeFiles.length === 1 ? 360 : "none",
          width: "100%",
        }}
      >
        {activeFiles.map((f, idx) => {
          const status: FileScanStatus = tick < idx * 2 ? "queued" : tick < idx * 2 + 2 ? "scanning" : "done";
          return (
            <div
              key={f.name}
              style={{
                position: "relative",
                overflow: "hidden",
                borderRadius: 24,
                padding: "18px 20px",
                boxSizing: "border-box",
                background: "rgba(255,255,255,0.035)",
                border: `1px solid ${status === "scanning" ? "rgba(53,224,200,0.45)" : "rgba(255,255,255,0.1)"}`,
                backdropFilter: "blur(16px)",
                WebkitBackdropFilter: "blur(16px)",
                opacity: status === "queued" ? 0.5 : 1,
                transition: "all 0.22s ease",
              }}
            >
              {status === "scanning" && (
                <div style={{ position: "absolute", inset: 0, overflow: "hidden", pointerEvents: "none", borderRadius: 24 }}>
                  <div
                    style={{
                      position: "absolute",
                      top: 0,
                      bottom: 0,
                      width: "45%",
                      background: "linear-gradient(90deg, rgba(53,224,200,0) 0%, rgba(53,224,200,0.20) 50%, rgba(53,224,200,0) 100%)",
                      animation: "vc-scanline 1.1s linear infinite",
                    }}
                  />
                </div>
              )}
              <div style={{ position: "relative", display: "flex", alignItems: "center", gap: 10 }}>
                <FileIcon size={16} style={{ flexShrink: 0 }} />
                <span style={{ fontSize: 14, fontWeight: 600, color: "rgba(255,255,255,0.85)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", flex: 1, minWidth: 0 }}>
                  {f.name}
                </span>
              </div>
              <div style={{ position: "relative", display: "flex", alignItems: "center", justifyContent: "space-between", gap: 10, marginTop: 14 }}>
                <span style={{ fontSize: 13, color: status === "scanning" ? "#35E0C8" : "rgba(255,255,255,0.42)" }}>
                  {status === "queued" ? "Waiting" : status === "scanning" ? "Scanning…" : "Scanned"}
                </span>
                <span style={{ fontSize: 11, color: "rgba(255,255,255,0.5)" }}>{f.language}</span>
              </div>
            </div>
          );
        })}
      </div>

      {resultsReady && state.scanResults && (
        <div style={{ flex: 1, minHeight: 0, display: "flex", flexDirection: "column", gap: 12, animation: "vc-fade-in 0.3s ease" }}>
          <span style={{ fontSize: 12, fontWeight: 600, color: "rgba(255,255,255,0.5)", textTransform: "uppercase", letterSpacing: "0.06em" }}>
            Scan Results
          </span>
          <textarea
            value={state.scanResults}
            readOnly
            style={{
              flex: 1,
              width: "100%",
              padding: "16px",
              borderRadius: 16,
              background: "rgba(255,255,255,0.04)",
              border: "1px solid rgba(255,255,255,0.1)",
              color: "#FFFFFF",
              fontFamily: "monospace",
              fontSize: 13,
              lineHeight: 1.6,
              resize: "none",
              outline: "none",
              overflowY: "auto",
            }}
          />
        </div>
      )}

      <div style={{ flexShrink: 0, display: "flex", alignItems: "center", gap: 20, flexWrap: "wrap", minHeight: 54 }}>
        {!state.pipelineDone && (
          <p style={{ margin: 0, fontSize: 15.5, color: "rgba(255,255,255,0.55)", animation: "vc-fade-in 0.2s ease" }}>
            {SCAN_MESSAGES[Math.min(SCAN_MESSAGES.length - 1, tick)]}
          </p>
        )}
        {resultsReady && (
          <div style={{ display: "flex", alignItems: "center", gap: 20, flexWrap: "wrap", animation: "vc-fade-in 0.2s ease" }}>
            {summary && summary.total === 0 ? (
              <button
                onClick={actions.resetFlow}
                style={{
                  flexShrink: 0,
                  whiteSpace: "nowrap",
                  background: "#35E0C8",
                  color: "#04120F",
                  border: "none",
                  height: 54,
                  padding: "0 32px",
                  borderRadius: 18,
                  fontSize: 16.5,
                  fontWeight: 700,
                  cursor: "pointer",
                  fontFamily: "inherit",
                  transition: "background 0.15s ease, transform 0.12s ease",
                }}
              >
                Check Another App
              </button>
            ) : (
              <button
                onClick={actions.goToFindings}
                style={{
                  flexShrink: 0,
                  whiteSpace: "nowrap",
                  background: "#35E0C8",
                  color: "#04120F",
                  border: "none",
                  height: 54,
                  padding: "0 32px",
                  borderRadius: 18,
                  fontSize: 16.5,
                  fontWeight: 700,
                  cursor: "pointer",
                  fontFamily: "inherit",
                  transition: "background 0.15s ease, transform 0.12s ease",
                }}
              >
                Review
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
