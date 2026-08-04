import type { RepositoryFile } from "../../hooks/useVibecheckFlow";
import { FILES } from "../../data/fixtures";
import { FileIcon } from "../icons";

interface AttachmentChipsProps {
  files?: RepositoryFile[];
}

/** File preview chips shown in the composer once a repo is connected. */
export function AttachmentChips({ files }: AttachmentChipsProps) {
  const attachments = files && files.length > 0 ? files : FILES.slice(0, 3);

  return (
    <div style={{ display: "flex", alignItems: "stretch", gap: 10, flexWrap: "wrap" }}>
      {attachments.map((file, idx) => {
        const isEllipsis = "isEllipsis" in file && file.isEllipsis;

        return (
          <div
            key={isEllipsis ? "ellipsis" : file.name}
            style={{
              width: isEllipsis ? "auto" : 132,
              padding: isEllipsis ? "12px 14px" : "12px 14px",
              boxSizing: "border-box",
              borderRadius: 18,
              background: isEllipsis ? "transparent" : "rgba(255,255,255,0.05)",
              border: isEllipsis ? "none" : "1px solid rgba(255,255,255,0.12)",
              display: "flex",
              flexDirection: "column",
              animation: "vc-rise 0.3s cubic-bezier(0.22,1,0.36,1)",
              justifyContent: "center",
            }}
          >
            {isEllipsis ? (
              <span
                style={{
                  fontSize: 16,
                  fontWeight: 600,
                  color: "rgba(255,255,255,0.45)",
                  lineHeight: 1,
                }}
              >
                {file.name}
              </span>
            ) : (
              <>
                <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
                  <FileIcon size={14} style={{ flexShrink: 0 }} />
                  <span
                    style={{
                      fontSize: 12.5,
                      fontWeight: 600,
                      color: "rgba(255,255,255,0.85)",
                      overflow: "hidden",
                      textOverflow: "ellipsis",
                      whiteSpace: "nowrap",
                    }}
                  >
                    {file.name}
                  </span>
                </div>
                <span style={{ fontSize: 10, fontWeight: 700, letterSpacing: "0.06em", textTransform: "uppercase", color: "rgba(255,255,255,0.35)", marginTop: 8 }}>
                  {file.language || "File"}
                </span>
              </>
            )}
          </div>
        );
      })}
    </div>
  );
}
