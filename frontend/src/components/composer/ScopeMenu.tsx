import { useState } from "react";
import { SCOPE_ITEMS } from "../../data/fixtures";
import { CheckIcon, InfoIcon } from "../icons";

interface ScopeMenuProps {
  scopeSelected: Record<string, boolean>;
  onToggle: (key: string) => void;
  onToggleAll: () => void;
  onBackgroundClick: () => void;
}

/** Popup below the composer's scope button: which check categories are on. */
export function ScopeMenu({ scopeSelected, onToggle, onToggleAll, onBackgroundClick }: ScopeMenuProps) {
  const [infoOpen, setInfoOpen] = useState<string | null>(null);
  const scopeOnCount = SCOPE_ITEMS.filter((item) => scopeSelected[item.key] !== false).length;
  const allOn = scopeOnCount === SCOPE_ITEMS.length;

  return (
    <>
      <div onClick={onBackgroundClick} style={{ position: "fixed", inset: 0, zIndex: 9 }} />
      <div
        onClick={(e) => e.stopPropagation()}
        style={{
          position: "absolute",
          left: 18,
          right: 18,
          bottom: 74,
          zIndex: 10,
          background: "rgba(16,18,18,0.94)",
          border: "1px solid rgba(255,255,255,0.14)",
          borderRadius: 26,
          backdropFilter: "blur(24px)",
          WebkitBackdropFilter: "blur(24px)",
          padding: "16px 18px 14px",
          display: "flex",
          flexDirection: "column",
          gap: 2,
          animation: "vc-fade-in 0.15s ease",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12, paddingBottom: 10 }}>
          <span style={{ fontSize: 11.5, fontWeight: 700, letterSpacing: "0.18em", textTransform: "uppercase", color: "rgba(255,255,255,0.42)" }}>
            What we check
          </span>
          <button
            onClick={onToggleAll}
            style={{ background: "none", border: "none", color: "#35E0C8", fontSize: 13.5, fontWeight: 700, fontFamily: "inherit", cursor: "pointer", padding: "4px 6px" }}
          >
            {allOn ? "Clear all" : "Select all"}
          </button>
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(2, minmax(0, 1fr))", columnGap: 22 }}>
          {SCOPE_ITEMS.map((item) => {
            const checked = scopeSelected[item.key] !== false;
            const showInfo = infoOpen === item.key;
            return (
              <div key={item.key} style={{ display: "flex", alignItems: "center", gap: 11, padding: "9px 0", transition: "opacity 0.15s ease", opacity: checked ? 1 : 0.5 }}>
                <button
                  onClick={() => onToggle(item.key)}
                  aria-pressed={checked}
                  style={{
                    width: 22,
                    height: 22,
                    borderRadius: 7,
                    flexShrink: 0,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    boxSizing: "border-box",
                    cursor: "pointer",
                    padding: 0,
                    border: `2px solid ${checked ? "#35E0C8" : "rgba(255,255,255,0.3)"}`,
                    background: checked ? "#35E0C8" : "transparent",
                    transition: "all 0.13s ease",
                  }}
                >
                  {checked && <CheckIcon size={13} />}
                </button>
                <span style={{ fontSize: 14.5, lineHeight: 1.3, color: checked ? "#FFFFFF" : "rgba(255,255,255,0.55)", flex: 1, minWidth: 0 }}>
                  {item.label}
                </span>
                <div
                  onMouseEnter={() => setInfoOpen(item.key)}
                  onMouseLeave={() => setInfoOpen(null)}
                  style={{ position: "relative", width: 26, height: 26, flexShrink: 0, display: "flex", alignItems: "center", justifyContent: "center", cursor: "help" }}
                >
                  <InfoIcon size={16} color={showInfo ? "#35E0C8" : "rgba(255,255,255,0.4)"} />
                  {showInfo && (
                    <div
                      style={{
                        position: "absolute",
                        bottom: 30,
                        left: "50%",
                        transform: "translateX(-50%)",
                        zIndex: 12,
                        width: 250,
                        padding: "12px 14px",
                        boxSizing: "border-box",
                        borderRadius: 16,
                        background: "rgba(28,31,31,0.98)",
                        border: "1px solid rgba(255,255,255,0.16)",
                        boxShadow: "0 12px 34px rgba(0,0,0,0.6)",
                        fontSize: 13.5,
                        lineHeight: 1.45,
                        color: "rgba(255,255,255,0.8)",
                        animation: "vc-fade-in 0.12s ease",
                      }}
                    >
                      {item.desc}
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </>
  );
}
