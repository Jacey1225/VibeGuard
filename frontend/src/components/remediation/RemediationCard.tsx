import type { RealRemediation } from "../../hooks/useVibecheckFlow";
import { normalizeRelativePath } from "../../utils/path";
import { FileIcon, WarningIcon, CheckCircleFilledIcon, SpinnerIcon } from "../icons";
import { FONT } from "../../styles/tokens";

interface RemediationCardProps {
  remediation: RealRemediation;
  deciding: boolean;
  onApprove: () => void;
  onReject: () => void;
}

const STATUS_LABEL: Record<RealRemediation["status"], string> = {
  proposed: "Awaiting review",
  pushed: "Pushed",
  rejected: "Rejected",
  push_failed: "Push failed — retryable",
};

/** One proposed fix for a file, with its diff and an approve/reject decision -- the real-data counterpart to DiffCard. */
export function RemediationCard({ remediation, deciding, onApprove, onReject }: RemediationCardProps) {
  const decidable = remediation.status === "proposed" || remediation.status === "push_failed";
  const path = normalizeRelativePath(remediation.relative_path);

  return (
    <div
      style={{
        borderRadius: 22,
        padding: "20px 22px",
        background: "rgba(255,255,255,0.035)",
        border: "1px solid rgba(255,255,255,0.1)",
        display: "flex",
        flexDirection: "column",
        gap: 14,
      }}
    >
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 14, flexWrap: "wrap" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8, minWidth: 0 }}>
          <FileIcon size={14} style={{ flexShrink: 0 }} />
          <span style={{ fontSize: 13, fontFamily: FONT.mono, color: "rgba(255,255,255,0.75)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
            {path}
          </span>
        </div>
        <span
          style={{
            fontSize: 11.5,
            fontWeight: 700,
            letterSpacing: "0.06em",
            textTransform: "uppercase",
            color: remediation.status === "pushed" ? "#35E0C8" : remediation.status === "rejected" ? "rgba(255,255,255,0.4)" : remediation.status === "push_failed" ? "#FF8B7C" : "rgba(255,255,255,0.6)",
            background: "rgba(0,0,0,0.2)",
            border: "1px solid rgba(255,255,255,0.14)",
            borderRadius: 999,
            padding: "3px 10px",
            whiteSpace: "nowrap",
          }}
        >
          {STATUS_LABEL[remediation.status]}
        </span>
      </div>

      <p style={{ margin: 0, fontSize: 14, lineHeight: 1.55, color: "rgba(255,255,255,0.82)" }}>{remediation.summary}</p>

      {remediation.introduces_new_heuristic_hits && (
        <div style={{ display: "flex", alignItems: "center", gap: 8, borderRadius: 14, padding: "10px 14px", fontSize: 13, color: "#FFD9D3", background: "rgba(255,107,90,0.12)", border: "1px solid rgba(255,107,90,0.4)" }}>
          <WarningIcon size={14} style={{ flexShrink: 0 }} />
          This fix newly matches {remediation.new_heuristic_hit_summary ?? "another VibeGuard check"} — review closely before approving.
        </div>
      )}

      {remediation.status === "push_failed" && (
        <div style={{ fontSize: 12.5, color: "rgba(255,255,255,0.45)" }}>
          Push failed ({remediation.push_failure_reason ?? "unknown reason"}) — approve again to retry.
        </div>
      )}

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
          whiteSpace: "pre",
        }}
      >
        {remediation.diff_text}
      </pre>

      {decidable && (
        <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
          <button
            onClick={onApprove}
            disabled={deciding}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
              background: deciding ? "rgba(53,224,200,0.4)" : "#35E0C8",
              color: "#04120F",
              border: "none",
              height: 42,
              padding: "0 20px",
              borderRadius: 14,
              fontSize: 14,
              fontWeight: 700,
              cursor: deciding ? "not-allowed" : "pointer",
              fontFamily: "inherit",
            }}
          >
            {deciding && <SpinnerIcon size={14} color="#04120F" style={{ animation: "vc-spin 0.8s linear infinite" }} />}
            {remediation.status === "push_failed" ? "Retry push" : "Approve & push"}
          </button>
          <button
            onClick={onReject}
            disabled={deciding}
            style={{
              background: "rgba(255,255,255,0.07)",
              color: "rgba(255,255,255,0.85)",
              border: "1px solid rgba(255,255,255,0.16)",
              height: 42,
              padding: "0 20px",
              borderRadius: 14,
              fontSize: 14,
              fontWeight: 700,
              cursor: deciding ? "not-allowed" : "pointer",
              fontFamily: "inherit",
            }}
          >
            Reject
          </button>
        </div>
      )}

      {remediation.status === "pushed" && remediation.pushed_commit_sha && (
        <div style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 12.5, color: "rgba(255,255,255,0.45)" }}>
          <CheckCircleFilledIcon size={14} />
          Pushed as {remediation.pushed_commit_sha.slice(0, 7)}
          {remediation.push_target_branch ? ` on ${remediation.push_target_branch}` : ""}
        </div>
      )}
    </div>
  );
}
