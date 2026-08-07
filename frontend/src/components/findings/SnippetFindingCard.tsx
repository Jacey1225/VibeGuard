import { useMemo } from "react";
import type { RealFindingSeverity, SnippetFinding } from "../../hooks/useVibecheckFlow";
import { FileIcon } from "../icons";
import { FONT } from "../../styles/tokens";
import { SnippetFixControl } from "./SnippetFixControl";

interface SnippetFindingCardProps {
  finding: SnippetFinding;
  /** The full text of the scanned snippet, captured at submission time -- sliced client-side around `finding.line_number` instead of a `/repositories/{id}/files/preview` fetch, since a snippet has no server-side file to preview. */
  snippetContent: string;
  snippetId: string;
}

interface ContextLine {
  num: number;
  text: string;
}

const SEVERITY_STYLE: Record<RealFindingSeverity, { bg: string; border: string; accent: string; label: string }> = {
  critical: { bg: "rgba(255,92,92,0.14)", border: "rgba(255,92,92,0.4)", accent: "#FF5C5C", label: "Critical" },
  high: { bg: "rgba(255,107,90,0.13)", border: "rgba(255,107,90,0.4)", accent: "#FF6B5A", label: "High" },
  medium: { bg: "rgba(245,181,68,0.12)", border: "rgba(245,181,68,0.38)", accent: "#F5B544", label: "Medium" },
  low: { bg: "rgba(127,216,196,0.1)", border: "rgba(127,216,196,0.32)", accent: "#7FD8C4", label: "Low" },
  info: { bg: "rgba(255,255,255,0.05)", border: "rgba(255,255,255,0.14)", accent: "rgba(255,255,255,0.5)", label: "Info" },
};

/** How many lines of context to show above and below the flagged line. */
const CONTEXT_LINES = 3;

/**
 * Slices `contextLines` rows of a snippet's own text above/below the
 * flagged line, synchronously and client-side -- there's no server round
 * trip and so no loading/network-error state, unlike `RealFindingCard`'s
 * `usePreview`. Returns `null` when there's no line to center on, or the
 * reported line falls outside the snippet's current text.
 */
function sliceSnippetContext(content: string, lineNumber: number | null): ContextLine[] | null {
  if (!lineNumber || lineNumber < 1) return null;
  const lines = content.split(/\r\n|\r|\n/);
  if (lineNumber > lines.length) return null;

  const start = Math.max(1, lineNumber - CONTEXT_LINES);
  const end = Math.min(lines.length, lineNumber + CONTEXT_LINES);
  const sliced: ContextLine[] = [];
  for (let num = start; num <= end; num += 1) {
    const text = lines[num - 1];
    sliced.push({ num, text: text === "" ? " " : text });
  }
  return sliced;
}

/**
 * One finding within a plain-text snippet scan: severity-colored card,
 * client-sliced code context (no live preview fetch), and a per-finding
 * fix-submission control. The snippet-scoped counterpart to
 * `RealFindingCard` -- not selectable (there's no batch remediation step
 * to feed) and sources code from the snippet's own text instead of
 * `GET /repositories/{id}/files/preview`.
 */
export function SnippetFindingCard({ finding, snippetContent, snippetId }: SnippetFindingCardProps) {
  const style = SEVERITY_STYLE[finding.severity] ?? SEVERITY_STYLE.info;
  const contextLines = useMemo(
    () => sliceSnippetContext(snippetContent, finding.line_number),
    [snippetContent, finding.line_number],
  );

  return (
    <div
      style={{
        borderRadius: 22,
        padding: "20px 22px",
        background: style.bg,
        border: "1px solid rgba(255,255,255,0.08)",
        display: "flex",
        flexDirection: "column",
        gap: 14,
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
        <span
          style={{
            fontSize: 11,
            fontWeight: 700,
            letterSpacing: "0.08em",
            textTransform: "uppercase",
            color: style.accent,
            background: "rgba(0,0,0,0.2)",
            border: `1px solid ${style.border}`,
            borderRadius: 999,
            padding: "3px 10px",
          }}
        >
          {style.label}
        </span>
        <span style={{ fontSize: 11.5, color: "rgba(255,255,255,0.4)", textTransform: "uppercase", letterSpacing: "0.06em" }}>
          {finding.category.replace(/_/g, " ")}
        </span>
      </div>

      <h3 style={{ margin: 0, fontSize: 16.5, fontWeight: 700, color: "#FFFFFF", lineHeight: 1.3 }}>{finding.title}</h3>

      <div style={{ display: "flex", alignItems: "center", gap: 8, minWidth: 0 }}>
        <FileIcon size={14} style={{ flexShrink: 0 }} />
        <span
          style={{
            fontSize: 12.5,
            fontFamily: FONT.mono,
            color: "rgba(255,255,255,0.6)",
            overflow: "hidden",
            textOverflow: "ellipsis",
            whiteSpace: "nowrap",
          }}
        >
          {finding.line_number ? `Line ${finding.line_number}` : "Applies to the whole snippet"}
        </span>
      </div>

      <p style={{ margin: 0, fontSize: 14, lineHeight: 1.55, color: "rgba(255,255,255,0.82)" }}>{finding.description}</p>

      {contextLines === null ? (
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 8,
            borderRadius: 14,
            padding: "14px 18px",
            fontSize: 13,
            color: "rgba(255,255,255,0.45)",
            background: "rgba(0,0,0,0.2)",
            border: "1px solid rgba(255,255,255,0.08)",
          }}
        >
          <FileIcon size={14} style={{ flexShrink: 0 }} />
          No specific line reported — applies to the whole snippet.
        </div>
      ) : (
        <div
          style={{
            borderRadius: 14,
            overflow: "hidden",
            background: "rgba(0,0,0,0.28)",
            border: "1px solid rgba(255,255,255,0.08)",
          }}
        >
          <div style={{ padding: "10px 0", overflowX: "auto" }}>
            {contextLines.map((line) => {
              const isHighlighted = line.num === finding.line_number;
              return (
                <div
                  key={line.num}
                  style={{
                    display: "flex",
                    background: isHighlighted ? "rgba(255,92,92,0.14)" : "transparent",
                    borderLeft: isHighlighted ? `3px solid ${style.accent}` : "3px solid transparent",
                  }}
                >
                  <span
                    style={{
                      flexShrink: 0,
                      width: 44,
                      textAlign: "right",
                      paddingRight: 12,
                      fontFamily: FONT.mono,
                      fontSize: 12,
                      color: isHighlighted ? "rgba(255,255,255,0.6)" : "rgba(255,255,255,0.28)",
                      userSelect: "none",
                    }}
                  >
                    {line.num}
                  </span>
                  <span
                    style={{
                      fontFamily: FONT.mono,
                      fontSize: 12.5,
                      lineHeight: 1.7,
                      color: isHighlighted ? "#FFFFFF" : "rgba(255,255,255,0.65)",
                      whiteSpace: "pre",
                      paddingRight: 16,
                    }}
                  >
                    {line.text}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      <SnippetFixControl snippetId={snippetId} findingId={finding.id} />
    </div>
  );
}
