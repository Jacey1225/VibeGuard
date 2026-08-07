import { useState } from "react";
import { GithubIcon, PasteIcon } from "../icons";
import { FONT } from "../../styles/tokens";

interface SourceMenuProps {
  onPasteExample: () => void;
  repoUrlInput: string;
  repoUrlLoading: boolean;
  repoUrlError: string | null;
  onRepoUrlInput: (e: React.ChangeEvent<HTMLInputElement>) => void;
  onSubmitRepoUrl: () => void;
  onClearError: () => void;
  /** The GitHub-free path: paste real code and scan it directly, with zero GitHub interaction. Fully separate from `onPasteExample` (which loads fixture demo code, not a real scan). */
  snippetPasteInput: string;
  snippetPasteLoading: boolean;
  snippetPasteError: string | null;
  onSnippetPasteInput: (e: React.ChangeEvent<HTMLTextAreaElement>) => void;
  onSubmitSnippetPaste: () => void;
  onClearSnippetPasteError: () => void;
}

const itemBaseStyle = {
  display: "flex",
  alignItems: "center",
  gap: 12,
  background: "none",
  border: "none",
  textAlign: "left" as const,
  padding: "13px 15px",
  borderRadius: 18,
  fontSize: 15.5,
  fontWeight: 600,
  fontFamily: "inherit",
  cursor: "pointer",
  transition: "background 0.12s ease",
};

type MenuView = "menu" | "repo" | "snippet";

/** Popup below the composer's "+" button: connect a GitHub repo, paste example code, or scan pasted code with no GitHub connection at all. */
export function SourceMenu({
  onPasteExample,
  repoUrlInput,
  repoUrlLoading,
  repoUrlError,
  onRepoUrlInput,
  onSubmitRepoUrl,
  onClearError,
  snippetPasteInput,
  snippetPasteLoading,
  snippetPasteError,
  onSnippetPasteInput,
  onSubmitSnippetPaste,
  onClearSnippetPasteError,
}: SourceMenuProps) {
  const [view, setView] = useState<MenuView>("menu");
  const [hovered, setHovered] = useState<"github" | "paste" | "snippet" | null>(null);

  const handleConnectClick = () => {
    onClearError();
    setView("repo");
  };

  const handleScanSnippetClick = () => {
    onClearSnippetPasteError();
    setView("snippet");
  };

  const handleBack = () => {
    setView("menu");
  };

  const handleSubmit = () => {
    onSubmitRepoUrl();
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !repoUrlLoading) {
      handleSubmit();
    }
  };

  return (
    <div
      style={{
        position: "absolute",
        left: 18,
        bottom: 74,
        zIndex: 10,
        background: "rgba(16,18,18,0.94)",
        border: "1px solid rgba(255,255,255,0.14)",
        borderRadius: 24,
        backdropFilter: "blur(24px)",
        WebkitBackdropFilter: "blur(24px)",
        padding: 8,
        display: "flex",
        flexDirection: "column",
        gap: 4,
        minWidth: 290,
        animation: "vc-fade-in 0.15s ease",
      }}
    >
      {view === "menu" && (
        <>
          <button
            onClick={handleConnectClick}
            onMouseEnter={() => setHovered("github")}
            onMouseLeave={() => setHovered(null)}
            style={{
              ...itemBaseStyle,
              color: "#FFFFFF",
              background: hovered === "github" ? "rgba(255,255,255,0.08)" : "none",
            }}
          >
            <GithubIcon size={21} style={{ flexShrink: 0 }} />
            Connect a GitHub project
          </button>
          <button
            onClick={onPasteExample}
            onMouseEnter={() => setHovered("paste")}
            onMouseLeave={() => setHovered(null)}
            style={{
              ...itemBaseStyle,
              color: "rgba(255,255,255,0.75)",
              background: hovered === "paste" ? "rgba(255,255,255,0.08)" : "none",
            }}
          >
            <PasteIcon size={21} style={{ flexShrink: 0 }} />
            Try it with example code
          </button>
          <button
            onClick={handleScanSnippetClick}
            onMouseEnter={() => setHovered("snippet")}
            onMouseLeave={() => setHovered(null)}
            style={{
              ...itemBaseStyle,
              color: "rgba(255,255,255,0.75)",
              background: hovered === "snippet" ? "rgba(255,255,255,0.08)" : "none",
            }}
          >
            <PasteIcon size={21} style={{ flexShrink: 0 }} />
            Scan pasted code — no GitHub needed
          </button>
        </>
      )}
      {view === "repo" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 12, padding: "8px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
            <GithubIcon size={20} style={{ flexShrink: 0, color: "#35E0C8" }} />
            <span style={{ fontSize: 14, fontWeight: 600, color: "#FFFFFF" }}>Paste repository URL</span>
          </div>

          <input
            type="text"
            value={repoUrlInput}
            onChange={onRepoUrlInput}
            onKeyDown={handleKeyDown}
            placeholder="https://github.com/owner/repo"
            autoFocus
            disabled={repoUrlLoading}
            style={{
              width: "100%",
              boxSizing: "border-box",
              padding: "10px 12px",
              borderRadius: 12,
              background: "rgba(255,255,255,0.08)",
              border: repoUrlError ? "1px solid rgba(255,59,48,0.6)" : "1px solid rgba(255,255,255,0.16)",
              color: "#FFFFFF",
              fontSize: 13,
              fontFamily: "inherit",
              outline: "none",
              transition: "border-color 0.15s ease, background 0.15s ease",
            }}
          />

          {repoUrlError && (
            <div
              style={{
                fontSize: 12,
                color: "rgba(255,59,48,0.9)",
                padding: "8px 12px",
                background: "rgba(255,59,48,0.08)",
                borderRadius: 8,
                lineHeight: 1.4,
              }}
            >
              {repoUrlError}
            </div>
          )}

          <div style={{ display: "flex", gap: 8, marginTop: 4 }}>
            <button
              onClick={handleBack}
              disabled={repoUrlLoading}
              style={{
                flex: 1,
                padding: "10px 14px",
                borderRadius: 12,
                background: "rgba(255,255,255,0.08)",
                border: "1px solid rgba(255,255,255,0.14)",
                color: "rgba(255,255,255,0.75)",
                fontSize: 13,
                fontWeight: 600,
                fontFamily: "inherit",
                cursor: "pointer",
                transition: "all 0.12s ease",
              }}
            >
              Back
            </button>
            <button
              onClick={handleSubmit}
              disabled={repoUrlLoading || !repoUrlInput.trim()}
              style={{
                flex: 1,
                padding: "10px 14px",
                borderRadius: 12,
                background: repoUrlLoading || !repoUrlInput.trim() ? "rgba(53,224,200,0.3)" : "#35E0C8",
                border: "none",
                color: repoUrlLoading || !repoUrlInput.trim() ? "rgba(255,255,255,0.4)" : "#04120F",
                fontSize: 13,
                fontWeight: 600,
                fontFamily: "inherit",
                cursor: repoUrlLoading || !repoUrlInput.trim() ? "not-allowed" : "pointer",
                transition: "all 0.12s ease",
              }}
            >
              {repoUrlLoading ? "Connecting..." : "Connect"}
            </button>
          </div>
        </div>
      )}
      {view === "snippet" && (
        <div style={{ display: "flex", flexDirection: "column", gap: 12, padding: "8px", width: 340 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
            <PasteIcon size={20} style={{ flexShrink: 0, color: "#35E0C8" }} />
            <span style={{ fontSize: 14, fontWeight: 600, color: "#FFFFFF" }}>Paste your code</span>
          </div>

          <label htmlFor="vc-snippet-paste-textarea" style={{ fontSize: 12, color: "rgba(255,255,255,0.55)" }}>
            Your code (scanned directly -- no repository connection)
          </label>
          <textarea
            id="vc-snippet-paste-textarea"
            value={snippetPasteInput}
            onChange={onSnippetPasteInput}
            placeholder="Paste code to scan here"
            autoFocus
            disabled={snippetPasteLoading}
            spellCheck={false}
            rows={7}
            style={{
              width: "100%",
              boxSizing: "border-box",
              resize: "none",
              padding: "10px 12px",
              borderRadius: 12,
              background: "rgba(255,255,255,0.08)",
              border: snippetPasteError ? "1px solid rgba(255,59,48,0.6)" : "1px solid rgba(255,255,255,0.16)",
              color: "#FFFFFF",
              fontSize: 12.5,
              fontFamily: FONT.mono,
              outline: "none",
              transition: "border-color 0.15s ease, background 0.15s ease",
            }}
          />

          {snippetPasteError && (
            <div
              role="alert"
              style={{
                fontSize: 12,
                color: "rgba(255,59,48,0.9)",
                padding: "8px 12px",
                background: "rgba(255,59,48,0.08)",
                borderRadius: 8,
                lineHeight: 1.4,
              }}
            >
              {snippetPasteError}
            </div>
          )}

          <div style={{ display: "flex", gap: 8, marginTop: 4 }}>
            <button
              onClick={handleBack}
              disabled={snippetPasteLoading}
              style={{
                flex: 1,
                padding: "10px 14px",
                borderRadius: 12,
                background: "rgba(255,255,255,0.08)",
                border: "1px solid rgba(255,255,255,0.14)",
                color: "rgba(255,255,255,0.75)",
                fontSize: 13,
                fontWeight: 600,
                fontFamily: "inherit",
                cursor: "pointer",
                transition: "all 0.12s ease",
              }}
            >
              Back
            </button>
            <button
              onClick={onSubmitSnippetPaste}
              disabled={snippetPasteLoading || !snippetPasteInput.trim()}
              style={{
                flex: 1,
                padding: "10px 14px",
                borderRadius: 12,
                background: snippetPasteLoading || !snippetPasteInput.trim() ? "rgba(53,224,200,0.3)" : "#35E0C8",
                border: "none",
                color: snippetPasteLoading || !snippetPasteInput.trim() ? "rgba(255,255,255,0.4)" : "#04120F",
                fontSize: 13,
                fontWeight: 600,
                fontFamily: "inherit",
                cursor: snippetPasteLoading || !snippetPasteInput.trim() ? "not-allowed" : "pointer",
                transition: "all 0.12s ease",
              }}
            >
              {snippetPasteLoading ? "Scanning…" : "Scan"}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
