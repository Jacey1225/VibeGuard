import { useEffect, useState } from "react";
import type { RealFinding, RealFindingSeverity } from "../../hooks/useVibecheckFlow";
import { getApiBaseUrl } from "../../hooks/useVibecheckFlow";
import { normalizeRelativePath } from "../../utils/path";
import { FileIcon, WarningIcon } from "../icons";
import { FONT } from "../../styles/tokens";

interface RealFindingCardProps {
  finding: RealFinding;
  repoId: string | null;
  checked: boolean;
  onToggle: () => void;
}

interface PreviewLine {
  num: number;
  text: string;
}

type PreviewState =
  | { status: "skipped" }
  | { status: "loading" }
  | { status: "ready"; lines: PreviewLine[]; highlightLine: number }
  | { status: "error"; message: string };

const SEVERITY_STYLE: Record<RealFindingSeverity, { bg: string; border: string; accent: string; label: string }> = {
  critical: { bg: "rgba(255,92,92,0.14)", border: "rgba(255,92,92,0.4)", accent: "#FF5C5C", label: "Critical" },
  high: { bg: "rgba(255,107,90,0.13)", border: "rgba(255,107,90,0.4)", accent: "#FF6B5A", label: "High" },
  medium: { bg: "rgba(245,181,68,0.12)", border: "rgba(245,181,68,0.38)", accent: "#F5B544", label: "Medium" },
  low: { bg: "rgba(127,216,196,0.1)", border: "rgba(127,216,196,0.32)", accent: "#7FD8C4", label: "Low" },
  info: { bg: "rgba(255,255,255,0.05)", border: "rgba(255,255,255,0.14)", accent: "rgba(255,255,255,0.5)", label: "Info" },
};

/**
 * Fetches a windowed preview of the real file a finding points at, centered
 * on its line number, from the backend's already-cloned scan copy
 * (`GET /repositories/{id}/files/preview`) -- never a live, unauthenticated
 * call to api.github.com. This is served straight from what was actually
 * scanned, so it can't drift, can't hit GitHub's per-IP rate limit, and
 * works for private/inaccessible repos the browser has no credential for.
 * Findings with no line number (e.g. the dependency-manifest heuristic)
 * never had a specific line to locate, so no fetch is made at all -- the
 * card falls back to a file-only reference with no code shown, per the
 * same rule as a preview that fails to resolve.
 */
function usePreview(finding: RealFinding, repoId: string | null): PreviewState {
  const [state, setState] = useState<PreviewState>(finding.line_number ? { status: "loading" } : { status: "skipped" });

  useEffect(() => {
    if (!finding.line_number || finding.line_number < 1) {
      setState({ status: "skipped" });
      return;
    }
    if (!repoId) {
      setState({ status: "error", message: "No repository connected" });
      return;
    }

    let cancelled = false;
    setState({ status: "loading" });

    const path = normalizeRelativePath(finding.relative_path);
    const lineNumber = finding.line_number;

    let url: string;
    try {
      url = `${getApiBaseUrl()}/repositories/${repoId}/files/preview?path=${encodeURIComponent(path)}&line=${lineNumber}`;
    } catch (err) {
      setState({ status: "error", message: err instanceof Error ? err.message : "Preview unavailable" });
      return;
    }

    fetch(url)
      .then(async (res) => {
        if (!res.ok) {
          // 404 (repo/file not found) and 422 (binary/oversized file, or
          // line outside the file's current stored length) both carry a
          // specific `detail` message from the backend -- surface that
          // directly instead of a generic status-code string.
          const body = await res.json().catch(() => null);
          const detail = body && typeof body.detail === "string" ? body.detail : null;
          throw new Error(detail ?? `Preview request failed (${res.status})`);
        }
        const data = await res.json();
        const lines: PreviewLine[] = (data.lines ?? []).map((line: { number: number; text: string }) => ({
          num: line.number,
          text: line.text === "" ? " " : line.text,
        }));
        if (!cancelled) setState({ status: "ready", lines, highlightLine: data.highlight_line });
      })
      .catch((err) => {
        // A thrown TypeError here (the browser's literal "failed to fetch"
        // message) means a network-level failure reaching our own backend
        // -- distinct from, and much rarer than, the old direct-to-GitHub
        // rate-limit/CORS failures this replaces.
        if (!cancelled) setState({ status: "error", message: err instanceof Error ? err.message : "Preview unavailable" });
      });

    return () => {
      cancelled = true;
    };
  }, [finding.relative_path, finding.line_number, repoId]);

  return state;
}

/** One real finding: severity-colored card with a selection checkbox, description, location, and (when a line is located) a live highlighted code preview. */
export function RealFindingCard({ finding, repoId, checked, onToggle }: RealFindingCardProps) {
  const preview = usePreview(finding, repoId);
  const style = SEVERITY_STYLE[finding.severity] ?? SEVERITY_STYLE.info;
  const path = normalizeRelativePath(finding.relative_path);
  const location = finding.line_number ? `${path}:${finding.line_number}` : path;
  const showsNoCode = preview.status === "skipped" || preview.status === "error";

  return (
    <div
      style={{
        borderRadius: 22,
        padding: "20px 22px",
        background: style.bg,
        border: `1px solid ${checked ? style.border : "rgba(255,255,255,0.08)"}`,
        display: "flex",
        flexDirection: "column",
        gap: 14,
        opacity: checked ? 1 : 0.55,
        transition: "opacity 0.15s ease, border-color 0.15s ease",
      }}
    >
      <div style={{ display: "flex", alignItems: "flex-start", justifyContent: "space-between", gap: 14, flexWrap: "wrap" }}>
        <div style={{ display: "flex", alignItems: "flex-start", gap: 12, minWidth: 0 }}>
          <input
            type="checkbox"
            checked={checked}
            onChange={onToggle}
            style={{
              flexShrink: 0,
              width: 20,
              height: 20,
              marginTop: 2,
              accentColor: style.accent,
              cursor: "pointer",
            }}
          />
          <div style={{ display: "flex", flexDirection: "column", gap: 6, minWidth: 0 }}>
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
          </div>
        </div>
      </div>

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
          Location: {location}
        </span>
      </div>

      <p style={{ margin: 0, fontSize: 14, lineHeight: 1.55, color: "rgba(255,255,255,0.82)" }}>{finding.description}</p>

      {preview.status === "loading" && (
        <div
          style={{
            borderRadius: 14,
            padding: "16px 18px",
            fontSize: 13,
            color: "rgba(255,255,255,0.4)",
            background: "rgba(0,0,0,0.28)",
            border: "1px solid rgba(255,255,255,0.08)",
          }}
        >
          Loading code preview…
        </div>
      )}

      {showsNoCode && (
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
          {preview.status === "error" ? (
            <>
              <WarningIcon size={14} style={{ flexShrink: 0 }} />
              {preview.message} — see the full file: {path}
            </>
          ) : (
            <>
              <FileIcon size={14} style={{ flexShrink: 0 }} />
              No specific line reported — applies to the whole file: {path}
            </>
          )}
        </div>
      )}

      {preview.status === "ready" && (
        <div
          style={{
            borderRadius: 14,
            overflow: "hidden",
            background: "rgba(0,0,0,0.28)",
            border: "1px solid rgba(255,255,255,0.08)",
          }}
        >
          <div style={{ padding: "10px 0", overflowX: "auto" }}>
            {preview.lines.map((line) => {
              const isHighlighted = preview.highlightLine === line.num;
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
    </div>
  );
}
