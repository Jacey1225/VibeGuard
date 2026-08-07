import { useMemo } from "react";
import type { VibecheckState } from "../../hooks/useVibecheckFlow";
import { useVibecheckFlow } from "../../hooks/useVibecheckFlow";
import { normalizeRelativePath } from "../../utils/path";
import { CheckCircleFilledIcon, WarningIcon } from "../icons";

type Actions = ReturnType<typeof useVibecheckFlow>["actions"];

interface RealRemediationDoneScreenProps {
  state: VibecheckState;
  actions: Actions;
}

/** Screen 5 (real-data path): summarizes real approve/reject/push outcomes -- the real-data counterpart to DoneScreen. */
export function RealRemediationDoneScreen({ state, actions }: RealRemediationDoneScreenProps) {
  const pushed = useMemo(() => state.realRemediations.filter((r) => r.status === "pushed"), [state.realRemediations]);
  const rejected = state.realRemediations.filter((r) => r.status === "rejected");
  const stillPending = state.realRemediations.filter((r) => r.status === "proposed" || r.status === "push_failed");

  return (
    <div
      style={{
        position: "fixed",
        inset: 0,
        zIndex: 20,
        background: "#000000",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        gap: "clamp(14px, 2.4vh, 28px)",
        overflow: "hidden",
        animation: "vc-fade-in 0.2s ease",
      }}
    >
      <div
        style={{
          position: "absolute",
          left: "50%",
          top: "50%",
          width: "150vmax",
          height: "150vmax",
          transform: "translate(-50%, -50%)",
          pointerEvents: "none",
          background: "radial-gradient(circle, rgba(53,224,200,0.20) 0%, rgba(53,224,200,0.05) 32%, rgba(0,0,0,0) 62%)",
        }}
      />

      <div
        style={{
          position: "relative",
          width: "clamp(70px, 10vh, 96px)",
          height: "clamp(70px, 10vh, 96px)",
          borderRadius: "50%",
          background: "rgba(53,224,200,0.12)",
          border: "1px solid rgba(53,224,200,0.45)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          color: "#35E0C8",
        }}
      >
        <CheckCircleFilledIcon size={40} />
      </div>

      <h1
        style={{
          margin: 0,
          position: "relative",
          fontSize: "clamp(28px, min(3.8vw, 5.6vh), 54px)",
          fontWeight: 700,
          letterSpacing: "-0.035em",
          lineHeight: 1.03,
          textAlign: "center",
          maxWidth: "22ch",
        }}
      >
        {pushed.length === 0 ? "No fixes pushed yet" : pushed.length === 1 ? "1 fix pushed to GitHub" : `${pushed.length} fixes pushed to GitHub`}
      </h1>

      <p style={{ margin: 0, position: "relative", fontSize: "clamp(15px, 1.35vw, 19px)", lineHeight: 1.5, color: "rgba(255,255,255,0.6)", maxWidth: "52ch", textAlign: "center" }}>
        Approved fixes were committed directly to {state.sourceLabel.replace("https://github.com/", "")}.
      </p>

      {pushed.length > 0 && (
        <div style={{ position: "relative", display: "flex", flexDirection: "column", gap: 10 }}>
          {pushed.map((r) => (
            <div
              key={r.id}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 12,
                background: "rgba(255,255,255,0.045)",
                border: "1px solid rgba(53,224,200,0.28)",
                borderRadius: 999,
                padding: "11px 22px",
                backdropFilter: "blur(16px)",
                WebkitBackdropFilter: "blur(16px)",
              }}
            >
              <CheckCircleFilledIcon size={17} style={{ flexShrink: 0 }} />
              <span style={{ fontSize: "clamp(15px, 1.3vw, 17px)", fontWeight: 600, color: "rgba(255,255,255,0.88)", lineHeight: 1.4 }}>
                {normalizeRelativePath(r.relative_path)}
              </span>
            </div>
          ))}
        </div>
      )}

      {(stillPending.length > 0 || rejected.length > 0) && (
        <div style={{ position: "relative", display: "flex", alignItems: "center", gap: 10 }}>
          <WarningIcon size={16} color="rgba(255,206,116,0.9)" style={{ flexShrink: 0 }} />
          <span style={{ fontSize: 14.5, color: "rgba(255,206,116,0.9)" }}>
            {stillPending.length > 0
              ? `${stillPending.length} fix(es) still awaiting a decision — you can come back to them anytime.`
              : `${rejected.length} fix(es) rejected.`}
          </span>
        </div>
      )}

      <button
        onClick={actions.resetFlow}
        style={{
          position: "relative",
          background: "none",
          border: "1px solid rgba(255,255,255,0.2)",
          color: "rgba(255,255,255,0.75)",
          height: 52,
          padding: "0 28px",
          borderRadius: 18,
          fontSize: 16,
          fontWeight: 600,
          cursor: "pointer",
          fontFamily: "inherit",
        }}
      >
        Check another project
      </button>
    </div>
  );
}
