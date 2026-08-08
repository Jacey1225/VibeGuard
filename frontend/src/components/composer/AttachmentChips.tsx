import type { RepositoryFileSummary } from "../../hooks/useVibecheckFlow";
import { FileIcon } from "../icons";

interface AttachmentChipsProps {
  summary: RepositoryFileSummary | null;
}

/**
 * Composer's "repo connected" indicator. Renders a single truthful chip
 * built from data the backend already verified when it cloned and walked
 * the repository (`POST /repositories`'s `total_files_stored` /
 * `files_truncated` -- see `RepositoryResponse` in
 * `src/vibeguard/api/schemas.py`), never a per-file listing.
 *
 * A prior version rendered up to five chips from a separate, redundant,
 * unauthenticated call straight to GitHub's non-recursive `contents` API
 * (root directory only -- every subdirectory file was silently dropped),
 * and fell back to three hardcoded fixture filenames unrelated to the
 * submitted repo whenever that call returned nothing (the common case).
 * Both defects are gone, not patched: there's no client-side per-file
 * guess left to get wrong, and no fallback data left to show by mistake.
 * See intake spec 20260807-repo-file-preview-truncated.
 */
export function AttachmentChips({ summary }: AttachmentChipsProps) {
  if (!summary) return null;

  const label = summary.totalFiles === 1 ? "1 file" : `${summary.totalFiles} files`;

  return (
    <div style={{ display: "flex", alignItems: "stretch", gap: 10, flexWrap: "wrap" }}>
      <div
        style={{
          padding: "12px 14px",
          boxSizing: "border-box",
          borderRadius: 18,
          background: "rgba(255,255,255,0.05)",
          border: "1px solid rgba(255,255,255,0.12)",
          display: "flex",
          flexDirection: "column",
          animation: "vc-rise 0.3s cubic-bezier(0.22,1,0.36,1)",
          justifyContent: "center",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <FileIcon size={14} style={{ flexShrink: 0 }} />
          <span
            style={{
              fontSize: 12.5,
              fontWeight: 600,
              color: "rgba(255,255,255,0.85)",
              whiteSpace: "nowrap",
            }}
          >
            {label} ready to scan
          </span>
        </div>
        {summary.filesTruncated && (
          <span
            style={{
              fontSize: 10,
              fontWeight: 700,
              letterSpacing: "0.02em",
              color: "rgba(255,255,255,0.35)",
              marginTop: 8,
            }}
          >
            Repo is larger than the scan limit — some files were skipped
          </span>
        )}
      </div>
    </div>
  );
}
