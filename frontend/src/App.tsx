import { useVibecheckFlow } from "./hooks/useVibecheckFlow";
import { Header } from "./components/Header";
import { StepNav } from "./components/StepNav";
import { ComposerScreen } from "./components/screens/ComposerScreen";
import { ScanningScreen } from "./components/screens/ScanningScreen";
import { FindingsScreen } from "./components/screens/FindingsScreen";
import { FixingScreen } from "./components/screens/FixingScreen";
import { DiffScreen } from "./components/screens/DiffScreen";
import { DoneScreen } from "./components/screens/DoneScreen";

export interface AppProps {
  /** "pills" mirrors the design's default pill-tab stepper; "progress" is the compact bar variant. */
  bottomNavStyle?: "pills" | "progress";
  ambientGlow?: boolean;
  scanSpeed?: number;
}

/**
 * Top-level Vibecheck flow: composer -> scan -> findings -> fix -> diff -> done.
 * A UI-only simulation of VibeGuard's product flow — see frontend/README.md.
 */
export function App({ bottomNavStyle = "pills", ambientGlow = true, scanSpeed = 1 }: AppProps) {
  const { state, actions } = useVibecheckFlow({ scanSpeed });
  const repoConnected = state.screen > 0 && !!state.sourceLabel;

  return (
    <div style={{ position: "relative", height: "100vh", overflow: "hidden", background: "#000000", display: "flex", flexDirection: "column" }}>
      <div
        style={{
          position: "absolute",
          left: "50%",
          top: "-28vh",
          width: "120vw",
          height: "70vh",
          transform: "translateX(-50%)",
          pointerEvents: "none",
          zIndex: 1,
          opacity: ambientGlow ? 1 : 0,
          background: "radial-gradient(ellipse at center, rgba(53,224,200,0.13) 0%, rgba(53,224,200,0) 68%)",
          transition: "opacity 0.3s ease",
        }}
      />

      <Header repoConnected={repoConnected} sourceLabel={state.sourceLabel} />

      <div ref={actions.setMainRef} className="vc-noscroll" style={{ position: "relative", zIndex: 3, flex: 1, minHeight: 0, overflow: "hidden", display: "flex", flexDirection: "column", alignItems: "center" }}>
        <div
          style={{
            width: "100%",
            maxWidth: 1280,
            height: "100%",
            padding: "0 clamp(24px, 4vw, 56px) clamp(6px, 1.2vh, 14px)",
            boxSizing: "border-box",
            display: "flex",
            flexDirection: "column",
            transform: state.morphing ? "scale(0.965) translateY(-14px)" : "none",
            opacity: state.morphing ? 0 : 1,
            filter: state.morphing ? "blur(7px)" : "none",
            transition: "transform 0.26s cubic-bezier(0.4,0,0.2,1), opacity 0.22s ease, filter 0.26s ease",
            animation: state.morphing ? undefined : "vc-morph-in 0.34s cubic-bezier(0.22,1,0.36,1)",
          }}
        >
          {state.screen === 0 && <ComposerScreen state={state} actions={actions} />}
          {state.screen === 1 && <ScanningScreen state={state} actions={actions} />}
          {state.screen === 2 && <FindingsScreen state={state} actions={actions} />}
          {state.screen === 3 && <FixingScreen state={state} />}
          {state.screen === 4 && <DiffScreen state={state} actions={actions} />}
        </div>
      </div>

      {state.screen === 5 && <DoneScreen state={state} actions={actions} />}

      <StepNav screen={state.screen} variant={bottomNavStyle} />
    </div>
  );
}
