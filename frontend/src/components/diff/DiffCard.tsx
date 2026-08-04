import type { CSSProperties } from "react";
import type { CodeSnippetLine } from "../../types";
import { FONT } from "../../styles/tokens";
import { FileIcon, CheckThinIcon } from "../icons";

export interface DiffBlockData {
  title: string;
  file: string;
  fixSummary: string;
  positionLabel: string;
  beforeLines: CodeSnippetLine[];
  afterLines: CodeSnippetLine[];
  minusText: string;
  plusText: string;
}

interface DiffCardProps {
  data: DiffBlockData;
  distanceFromActive: number;
  compact: boolean;
}

/** One before/after diff in the "what changed" review stack. */
export function DiffCard({ data, distanceFromActive, compact }: DiffCardProps) {
  const isActive = distanceFromActive === 0;
  const cardStyle: CSSProperties = {
    position: "absolute",
    inset: 0,
    display: "flex",
    alignItems: "stretch",
    background: "rgba(255,255,255,0.035)",
    border: "1px solid rgba(255,255,255,0.1)",
    borderRadius: 30,
    overflow: "hidden",
    backdropFilter: "blur(18px)",
    WebkitBackdropFilter: "blur(18px)",
    transform: `translateY(${isActive ? 0 : distanceFromActive < 0 ? -20 : 20}px) scale(${isActive ? 1 : 0.98})`,
    opacity: isActive ? 1 : 0,
    zIndex: isActive ? 3 : 1,
    pointerEvents: isActive ? "auto" : "none",
    transition: "transform 0.3s cubic-bezier(0.22,1,0.36,1), opacity 0.2s ease",
  };

  return (
    <div style={cardStyle}>
      <div style={{ flex: 1, minWidth: 0, display: "flex", flexDirection: "column", justifyContent: "center", gap: "clamp(10px, 1.6vh, 16px)", padding: "clamp(20px, 3vh, 34px) clamp(22px, 2.6vw, 36px)" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8, background: "rgba(53,224,200,0.12)", color: "#35E0C8", fontSize: 12, fontWeight: 700, padding: "6px 14px", borderRadius: 999, alignSelf: "flex-start" }}>
          <CheckThinIcon size={13} />
          Fixed · still works
        </div>
        <h2 style={{ margin: 0, fontSize: "clamp(21px, min(2.3vw, 3.8vh), 32px)", fontWeight: 700, letterSpacing: "-0.025em", lineHeight: 1.12, textWrap: "pretty" }}>
          {data.title}
        </h2>
        <p style={{ margin: 0, fontSize: "clamp(15px, min(1.3vw, 2.1vh), 18px)", lineHeight: 1.5, color: "rgba(255,255,255,0.72)", maxWidth: "46ch", textWrap: "pretty" }}>
          {data.fixSummary}
        </p>
        <span style={{ fontSize: 13, color: "rgba(255,255,255,0.4)" }}>{data.positionLabel}</span>
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
              <DiffContextLine key={`b${line.num}`} line={line} />
            ))}
            <div style={{ display: "flex", alignItems: "flex-start", gap: 14, padding: "2px 18px", fontFamily: FONT.mono, fontSize: 12, lineHeight: 1.8, background: "rgba(255,107,90,0.1)", borderLeft: "3px solid #FF6B5A" }}>
              <span style={{ width: 20, textAlign: "right", flexShrink: 0, color: "#FF8B7C", fontSize: 11, userSelect: "none" }}>−</span>
              <span style={{ whiteSpace: "pre", color: "#FF8B7C" }}>{data.minusText}</span>
            </div>
            <div style={{ display: "flex", alignItems: "flex-start", gap: 14, padding: "2px 18px", fontFamily: FONT.mono, fontSize: 12, lineHeight: 1.8, background: "rgba(53,224,200,0.1)", borderLeft: "3px solid #35E0C8" }}>
              <span style={{ width: 20, textAlign: "right", flexShrink: 0, color: "#35E0C8", fontSize: 11, userSelect: "none" }}>+</span>
              <span style={{ whiteSpace: "pre", color: "#7FF0E0" }}>{data.plusText}</span>
            </div>
            {data.afterLines.map((line) => (
              <DiffContextLine key={`a${line.num}`} line={line} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function DiffContextLine({ line }: { line: CodeSnippetLine }) {
  return (
    <div style={{ display: "flex", alignItems: "flex-start", gap: 14, padding: "1px 18px", fontFamily: FONT.mono, fontSize: 12, lineHeight: 1.8 }}>
      <span style={{ width: 20, textAlign: "right", flexShrink: 0, color: "rgba(255,255,255,0.22)", fontSize: 11, userSelect: "none" }}>{line.num}</span>
      <span style={{ whiteSpace: "pre", color: "rgba(255,255,255,0.35)" }}>{line.text}</span>
    </div>
  );
}
