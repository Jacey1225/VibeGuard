import { useMemo } from "react";
import type { VibecheckState } from "../../hooks/useVibecheckFlow";
import { useVibecheckFlow } from "../../hooks/useVibecheckFlow";
import { splitSnippet } from "../../utils/snippet";
import { CheckCircleFilledIcon, WarningIcon } from "../icons";

type Actions = ReturnType<typeof useVibecheckFlow>["actions"];

interface DoneScreenProps {
  state: VibecheckState;
  actions: Actions;
}

/** Screen 5: full-screen "done" overlay summarizing what was fixed and what's left. */
export function DoneScreen({ state, actions }: DoneScreenProps) {
  const queuedFindings = useMemo(() => state.findings.filter((f) => f.status === "queued"), [state.findings]);
  const skippedAny = state.findings.filter((f) => f.status !== "queued");
  const queuedCount = queuedFindings.length;

  const achievements = queuedFindings.map((f) => splitSnippet(f.id).achievement);

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
          animation: "vc-wash 0.8s cubic-bezier(0.22,1,0.36,1) forwards",
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
          animation: "vc-pop 0.4s cubic-bezier(0.22,1,0.36,1)",
        }}
      >
        <svg width="46%" height="46%" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2.2} strokeLinecap="round" strokeLinejoin="round">
          <path d="M4.5 12.5l5 5L19.5 7" strokeDasharray={40} style={{ animation: "vc-check-draw 0.4s cubic-bezier(0.65,0,0.35,1) 0.12s backwards" }} />
        </svg>
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
          maxWidth: "20ch",
          animation: "vc-rise 0.4s cubic-bezier(0.22,1,0.36,1) 0.08s backwards",
        }}
      >
        {queuedCount === 1 ? "Your App is Secured" : `${queuedCount} holes closed. Your app is safer.`}
      </h1>

      <p
        style={{
          margin: 0,
          position: "relative",
          fontSize: "clamp(15px, 1.35vw, 19px)",
          lineHeight: 1.5,
          color: "rgba(255,255,255,0.6)",
          maxWidth: "52ch",
          textAlign: "center",
          animation: "vc-rise 0.4s cubic-bezier(0.22,1,0.36,1) 0.14s backwards",
        }}
      >
        The changes are waiting in your project as a suggestion — accept them whenever you’re ready.
      </p>

      <div style={{ position: "relative", display: "flex", flexDirection: "column", gap: 10 }}>
        {achievements.map((text, i) => (
          <div
            key={i}
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
              animation: `vc-rise 0.4s cubic-bezier(0.22,1,0.36,1) ${0.2 + i * 0.07}s backwards`,
            }}
          >
            <CheckCircleFilledIcon size={17} style={{ flexShrink: 0 }} />
            <span style={{ fontSize: "clamp(15px, 1.3vw, 17px)", fontWeight: 600, color: "rgba(255,255,255,0.88)", lineHeight: 1.4 }}>{text}</span>
          </div>
        ))}
      </div>

      {skippedAny.length > 0 && (
        <div style={{ position: "relative", display: "flex", alignItems: "center", gap: 10, animation: "vc-rise 0.4s cubic-bezier(0.22,1,0.36,1) 0.34s backwards" }}>
          <WarningIcon size={16} color="rgba(255,206,116,0.9)" style={{ flexShrink: 0 }} />
          <span style={{ fontSize: 14.5, color: "rgba(255,206,116,0.9)" }}>
            {skippedAny.length === 1
              ? "1 problem left open — you can come back to it anytime."
              : `${skippedAny.length} problems left open — you can come back to them anytime.`}
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
          transition: "all 0.15s ease",
          animation: "vc-rise 0.4s cubic-bezier(0.22,1,0.36,1) 0.4s backwards",
        }}
      >
        Check another project
      </button>
    </div>
  );
}
