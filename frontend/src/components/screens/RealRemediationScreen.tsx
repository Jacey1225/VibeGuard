import type { VibecheckState } from "../../hooks/useVibecheckFlow";
import { useVibecheckFlow } from "../../hooks/useVibecheckFlow";
import { SpinnerIcon, WarningIcon } from "../icons";

type Actions = ReturnType<typeof useVibecheckFlow>["actions"];

interface RealRemediationScreenProps {
  state: VibecheckState;
  actions: Actions;
}

/** Screen 3 (real-data path): blocks on `POST /repositories/{id}/remediate` -- the real-data counterpart to FixingScreen's simulated timer. */
export function RealRemediationScreen({ state, actions }: RealRemediationScreenProps) {
  return (
    <div style={{ flex: 1, minHeight: 0, display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: "clamp(14px, 2.4vh, 24px)" }}>
      <span style={{ fontSize: 11.5, fontWeight: 700, letterSpacing: "0.22em", textTransform: "uppercase", color: "#35E0C8" }}>Step 4 — fixing</span>

      {state.remediationError ? (
        <>
          <div style={{ display: "flex", alignItems: "center", gap: 10, maxWidth: "48ch", textAlign: "center" }}>
            <WarningIcon size={20} style={{ flexShrink: 0 }} />
            <span style={{ fontSize: 15.5, color: "rgba(255,255,255,0.82)" }}>{state.remediationError}</span>
          </div>
          <button
            onClick={actions.startRemediation}
            style={{
              background: "#35E0C8",
              color: "#04120F",
              border: "none",
              height: 48,
              padding: "0 26px",
              borderRadius: 16,
              fontSize: 15,
              fontWeight: 700,
              cursor: "pointer",
              fontFamily: "inherit",
            }}
          >
            Try again
          </button>
        </>
      ) : (
        <>
          <SpinnerIcon size={30} style={{ animation: "vc-spin 0.8s linear infinite" }} />
          <h1 style={{ margin: 0, fontSize: "clamp(21px, min(2.8vw, 4.4vh), 38px)", fontWeight: 700, letterSpacing: "-0.03em", lineHeight: 1.05, textAlign: "center" }}>
            Generating fixes for {state.sourceLabel.replace("https://github.com/", "")}…
          </h1>
          <p style={{ margin: 0, fontSize: 14.5, color: "rgba(255,255,255,0.5)", maxWidth: "42ch", textAlign: "center" }}>
            One LLM call per file with findings — this can take a moment for repos with several affected files.
          </p>
        </>
      )}
    </div>
  );
}
