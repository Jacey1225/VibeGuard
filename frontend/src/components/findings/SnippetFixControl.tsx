import { useEffect, useState } from "react";
import type { SnippetFixSubmission } from "../../hooks/useVibecheckFlow";
import { getApiBaseUrl } from "../../hooks/useVibecheckFlow";
import { CheckCircleFilledIcon, SpinnerIcon, WarningIcon } from "../icons";
import { FONT } from "../../styles/tokens";

interface SnippetFixControlProps {
  snippetId: string;
  findingId: number;
}

type ControlState =
  | { phase: "loading" }
  | { phase: "idle" }
  // `existing` carries the prior submission through an edit-in-progress so
  // Cancel can restore the read-only "submitted" view instead of dropping
  // back to "idle" (which would misleadingly imply nothing was ever
  // submitted, even though the prior fix is still stored server-side).
  | { phase: "editing"; draft: string; error: string | null; existing: SnippetFixSubmission | null }
  | { phase: "saving"; draft: string; existing: SnippetFixSubmission | null }
  | { phase: "submitted"; submission: SnippetFixSubmission };

const textAreaStyle = {
  width: "100%",
  boxSizing: "border-box" as const,
  resize: "vertical" as const,
  minHeight: 120,
  padding: "12px 14px",
  borderRadius: 12,
  background: "rgba(0,0,0,0.28)",
  border: "1px solid rgba(255,255,255,0.08)",
  color: "#FFFFFF",
  fontFamily: FONT.mono,
  fontSize: 12.5,
  lineHeight: 1.6,
  outline: "none",
};

const primaryButtonStyle = (disabled: boolean) => ({
  display: "flex",
  alignItems: "center",
  gap: 8,
  background: disabled ? "rgba(53,224,200,0.4)" : "#35E0C8",
  color: "#04120F",
  border: "none",
  height: 42,
  padding: "0 20px",
  borderRadius: 14,
  fontSize: 13.5,
  fontWeight: 700,
  cursor: disabled ? "not-allowed" : "pointer",
  fontFamily: "inherit",
});

const ghostButtonStyle = {
  background: "rgba(255,255,255,0.07)",
  color: "rgba(255,255,255,0.85)",
  border: "1px solid rgba(255,255,255,0.16)",
  height: 42,
  padding: "0 18px",
  borderRadius: 14,
  fontSize: 13.5,
  fontWeight: 700,
  cursor: "pointer",
  fontFamily: "inherit",
};

/**
 * The per-finding fix-submission control on `SnippetFindingCard`: paste your
 * own already-fixed code and record it via `POST
 * /snippets/{id}/findings/{id}/fix`. Not an LLM suggestion and nothing gets
 * pushed anywhere -- this just records what the caller typed. Manages its
 * own idle/editing/saving/submitted state and does its own read-on-mount
 * (`GET` the same route) rather than living in shared flow state, since a
 * fix submission is scoped to exactly one finding and nothing else on
 * screen needs to react to it.
 */
export function SnippetFixControl({ snippetId, findingId }: SnippetFixControlProps) {
  const [state, setState] = useState<ControlState>({ phase: "loading" });

  useEffect(() => {
    let cancelled = false;
    setState({ phase: "loading" });

    let url: string;
    try {
      url = `${getApiBaseUrl()}/snippets/${snippetId}/findings/${findingId}/fix`;
    } catch {
      if (!cancelled) setState({ phase: "idle" });
      return;
    }

    fetch(url)
      .then(async (res) => {
        if (cancelled) return;
        if (res.status === 404) {
          setState({ phase: "idle" });
          return;
        }
        if (!res.ok) {
          // Best-effort check -- an unexpected failure here just means the
          // control starts from "no submission yet" instead of blocking
          // the whole card on an error banner.
          setState({ phase: "idle" });
          return;
        }
        const submission: SnippetFixSubmission = await res.json();
        setState({ phase: "submitted", submission });
      })
      .catch(() => {
        if (!cancelled) setState({ phase: "idle" });
      });

    return () => {
      cancelled = true;
    };
  }, [snippetId, findingId]);

  const openEditor = (prefill: string, existing: SnippetFixSubmission | null) =>
    setState({ phase: "editing", draft: prefill, error: null, existing });

  const cancelEditing = () => {
    if (state.phase !== "editing") return;
    setState(state.existing ? { phase: "submitted", submission: state.existing } : { phase: "idle" });
  };

  const submit = async () => {
    if (state.phase !== "editing") return;
    const draft = state.draft;
    const existing = state.existing;
    if (!draft.trim()) return;
    setState({ phase: "saving", draft, existing });

    try {
      const response = await fetch(`${getApiBaseUrl()}/snippets/${snippetId}/findings/${findingId}/fix`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ fixed_content: draft }),
      });

      if (!response.ok) {
        const body = await response.json().catch(() => null);
        const detail = body && typeof body.detail === "string" ? body.detail : null;
        setState({ phase: "editing", draft, error: detail ?? `Failed to submit fix (${response.status})`, existing });
        return;
      }

      const submission: SnippetFixSubmission = await response.json();
      setState({ phase: "submitted", submission });
    } catch (err) {
      setState({ phase: "editing", draft, error: err instanceof Error ? err.message : "Failed to reach the server", existing });
    }
  };

  if (state.phase === "loading") {
    // No visible loading affordance -- this check is fast and best-effort;
    // showing a spinner here would just flicker before "Submit your fix".
    return null;
  }

  if (state.phase === "idle") {
    return (
      <button
        onClick={() => openEditor("", null)}
        style={{
          alignSelf: "flex-start",
          background: "none",
          border: "none",
          color: "#7FD8C4",
          fontSize: 13.5,
          fontWeight: 700,
          cursor: "pointer",
          fontFamily: "inherit",
          padding: "6px 0",
        }}
      >
        Submit your fix
      </button>
    );
  }

  if (state.phase === "submitted") {
    return (
      <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 10 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 12.5, color: "rgba(255,255,255,0.6)" }}>
            <CheckCircleFilledIcon size={16} />
            Fix submitted
          </div>
          <button
            onClick={() => openEditor(state.submission.fixed_content, state.submission)}
            style={{
              background: "none",
              border: "none",
              color: "#7FD8C4",
              fontSize: 12.5,
              fontWeight: 700,
              cursor: "pointer",
              fontFamily: "inherit",
              padding: "4px 0",
            }}
          >
            Edit
          </button>
        </div>
        <pre
          className="vc-noscroll"
          style={{
            margin: 0,
            maxHeight: 220,
            overflow: "auto",
            borderRadius: 14,
            padding: "14px 16px",
            background: "rgba(0,0,0,0.35)",
            border: "1px solid rgba(255,255,255,0.08)",
            fontFamily: FONT.mono,
            fontSize: 12,
            lineHeight: 1.7,
            color: "rgba(255,255,255,0.75)",
            whiteSpace: "pre-wrap",
          }}
        >
          {state.submission.fixed_content}
        </pre>
      </div>
    );
  }

  // "editing" or "saving"
  const saving = state.phase === "saving";
  const draft = state.draft;
  const error = state.phase === "editing" ? state.error : null;
  const existing = state.existing;
  const fieldId = `vc-snippet-fix-${findingId}`;

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
      <label htmlFor={fieldId} style={{ fontSize: 12, fontWeight: 600, color: "rgba(255,255,255,0.55)" }}>
        Your fixed code
      </label>
      <textarea
        id={fieldId}
        value={draft}
        onChange={(e) => setState({ phase: "editing", draft: e.target.value, error: null, existing })}
        placeholder="Paste your corrected code here"
        spellCheck={false}
        disabled={saving}
        style={textAreaStyle}
      />
      {error && (
        <div role="alert" style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 12.5, color: "#FFD9D3" }}>
          <WarningIcon size={14} style={{ flexShrink: 0 }} />
          {error}
        </div>
      )}
      <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
        <button onClick={submit} disabled={saving || !draft.trim()} style={primaryButtonStyle(saving || !draft.trim())}>
          {saving && <SpinnerIcon size={14} color="#04120F" style={{ animation: "vc-spin 0.8s linear infinite" }} />}
          {saving ? "Submitting…" : "Submit fix"}
        </button>
        <button onClick={cancelEditing} disabled={saving} style={{ ...ghostButtonStyle, cursor: saving ? "not-allowed" : "pointer" }}>
          Cancel
        </button>
      </div>
    </div>
  );
}
