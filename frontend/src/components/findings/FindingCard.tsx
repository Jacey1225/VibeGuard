import type { CSSProperties } from "react";
import type { CodeSnippetLine, Finding, FindingStatus } from "../../types";
import { SEVERITY } from "../../data/fixtures";
import { FileIcon, CheckThinIcon } from "../icons";
import { FONT } from "../../styles/tokens";

export interface AnnotatedFinding {
  finding: Finding;
  file: string;
  fixSummary: string;
  positionLabel: string;
  beforeLines: CodeSnippetLine[];
  afterLines: CodeSnippetLine[];
  flag: CodeSnippetLine;
}

interface FindingCardProps {
  data: AnnotatedFinding;
  distanceFromActive: number;
  compact: boolean;
  onFix: () => void;
  onSkip: () => void;
}

function displayStatus(status: FindingStatus): "queued" | "skipped" | "pending" {
  return status === "queued" || status === "skipped" ? status : "pending";
}

/** One finding in the review stack: severity, plain-English summary, and its code context. */
export function FindingCard({ data, distanceFromActive, compact, onFix, onSkip }: FindingCardProps) {
  const { finding } = data;
  const sev = SEVERITY[finding.severity];
  const stateKey = displayStatus(finding.status);
  const accent = stateKey === "queued" ? "#35E0C8" : stateKey === "skipped" ? "rgba(255,255,255,0.3)" : sev.color;
  const tint = stateKey === "queued" ? "rgba(53,224,200,0.12)" : stateKey === "skipped" ? "rgba(255,255,255,0.05)" : sev.tint;
  const isActive = distanceFromActive === 0;

  const outerStyle: CSSProperties = {
    position: "absolute",
    inset: 0,
    display: "flex",
    alignItems: "stretch",
    background: "rgba(255,255,255,0.035)",
    border: `1px solid ${stateKey === "queued" ? "rgba(53,224,200,0.35)" : "rgba(255,255,255,0.1)"}`,
    borderRadius: 30,
    overflow: "hidden",
    backdropFilter: "blur(18px)",
    WebkitBackdropFilter: "blur(18px)",
    transform: `translateY(${isActive ? 0 : distanceFromActive < 0 ? -20 : 20}px) scale(${isActive ? 1 : 0.98})`,
    opacity: isActive ? 1 : 0,
    zIndex: isActive ? 3 : 1,
    pointerEvents: isActive ? "auto" : "none",
    transition: "transform 0.3s cubic-bezier(0.22,1,0.36,1), opacity 0.2s ease, border-color 0.18s ease",
  };

  const fixBtnStyle: CSSProperties =
    stateKey === "queued"
      ? { background: "#35E0C8", color: "#04120F", border: "none", height: 48, padding: "0 34px", borderRadius: 16, fontSize: 16, fontWeight: 700, cursor: "pointer", fontFamily: "inherit", transition: "all 0.13s ease" }
      : { background: "rgba(255,255,255,0.08)", color: "#FFFFFF", border: "1px solid rgba(255,255,255,0.22)", height: 48, padding: "0 34px", borderRadius: 16, fontSize: 16, fontWeight: 700, cursor: "pointer", fontFamily: "inherit", transition: "all 0.13s ease" };

  const skipBtnStyle: CSSProperties =
    stateKey === "skipped"
      ? { background: "rgba(255,255,255,0.16)", color: "#FFFFFF", border: "1px solid rgba(255,255,255,0.3)", height: 48, padding: "0 30px", borderRadius: 16, fontSize: 16, fontWeight: 700, cursor: "pointer", fontFamily: "inherit", transition: "all 0.13s ease" }
      : { background: "none", color: "rgba(255,255,255,0.55)", border: "1px solid rgba(255,255,255,0.16)", height: 48, padding: "0 30px", borderRadius: 16, fontSize: 16, fontWeight: 600, cursor: "pointer", fontFamily: "inherit", transition: "all 0.13s ease" };

  return (
    <div style={outerStyle}>
      <div
        style={{
          flex: 1.15,
          minWidth: 0,
          display: "flex",
          flexDirection: "column",
          justifyContent: "center",
          gap: "clamp(10px, 1.6vh, 16px)",
          padding: "clamp(20px, 3vh, 34px) clamp(22px, 2.6vw, 36px)",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
          <span style={{ fontSize: 12, fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase", padding: "7px 15px", borderRadius: 999, whiteSpace: "nowrap", background: tint, color: accent }}>
            {stateKey === "skipped" ? "Skipped" : stateKey === "queued" ? "To fix" : sev.label}
          </span>
          <span style={{ fontSize: 13, color: "rgba(255,255,255,0.4)" }}>{data.positionLabel}</span>
        </div>
        <h2
          style={{
            margin: 0,
            fontSize: "clamp(22px, min(2.4vw, 4vh), 34px)",
            fontWeight: 700,
            letterSpacing: "-0.025em",
            lineHeight: 1.12,
            color: stateKey === "skipped" ? "rgba(255,255,255,0.55)" : "#FFFFFF",
            textWrap: "pretty",
          }}
        >
          {finding.title}
        </h2>
        <p style={{ margin: 0, fontSize: "clamp(15px, min(1.3vw, 2.1vh), 18px)", lineHeight: 1.5, color: "rgba(255,255,255,0.72)", maxWidth: "46ch", textWrap: "pretty" }}>
          {finding.plain}
        </p>
        <div style={{ display: "flex", alignItems: "flex-start", gap: 10, maxWidth: "46ch" }}>
          <CheckThinIcon size={16} style={{ flexShrink: 0, marginTop: 3 }} />
          <span style={{ fontSize: "clamp(13.5px, 1.1vw, 15.5px)", lineHeight: 1.45, color: "rgba(255,255,255,0.55)" }}>{data.fixSummary}</span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap", marginTop: 2 }}>
          <button onClick={onFix} style={fixBtnStyle}>
            Fix
          </button>
          <button onClick={onSkip} style={skipBtnStyle}>
            Skip
          </button>
        </div>
      </div>

      {!compact && (
        <div style={{ flex: 1, minWidth: 0, display: "flex", flexDirection: "column", background: "rgba(0,0,0,0.35)", borderLeft: "1px solid rgba(255,255,255,0.08)" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 9, padding: "13px 18px", borderBottom: "1px solid rgba(255,255,255,0.07)", flexShrink: 0 }}>
            <FileIcon size={14} color="rgba(255,255,255,0.4)" />
            <span style={{ fontFamily: FONT.mono, fontSize: 11.5, color: "rgba(255,255,255,0.45)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
              {data.file}
            </span>
          </div>
          <div className="vc-noscroll" style={{ flex: 1, minHeight: 0, overflow: "hidden", padding: "10px 0", display: "flex", flexDirection: "column", justifyContent: "center" }}>
            {data.beforeLines.map((line) => (
              <ContextLine key={`b${line.num}`} line={line} />
            ))}
            <div
              style={{
                display: "flex",
                alignItems: "flex-start",
                gap: 14,
                padding: "2px 18px",
                fontFamily: FONT.mono,
                fontSize: 12,
                lineHeight: 1.8,
                boxSizing: "border-box",
                background: tint,
                borderLeft: `3px solid ${accent}`,
                transition: "all 0.18s ease",
              }}
            >
              <span style={{ width: 20, textAlign: "right", flexShrink: 0, color: accent, fontSize: 11, fontWeight: 700, userSelect: "none" }}>
                {data.flag.num}
              </span>
              <span style={{ whiteSpace: "pre", color: stateKey === "skipped" ? "rgba(255,255,255,0.45)" : stateKey === "queued" ? "#7FF0E0" : sev.soft, fontWeight: 600, overflow: "hidden" }}>
                {data.flag.text}
              </span>
            </div>
            {data.afterLines.map((line) => (
              <ContextLine key={`a${line.num}`} line={line} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function ContextLine({ line }: { line: CodeSnippetLine }) {
  return (
    <div style={{ display: "flex", alignItems: "flex-start", gap: 14, padding: "1px 18px", fontFamily: FONT.mono, fontSize: 12, lineHeight: 1.8 }}>
      <span style={{ width: 20, textAlign: "right", flexShrink: 0, color: "rgba(255,255,255,0.22)", fontSize: 11, userSelect: "none" }}>{line.num}</span>
      <span style={{ whiteSpace: "pre", color: "rgba(255,255,255,0.35)", overflow: "hidden" }}>{line.text}</span>
    </div>
  );
}
