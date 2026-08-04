import type { CSSProperties } from "react";
import { ShieldIcon } from "./icons";

interface HeaderProps {
  repoConnected: boolean;
  sourceLabel: string;
}

const barStyle: CSSProperties = {
  position: "relative",
  zIndex: 4,
  flexShrink: 0,
  display: "flex",
  alignItems: "center",
  justifyContent: "space-between",
  gap: 20,
  padding: "clamp(12px, 1.8vh, 20px) clamp(24px, 4vw, 56px)",
  borderBottom: "1px solid rgba(255,255,255,0.08)",
};

const pillStyle: CSSProperties = {
  display: "flex",
  alignItems: "center",
  gap: 10,
  minWidth: 0,
  background: "rgba(255,255,255,0.05)",
  border: "1px solid rgba(255,255,255,0.1)",
  borderRadius: 999,
  padding: "7px 16px",
};

/** Top bar: Vibecheck logo/title, plus a connected-source pill once a repo or paste is attached. */
export function Header({ repoConnected, sourceLabel }: HeaderProps) {
  return (
    <div style={barStyle}>
      <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
        <ShieldIcon size={24} color="#000000" style={{ flexShrink: 0 }} />
        <span style={{ fontSize: 14.5, fontWeight: 700, letterSpacing: "0.16em", textTransform: "uppercase" }}>
          Vibecheck
        </span>
      </div>
      {repoConnected && (
        <div style={pillStyle}>
          <span style={{ width: 7, height: 7, borderRadius: "50%", background: "#35E0C8", flexShrink: 0 }} />
          <span
            style={{
              fontSize: 13.5,
              color: "rgba(255,255,255,0.72)",
              overflow: "hidden",
              textOverflow: "ellipsis",
              whiteSpace: "nowrap",
            }}
          >
            {sourceLabel}
          </span>
        </div>
      )}
    </div>
  );
}
