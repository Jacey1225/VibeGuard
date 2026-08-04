import type { CSSProperties } from "react";
import type { CodeSnippetLine } from "../../types";
import { FONT } from "../../styles/tokens";
import { CheckCircleFilledIcon } from "../icons";

export interface FixBlockData {
  title: string;
  num: number;
  origText: string;
  fixedText: string;
  beforeLines: CodeSnippetLine[];
  afterLines: CodeSnippetLine[];
  done: boolean;
  running: boolean;
  caption: string;
}

interface FixCardProps {
  data: FixBlockData;
  distanceFromFocus: number;
}

/** One in-progress (or completed) fix in the fixing-screen stack. */
export function FixCard({ data, distanceFromFocus }: FixCardProps) {
  const isFocus = distanceFromFocus === 0;
  const { done, running } = data;

  const cardStyle: CSSProperties = {
    position: "absolute",
    inset: 0,
    display: "flex",
    flexDirection: "column",
    background: "rgba(255,255,255,0.035)",
    border: `1px solid ${running ? "rgba(53,224,200,0.45)" : "rgba(255,255,255,0.1)"}`,
    borderRadius: 30,
    overflow: "hidden",
    backdropFilter: "blur(18px)",
    WebkitBackdropFilter: "blur(18px)",
    transform: `translateY(${isFocus ? 0 : distanceFromFocus < 0 ? -22 : 22}px) scale(${isFocus ? 1 : 0.97})`,
    opacity: isFocus ? 1 : 0,
    zIndex: isFocus ? 3 : 1,
    pointerEvents: isFocus ? "auto" : "none",
    transition: "transform 0.32s cubic-bezier(0.22,1,0.36,1), opacity 0.22s ease, border-color 0.18s ease",
  };

  return (
    <div style={cardStyle}>
      <div style={{ flexShrink: 0, display: "flex", alignItems: "center", gap: 12, padding: "18px 24px 14px" }}>
        <span
          style={{
            flexShrink: 0,
            fontSize: 11.5,
            fontWeight: 700,
            letterSpacing: "0.06em",
            textTransform: "uppercase",
            padding: "6px 14px",
            borderRadius: 999,
            whiteSpace: "nowrap",
            background: running || done ? "rgba(53,224,200,0.13)" : "rgba(255,255,255,0.06)",
            color: running || done ? "#35E0C8" : "rgba(255,255,255,0.4)",
            transition: "all 0.18s ease",
          }}
        >
          {running ? "Fixing" : done ? "Fixed" : "Waiting"}
        </span>
        <span style={{ fontSize: "clamp(15px, 1.4vw, 18px)", fontWeight: 700, letterSpacing: "-0.01em", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
          {data.title}
        </span>
      </div>
      <div className="vc-noscroll" style={{ flex: 1, minHeight: 0, overflow: "hidden", padding: "6px 0", display: "flex", flexDirection: "column", justifyContent: "center" }}>
        {data.beforeLines.map((line) => (
          <FixContextLine key={`b${line.num}`} line={line} />
        ))}
        {!done && (
          <div
            style={{
              display: "flex",
              alignItems: "flex-start",
              gap: 16,
              padding: "2px 24px",
              fontFamily: FONT.mono,
              fontSize: 12.5,
              lineHeight: 1.85,
              boxSizing: "border-box",
              background: running ? "rgba(255,107,90,0.12)" : "rgba(255,255,255,0.04)",
              borderLeft: `3px solid ${running ? "#FF6B5A" : "rgba(255,255,255,0.15)"}`,
              color: running ? "#FF8B7C" : "rgba(255,255,255,0.4)",
              animation: running ? "vc-working 1s ease-in-out infinite" : undefined,
              transition: "all 0.18s ease",
            }}
          >
            <span style={{ width: 22, textAlign: "right", flexShrink: 0, fontSize: 11.5, fontWeight: 700, userSelect: "none", color: "currentColor" }}>{data.num}</span>
            <span style={{ whiteSpace: "pre", overflowWrap: "anywhere" }}>{data.origText}</span>
          </div>
        )}
        {done && (
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: 16,
              padding: "2px 24px",
              fontFamily: FONT.mono,
              fontSize: 12.5,
              lineHeight: 1.85,
              boxSizing: "border-box",
              background: "rgba(53,224,200,0.1)",
              borderLeft: "3px solid #35E0C8",
              animation: "vc-line-swap 0.28s cubic-bezier(0.22,1,0.36,1)",
            }}
          >
            <span style={{ width: 22, textAlign: "right", flexShrink: 0, color: "#35E0C8", fontSize: 11.5, fontWeight: 700, userSelect: "none" }}>{data.num}</span>
            <span style={{ whiteSpace: "pre", color: "#7FF0E0", fontWeight: 600, overflowWrap: "anywhere" }}>{data.fixedText}</span>
            <CheckCircleFilledIcon size={16} style={{ marginLeft: "auto", flexShrink: 0 }} />
          </div>
        )}
        {data.afterLines.map((line) => (
          <FixContextLine key={`a${line.num}`} line={line} />
        ))}
      </div>
      <div
        style={{
          flexShrink: 0,
          display: "flex",
          alignItems: "center",
          gap: 10,
          padding: "14px 24px 18px",
          borderTop: "1px solid rgba(255,255,255,0.07)",
          background: done ? "rgba(53,224,200,0.06)" : "transparent",
          transition: "background 0.22s ease",
        }}
      >
        <span style={{ fontSize: "clamp(14px, 1.2vw, 16px)", color: "rgba(255,255,255,0.75)", lineHeight: 1.45 }}>{data.caption}</span>
      </div>
    </div>
  );
}

function FixContextLine({ line }: { line: CodeSnippetLine }) {
  return (
    <div style={{ display: "flex", alignItems: "flex-start", gap: 16, padding: "1px 24px", fontFamily: FONT.mono, fontSize: 12.5, lineHeight: 1.85 }}>
      <span style={{ width: 22, textAlign: "right", flexShrink: 0, color: "rgba(255,255,255,0.22)", fontSize: 11.5, userSelect: "none" }}>{line.num}</span>
      <span style={{ whiteSpace: "pre", color: "rgba(255,255,255,0.35)" }}>{line.text}</span>
    </div>
  );
}
