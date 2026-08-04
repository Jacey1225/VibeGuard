import { useMemo } from "react";
import type { VibecheckState } from "../../hooks/useVibecheckFlow";
import { useVibecheckFlow } from "../../hooks/useVibecheckFlow";
import { detectLanguage } from "../../utils/detectLanguage";
import { PLACEHOLDERS } from "../../data/fixtures";
import { AttachmentChips } from "../composer/AttachmentChips";
import { ScopeMenu } from "../composer/ScopeMenu";
import { SourceMenu } from "../composer/SourceMenu";
import { ArrowUpIcon, LockIcon, PlusIcon, ScopeShieldIcon, ChevronDownIcon, SpinnerIcon } from "../icons";
import { FONT } from "../../styles/tokens";

type Actions = ReturnType<typeof useVibecheckFlow>["actions"];

interface ComposerScreenProps {
  state: VibecheckState;
  actions: Actions;
}

const CONNECT_STATUS_LABELS = ["Signing in to GitHub…", "Reading your project…", "Picking the files that matter…"];

/** Screen 0: paste-code / connect-GitHub composer that kicks off a check. */
export function ComposerScreen({ state, actions }: ComposerScreenProps) {
  const lang = useMemo(() => detectLanguage(state.codeInput), [state.codeInput]);
  const canSubmit = !!state.codeInput.trim() || state.attached;
  const composerActive = state.composerFocused || state.codeInput.length > 0 || state.attached;
  const scopeOnCount = Object.values(state.scopeSelected).filter((v) => v !== false).length;
  const scopeTotal = Object.keys(state.scopeSelected).length;
  const allScopeOn = scopeOnCount === scopeTotal;

  return (
    <div
      style={{
        flex: 1,
        minHeight: 0,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        gap: "clamp(12px, 2.2vh, 26px)",
        padding: "clamp(8px, 1.5vh, 16px) 0",
        boxSizing: "border-box",
      }}
    >
      {!state.attached && (
        <span style={{ flexShrink: 0, fontSize: "clamp(10.5px, 1.1vw, 12px)", fontWeight: 700, letterSpacing: "0.22em", textTransform: "uppercase", color: "#35E0C8" }}>
          Security check for vibe-coded apps
        </span>
      )}
      <h1
        style={{
          margin: 0,
          flexShrink: 0,
          fontSize: state.attached ? "clamp(22px, min(3.4vw, 4.4vh), 42px)" : "clamp(26px, min(4.6vw, 5.8vh), 60px)",
          fontWeight: 700,
          letterSpacing: "-0.035em",
          lineHeight: 1.03,
          textAlign: "center",
          maxWidth: "15ch",
          textWrap: "balance",
          transition: "font-size 0.26s cubic-bezier(0.22,1,0.36,1)",
        }}
      >
        Find what&apos;s unsafe in your app.
      </h1>
      {!state.attached && (
        <p
          style={{
            margin: 0,
            flexShrink: 0,
            fontSize: "clamp(14px, min(1.3vw, 2vh), 18px)",
            lineHeight: 1.45,
            color: "rgba(255,255,255,0.6)",
            maxWidth: "54ch",
            textAlign: "center",
            textWrap: "pretty",
          }}
        >
          We look for the security mistakes AI coding tools leave behind, explain each one in plain English, and fix
          only the ones you approve.
        </p>
      )}

      <div style={{ width: "100%", maxWidth: 800, flexShrink: 0, display: "flex", flexDirection: "column", gap: 10 }}>
        <span style={{ fontSize: 14, color: "rgba(255,255,255,0.45)", paddingLeft: 6 }}>
          Connect your project, or just paste some code. No instructions needed.
        </span>

        <div
          style={{
            position: "relative",
            display: "flex",
            flexDirection: "column",
            gap: 14,
            padding: "20px 20px 18px",
            boxSizing: "border-box",
            borderRadius: 30,
            background: "rgba(255,255,255,0.05)",
            border: `1px solid ${composerActive ? "rgba(53,224,200,0.5)" : "rgba(255,255,255,0.12)"}`,
            backdropFilter: "blur(20px)",
            WebkitBackdropFilter: "blur(20px)",
            boxShadow: composerActive ? "0 0 0 4px rgba(53,224,200,0.08)" : "none",
            transition: "border-color 0.15s ease, box-shadow 0.15s ease",
          }}
        >
          {state.connecting && (
            <div
              style={{
                position: "absolute",
                inset: 0,
                zIndex: 9,
                borderRadius: 30,
                background: "rgba(8,10,10,0.82)",
                backdropFilter: "blur(20px)",
                WebkitBackdropFilter: "blur(20px)",
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                justifyContent: "center",
                gap: 16,
                animation: "vc-fade-in 0.2s ease",
              }}
            >
              <SpinnerIcon size={30} />
              <span style={{ fontSize: 16, fontWeight: 600, color: "#FFFFFF" }}>
                {CONNECT_STATUS_LABELS[Math.min(2, state.connectStep)]}
              </span>
              <div style={{ width: 220, height: 4, borderRadius: 3, background: "rgba(255,255,255,0.1)", overflow: "hidden" }}>
                <div
                  style={{
                    height: "100%",
                    borderRadius: 3,
                    background: "#35E0C8",
                    width: `${Math.min(100, (state.connectStep + 1) * 33)}%`,
                    transition: "width 0.4s cubic-bezier(0.22,1,0.36,1)",
                  }}
                />
              </div>
            </div>
          )}

          {state.attached && (
            <div style={{ display: "flex", alignItems: "center", gap: 12, width: "100%", marginBottom: 8 }}>
              <div
                style={{
                  padding: "8px 12px",
                  borderRadius: 12,
                  background: "rgba(53,224,200,0.12)",
                  border: "1px solid rgba(53,224,200,0.3)",
                  display: "flex",
                  alignItems: "center",
                  gap: 8,
                  flex: 1,
                }}
              >
                <span style={{ fontSize: 13, fontWeight: 600, color: "#35E0C8", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                  Connected to {state.sourceLabel.replace("https://github.com/", "")}
                </span>
                <button
                  onClick={actions.disconnectRepo}
                  title="Disconnect repository"
                  style={{
                    background: "none",
                    border: "none",
                    color: "rgba(53,224,200,0.7)",
                    cursor: "pointer",
                    fontSize: 18,
                    padding: 0,
                    marginLeft: "auto",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    width: 20,
                    height: 20,
                    transition: "color 0.2s ease",
                  }}
                  onMouseEnter={(e) => (e.currentTarget.style.color = "#35E0C8")}
                  onMouseLeave={(e) => (e.currentTarget.style.color = "rgba(53,224,200,0.7)")}
                >
                  ✕
                </button>
              </div>
            </div>
          )}

          {state.attached && <AttachmentChips files={state.attachedFiles} />}

          <textarea
            ref={actions.setInputRef}
            value={state.codeInput}
            onChange={actions.onCodeInput}
            onFocus={actions.onComposerFocus}
            onBlur={actions.onComposerBlur}
            placeholder={state.attached ? "" : PLACEHOLDERS[state.placeholderIdx]}
            spellCheck={false}
            disabled={state.attached}
            style={{
              width: "100%",
              boxSizing: "border-box",
              resize: "none",
              background: state.attached ? "rgba(255,255,255,0.02)" : "none",
              border: "none",
              outline: "none",
              color: state.attached ? "rgba(255,255,255,0.3)" : "#FFFFFF",
              fontFamily: FONT.mono,
              fontSize: 14.5,
              lineHeight: 1.7,
              height: state.attached ? "clamp(56px, 8vh, 84px)" : "clamp(84px, 14vh, 132px)",
              padding: 0,
              cursor: state.attached ? "not-allowed" : "text",
              transition: "height 0.26s cubic-bezier(0.22,1,0.36,1), background 0.2s ease, color 0.2s ease",
            }}
          />

          {state.suggestedRepoUrl && !state.attached && (
            <div
              style={{
                padding: "12px 14px",
                borderRadius: 14,
                background: "rgba(53,224,200,0.08)",
                border: "1px solid rgba(53,224,200,0.3)",
                display: "flex",
                alignItems: "center",
                gap: 12,
                animation: "vc-pop 0.25s ease",
              }}
            >
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: 12, fontWeight: 600, color: "rgba(255,255,255,0.5)", marginBottom: 4 }}>
                  GitHub repository detected
                </div>
                <div style={{ fontSize: 14, fontWeight: 600, color: "#35E0C8" }}>
                  {state.suggestedRepoUrl.replace("https://github.com/", "")}
                </div>
              </div>
              <button
                onClick={() => actions.connectSuggestedRepo(state.suggestedRepoUrl!)}
                style={{
                  flexShrink: 0,
                  padding: "8px 14px",
                  borderRadius: 12,
                  background: "#35E0C8",
                  border: "none",
                  color: "#04120F",
                  fontSize: 13,
                  fontWeight: 600,
                  fontFamily: "inherit",
                  cursor: "pointer",
                  transition: "all 0.15s ease",
                }}
                onMouseEnter={(e) => {
                  e.currentTarget.style.background = "#2BC9B3";
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.background = "#35E0C8";
                }}
              >
                Connect
              </button>
            </div>
          )}

          <div style={{ display: "flex", alignItems: "center", gap: 10, flexWrap: "wrap" }}>
            <button
              onClick={actions.toggleSourceMenu}
              title="Connect GitHub"
              style={{
                width: 44,
                height: 44,
                flexShrink: 0,
                borderRadius: 16,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                background: state.sourceMenuOpen ? "rgba(53,224,200,0.16)" : "rgba(255,255,255,0.08)",
                border: `1px solid ${state.sourceMenuOpen ? "rgba(53,224,200,0.5)" : "rgba(255,255,255,0.16)"}`,
                color: state.sourceMenuOpen ? "#35E0C8" : "#FFFFFF",
                cursor: "pointer",
                padding: 0,
                transform: `rotate(${state.sourceMenuOpen ? 45 : 0}deg)`,
                transition: "all 0.16s cubic-bezier(0.22,1,0.36,1)",
              }}
            >
              <PlusIcon size={20} />
            </button>

            <button
              onClick={actions.toggleScopeMenu}
              style={{
                display: "flex",
                alignItems: "center",
                gap: 9,
                height: 44,
                padding: "0 16px",
                borderRadius: 16,
                background: state.scopeMenuOpen ? "rgba(53,224,200,0.14)" : "rgba(255,255,255,0.06)",
                border: `1px solid ${state.scopeMenuOpen ? "rgba(53,224,200,0.45)" : "rgba(255,255,255,0.14)"}`,
                color: state.scopeMenuOpen ? "#35E0C8" : "rgba(255,255,255,0.85)",
                fontSize: 14,
                fontWeight: 600,
                fontFamily: "inherit",
                cursor: "pointer",
                whiteSpace: "nowrap",
                transition: "all 0.16s ease",
              }}
            >
              <ScopeShieldIcon size={16} />
              {allScopeOn ? "All 6 areas" : `${scopeOnCount} of 6 areas`}
              <ChevronDownIcon
                size={14}
                style={{ transform: `rotate(${state.scopeMenuOpen ? 180 : 0}deg)`, transition: "transform 0.18s ease" }}
              />
            </button>

            {!!lang && (
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 8,
                  background: "rgba(53,224,200,0.12)",
                  color: "#35E0C8",
                  borderRadius: 999,
                  padding: "7px 15px",
                  animation: "vc-pop 0.25s ease",
                }}
              >
                <span style={{ width: 6, height: 6, borderRadius: "50%", background: "currentColor" }} />
                <span style={{ fontSize: 13, fontWeight: 700 }}>{lang}</span>
              </div>
            )}

            <button
              onClick={actions.submitComposer}
              disabled={!canSubmit}
              title="Start the check"
              style={{
                width: 44,
                height: 44,
                flexShrink: 0,
                marginLeft: "auto",
                borderRadius: 16,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                border: "none",
                padding: 0,
                background: canSubmit ? "#35E0C8" : "rgba(255,255,255,0.08)",
                color: canSubmit ? "#04120F" : "rgba(255,255,255,0.3)",
                cursor: canSubmit ? "pointer" : "not-allowed",
                transition: "all 0.16s ease",
              }}
            >
              <ArrowUpIcon size={20} />
            </button>
          </div>

          {state.sourceMenuOpen && (
            <SourceMenu
              onPasteExample={actions.pasteExample}
              repoUrlInput={state.repoUrlInput}
              repoUrlLoading={state.repoUrlLoading}
              repoUrlError={state.repoUrlError}
              onRepoUrlInput={actions.onRepoUrlInput}
              onSubmitRepoUrl={actions.submitRepoUrl}
              onClearError={actions.clearRepoUrlError}
            />
          )}
          {state.scopeMenuOpen && (
            <ScopeMenu
              scopeSelected={state.scopeSelected}
              onToggle={actions.toggleScope}
              onToggleAll={actions.toggleAllScope}
              onBackgroundClick={actions.closeScopeMenu}
            />
          )}
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: 9, paddingLeft: 6 }}>
          <LockIcon size={14} />
          <p style={{ margin: 0, fontSize: 13.5, color: "rgba(255,255,255,0.45)" }}>
            We only read. Nothing changes until you say so.
          </p>
        </div>
      </div>
    </div>
  );
}
