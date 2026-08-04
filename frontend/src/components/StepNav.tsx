import type { CSSProperties, ReactNode } from "react";
import { ApproveIcon, CheckThinIcon, ConnectIcon, DiffIcon, ImplementIcon, PipelineIcon } from "./icons";

export type BottomNavStyle = "pills" | "progress";

interface StepDef {
  key: "connect" | "pipeline" | "approve" | "implement" | "diff" | "propened";
  label: string;
}

const STEP_DEFS: readonly StepDef[] = [
  { key: "connect", label: "Connect" },
  { key: "pipeline", label: "Check" },
  { key: "approve", label: "Decide" },
  { key: "implement", label: "Fix" },
  { key: "diff", label: "Review" },
  { key: "propened", label: "Done" },
];

const STEP_ICONS: Record<StepDef["key"], (color: string) => ReactNode> = {
  connect: (color) => <ConnectIcon size={17} style={{ color }} />,
  pipeline: (color) => <PipelineIcon size={17} style={{ color }} />,
  approve: (color) => <ApproveIcon size={17} style={{ color }} />,
  implement: (color) => <ImplementIcon size={17} style={{ color }} />,
  diff: (color) => <DiffIcon size={17} style={{ color }} />,
  propened: (color) => <CheckThinIcon size={17} color={color} />,
};

interface StepNavProps {
  screen: number;
  variant: BottomNavStyle;
}

type StepPhase = "done" | "current" | "upcoming";

function phaseOf(index: number, screen: number): StepPhase {
  if (index < screen) return "done";
  if (index === screen) return "current";
  return "upcoming";
}

/** Bottom step indicator: pill-tab list or a compact progress-dot bar. */
export function StepNav({ screen, variant }: StepNavProps) {
  const wrapStyle: CSSProperties = {
    position: "relative",
    zIndex: 5,
    flexShrink: 0,
    width: "100%",
    display: "flex",
    justifyContent: "center",
    padding: "clamp(8px, 1.4vh, 14px) 0 clamp(12px, 2vh, 22px)",
  };

  if (variant === "pills") {
    return (
      <div style={wrapStyle}>
        <div
          style={{
            background: "rgba(255,255,255,0.05)",
            border: "1px solid rgba(255,255,255,0.1)",
            backdropFilter: "blur(20px)",
            WebkitBackdropFilter: "blur(20px)",
            borderRadius: 26,
            padding: 7,
            display: "flex",
            alignItems: "center",
            gap: 2,
          }}
        >
          {STEP_DEFS.map((step, i) => {
            const phase = phaseOf(i, screen);
            const iconColor = phase === "current" ? "#35E0C8" : phase === "done" ? "rgba(53,224,200,0.65)" : "rgba(255,255,255,0.3)";
            return (
              <div
                key={step.key}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 8,
                  padding: "9px 14px",
                  borderRadius: 19,
                  minHeight: 42,
                  boxSizing: "border-box",
                  background: phase === "current" ? "rgba(53,224,200,0.14)" : "transparent",
                  transition: "background 0.18s ease",
                }}
              >
                <div style={{ width: 19, height: 19, display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>
                  {STEP_ICONS[step.key](iconColor)}
                </div>
                <span
                  style={{
                    fontSize: 12.5,
                    whiteSpace: "nowrap",
                    fontWeight: phase === "current" ? 700 : 500,
                    color: phase === "current" ? "#FFFFFF" : phase === "done" ? "rgba(255,255,255,0.6)" : "rgba(255,255,255,0.3)",
                  }}
                >
                  {step.label}
                </span>
              </div>
            );
          })}
        </div>
      </div>
    );
  }

  return (
    <div style={wrapStyle}>
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 18,
          background: "rgba(255,255,255,0.05)",
          border: "1px solid rgba(255,255,255,0.1)",
          backdropFilter: "blur(20px)",
          WebkitBackdropFilter: "blur(20px)",
          borderRadius: 999,
          padding: "10px 22px",
        }}
      >
        <span style={{ fontSize: 13, fontWeight: 700, letterSpacing: "0.06em", whiteSpace: "nowrap" }}>
          {STEP_DEFS[screen].label}
        </span>
        <div style={{ display: "flex", alignItems: "center" }}>
          {STEP_DEFS.map((step, i) => {
            const isCurrent = i === screen;
            const passed = i <= screen;
            return (
              <div key={step.key} style={{ display: "flex", alignItems: "center" }}>
                {i > 0 && (
                  <div
                    style={{
                      width: 14,
                      height: 2,
                      borderRadius: 2,
                      background: passed ? "#35E0C8" : "rgba(255,255,255,0.16)",
                      transition: "background 0.25s ease",
                    }}
                  />
                )}
                <div
                  title={step.label}
                  style={{
                    width: isCurrent ? 13 : 9,
                    height: isCurrent ? 13 : 9,
                    borderRadius: "50%",
                    flexShrink: 0,
                    background: passed ? "#35E0C8" : "rgba(255,255,255,0.18)",
                    boxShadow: isCurrent ? "0 0 0 5px rgba(53,224,200,0.18)" : "none",
                    transition: "all 0.25s ease",
                  }}
                />
              </div>
            );
          })}
        </div>
        <span style={{ fontSize: 13, color: "rgba(255,255,255,0.45)", whiteSpace: "nowrap" }}>
          {`Step ${screen + 1} of 6`}
        </span>
      </div>
    </div>
  );
}
