import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { ChangeEvent, UIEvent } from "react";
import { EXAMPLE_CODE, INITIAL_FINDINGS, PIPELINE_TOTAL_TICKS, PLACEHOLDERS, SCOPE_ITEMS } from "../data/fixtures";
import { detectLanguage } from "../utils/detectLanguage";
import type { Finding, FindingStatus, ImplementStep } from "../types";

export interface VibecheckOptions {
  /** Multiplier applied to the simulated scan pipeline's tick duration. */
  scanSpeed?: number;
}

export interface RepositoryFile {
  name: string;
  language?: string;
  isEllipsis?: boolean;
}

export interface VibecheckState {
  screen: number;
  morphing: boolean;
  codeInput: string;
  placeholderIdx: number;
  composerFocused: boolean;
  sourceMenuOpen: boolean;
  scopeMenuOpen: boolean;
  infoOpen: string | null;
  connecting: boolean;
  connectStep: number;
  attached: boolean;
  sourceLabel: string;
  pipelineTick: number;
  pipelineDone: boolean;
  implementSteps: ImplementStep[];
  implementDone: boolean;
  activeFindingIndex: number;
  activeDiffIndex: number;
  stageH: number;
  scopeSelected: Record<string, boolean>;
  findings: Finding[];
  repoUrlInput: string;
  repoUrlLoading: boolean;
  repoUrlError: string | null;
  repoId: string | null;
  attachedFiles: RepositoryFile[];
  suggestedRepoUrl: string | null;
  scanResults: string;
  scanResultsLoading: boolean;
}

const PLACEHOLDER_ROTATE_MS = 3200;
const CONNECT_STEP_MS = 620;
const CONNECT_POLL_MS = 200;
const CONNECT_TOTAL_STEPS = 3;
const IMPLEMENT_STEP_MS = 1400;
const CHANGELOG_DELAY_MS = 1000;
const MORPH_MS = 260;
const PROGRAMMATIC_SCROLL_SETTLE_MS = 550;
const CONNECTED_REPO_LABEL = "acme-corp/internal-ops";

function initialState(): VibecheckState {
  const scopeSelected: Record<string, boolean> = {};
  for (const item of SCOPE_ITEMS) scopeSelected[item.key] = true;
  return {
    screen: 0,
    morphing: false,
    codeInput: "",
    placeholderIdx: 0,
    composerFocused: false,
    sourceMenuOpen: false,
    scopeMenuOpen: false,
    infoOpen: null,
    connecting: false,
    connectStep: 0,
    attached: false,
    sourceLabel: "",
    pipelineTick: 0,
    pipelineDone: false,
    implementSteps: [],
    implementDone: false,
    activeFindingIndex: 0,
    activeDiffIndex: 0,
    stageH: 480,
    scopeSelected,
    findings: INITIAL_FINDINGS.map((f) => ({ ...f })),
    repoUrlInput: "",
    repoUrlLoading: false,
    repoUrlError: null,
    repoId: null,
    attachedFiles: [],
    suggestedRepoUrl: null,
    scanResults: "",
    scanResultsLoading: false,
  };
}

type Patch = Partial<VibecheckState> | ((s: VibecheckState) => Partial<VibecheckState>);

/**
 * Drives the Vibecheck demo's screen-by-screen state machine: composer,
 * simulated scan, findings review, simulated fix pass, diff, done.
 *
 * This is a UI-only simulation — nothing here calls VibeGuard's real
 * scan/remediation API. See frontend/README.md.
 */
export function useVibecheckFlow(options: VibecheckOptions = {}) {
  const scanSpeed = options.scanSpeed ?? 1;
  const [state, setState] = useState<VibecheckState>(initialState);

  // Mirrors `state` after every commit so timer/event callbacks (created
  // once via useCallback) can read the latest values without stale
  // closures or re-subscribing on every state change. Updated in an
  // effect, not during render, per the rules of React refs.
  const stateRef = useRef(state);
  useEffect(() => {
    stateRef.current = state;
  });

  const patch = useCallback((update: Patch) => {
    setState((prev) => ({ ...prev, ...(typeof update === "function" ? update(prev) : update) }));
  }, []);

  const runtime = useRef({
    mainEl: null as HTMLElement | null,
    stageEl: null as HTMLElement | null,
    scrollEl: null as HTMLElement | null,
    diffScrollEl: null as HTMLElement | null,
    inputEl: null as HTMLTextAreaElement | null,
    stageObserver: null as ResizeObserver | null,
    programmaticScroll: false,
    placeholderTimer: undefined as ReturnType<typeof setInterval> | undefined,
    connectTimer: undefined as ReturnType<typeof setInterval> | undefined,
    morphTimer: undefined as ReturnType<typeof setTimeout> | undefined,
    pipelineTimer: undefined as ReturnType<typeof setInterval> | undefined,
    pipelineEndTimer: undefined as ReturnType<typeof setTimeout> | undefined,
    implementTimer: undefined as ReturnType<typeof setInterval> | undefined,
    implementEndTimer: undefined as ReturnType<typeof setTimeout> | undefined,
    changelogTimer: undefined as ReturnType<typeof setTimeout> | undefined,
    progScrollTimer: undefined as ReturnType<typeof setTimeout> | undefined,
  });

  const clearTimers = useCallback(() => {
    const r = runtime.current;
    clearInterval(r.pipelineTimer);
    clearInterval(r.implementTimer);
    clearTimeout(r.pipelineEndTimer);
    clearTimeout(r.implementEndTimer);
    clearTimeout(r.changelogTimer);
  }, []);

  const measure = useCallback(() => {
    const r = runtime.current;
    if (!r.mainEl) return;
    const h = r.mainEl.clientHeight;
    if (!h) return;
    const stageH = Math.max(260, Math.min(640, h - 104));
    patch((prev) => (prev.stageH === stageH ? {} : { stageH }));
  }, [patch]);

  const setMainRef = useCallback(
    (el: HTMLElement | null) => {
      runtime.current.mainEl = el;
      if (el) requestAnimationFrame(measure);
    },
    [measure],
  );

  const setStageRef = useCallback((el: HTMLElement | null) => {
    const r = runtime.current;
    if (r.stageObserver) {
      r.stageObserver.disconnect();
      r.stageObserver = null;
    }
    r.stageEl = el;
    if (!el || typeof ResizeObserver === "undefined") return;
    r.stageObserver = new ResizeObserver(() => {
      const h = Math.round(el.clientHeight);
      if (h > 80 && h !== stateRef.current.stageH) patch({ stageH: h });
    });
    r.stageObserver.observe(el);
  }, [patch]);

  const setInputRef = useCallback((el: HTMLTextAreaElement | null) => {
    runtime.current.inputEl = el;
  }, []);
  const setScrollRef = useCallback((el: HTMLElement | null) => {
    runtime.current.scrollEl = el;
  }, []);
  const setDiffScrollRef = useCallback((el: HTMLElement | null) => {
    runtime.current.diffScrollEl = el;
  }, []);

  // morphTo, runPipeline, and runImplement refer to each other (morphTo
  // kicks off whichever run* matches the target screen; runImplement's
  // completion morphs to the next screen). Rather than have their
  // useCallback bodies reference each other's `const` bindings directly
  // -- a real cycle that also defeats dependency-array analysis -- each
  // one is looked up through this ref, refreshed after every render.
  const latest = useRef<{
    runPipeline: () => void;
    runImplement: () => void;
    morphTo: (screen: number, extra?: Partial<VibecheckState>) => void;
  }>({ runPipeline: () => {}, runImplement: () => {}, morphTo: () => {} });

  const morphTo = useCallback(
    (screen: number, extra?: Partial<VibecheckState>) => {
      const r = runtime.current;
      clearTimeout(r.morphTimer);
      patch({ morphing: true });
      r.morphTimer = setTimeout(() => {
        patch({ ...(extra || {}), screen, morphing: false });
        if (screen === 1) latest.current.runPipeline();
        if (screen === 3) latest.current.runImplement();
      }, MORPH_MS);
    },
    [patch],
  );

  const runPipeline = useCallback(() => {
    const r = runtime.current;
    clearInterval(r.pipelineTimer);
    clearTimeout(r.pipelineEndTimer);
    const step = Math.max(150, 620 / scanSpeed);
    const start = Date.now() - stateRef.current.pipelineTick * step;

    const fetchScanResults = async () => {
      const repoId = stateRef.current.repoId;
      if (!repoId) return;

      const apiUrl = import.meta.env.VITE_VIBECHECK_API_URL || "http://localhost:8000";

      try {
        patch({ scanResultsLoading: true });
        // POST /repositories/{id}/scan blocks until the real scan (heuristics
        // + LLM confirmation) finishes, then returns the repository record --
        // it does NOT return findings text. Findings are a separate call.
        const scanResponse = await fetch(`${apiUrl}/repositories/${repoId}/scan`, { method: "POST" });

        if (!scanResponse.ok) {
          const errorBody = await scanResponse.text();
          patch({ scanResults: `Scan request failed (${scanResponse.status}): ${errorBody}` });
          return;
        }

        const repo = await scanResponse.json();

        // scan_failed means every LLM-requiring confirmation call errored --
        // it does NOT mean zero findings. Heuristic-only findings (e.g. the
        // dependency-manifest check) never touch the LLM and can still be
        // sitting in the DB, so findings are always fetched regardless of
        // status; scan_failed is surfaced as a note in the report instead
        // of a hard stop.
        const findingsResponse = await fetch(`${apiUrl}/repositories/${repoId}/findings`);
        if (!findingsResponse.ok) {
          const errorBody = await findingsResponse.text();
          patch({ scanResults: `Findings request failed (${findingsResponse.status}): ${errorBody}` });
          return;
        }

        const { findings } = await findingsResponse.json();

        const counts = { critical: 0, high: 0, medium: 0, low: 0, info: 0 };
        for (const f of findings) {
          if (f.severity in counts) counts[f.severity as keyof typeof counts] += 1;
        }

        const lines: string[] = [];
        lines.push("[SECURITY ANALYSIS REPORT]");
        lines.push("==========================");
        lines.push("");
        lines.push(`Repository: ${repo.owner}/${repo.name}`);
        lines.push(`Scan Date: ${repo.updated_at}`);
        lines.push(`Files Scanned: ${repo.total_files_stored}`);
        if (repo.scan_incomplete) {
          lines.push(`Scan Incomplete: ${repo.scan_incomplete_reason ?? "unknown reason"}`);
        }
        if (repo.status === "scan_failed") {
          lines.push(`Note: every LLM confirmation call failed (reason: ${repo.scan_failure_reason ?? "unknown"}) -- only heuristic-only findings below could be confirmed.`);
        }
        lines.push("");
        lines.push("[FINDINGS]");
        lines.push("==========");
        lines.push("");

        if (findings.length === 0) {
          lines.push("No findings.");
        } else {
          findings.forEach((f: Record<string, unknown>, i: number) => {
            lines.push(`${i + 1}. ${f.title}`);
            lines.push(`   Location: ${f.relative_path}${f.line_number ? `:${f.line_number}` : ""}`);
            lines.push(`   Category: ${f.category}`);
            lines.push(`   Severity: ${f.severity}`);
            lines.push(`   Description: ${f.description}`);
            lines.push(`   Remediation: ${f.remediation}`);
            lines.push("");
          });
        }

        lines.push("[SUMMARY]");
        lines.push("=========");
        lines.push(`Total Issues Found: ${findings.length}`);
        lines.push(`- Critical: ${counts.critical}`);
        lines.push(`- High: ${counts.high}`);
        lines.push(`- Medium: ${counts.medium}`);
        lines.push(`- Low: ${counts.low}`);
        lines.push(`- Info: ${counts.info}`);

        patch({ scanResults: lines.join("\n") });
      } catch (err) {
        patch({ scanResults: `Error fetching scan results: ${err instanceof Error ? err.message : "Unknown error"}` });
      } finally {
        patch({ scanResultsLoading: false });
      }
    };

    const advance = () => {
      const tick = Math.min(PIPELINE_TOTAL_TICKS, Math.floor((Date.now() - start) / step));
      const done = tick >= PIPELINE_TOTAL_TICKS;
      if (done) {
        clearInterval(r.pipelineTimer);
        clearTimeout(r.pipelineEndTimer);
        fetchScanResults();
      }
      patch({ pipelineTick: tick, pipelineDone: done });
    };
    r.pipelineTimer = setInterval(advance, step);
    r.pipelineEndTimer = setTimeout(advance, PIPELINE_TOTAL_TICKS * step + 60);
  }, [patch, scanSpeed]);

  const runImplement = useCallback(() => {
    const r = runtime.current;
    clearInterval(r.implementTimer);
    clearTimeout(r.implementEndTimer);
    const start = Date.now();
    const total = stateRef.current.implementSteps.length;
    const advance = () => {
      const doneCount = Math.min(total, Math.floor((Date.now() - start) / IMPLEMENT_STEP_MS) + 1);
      const steps = stateRef.current.implementSteps.map((step, i) => ({
        ...step,
        status: i < doneCount ? ("done" as const) : i === doneCount ? ("running" as const) : ("pending" as const),
      }));
      const allDone = doneCount >= total;
      if (allDone) {
        clearInterval(r.implementTimer);
        clearTimeout(r.implementEndTimer);
        clearTimeout(r.changelogTimer);
        r.changelogTimer = setTimeout(() => latest.current.morphTo(4), CHANGELOG_DELAY_MS);
      }
      patch({ implementSteps: steps, implementDone: allDone });
    };
    r.implementTimer = setInterval(advance, IMPLEMENT_STEP_MS);
    r.implementEndTimer = setTimeout(advance, total * IMPLEMENT_STEP_MS + 60);
  }, [patch]);

  useEffect(() => {
    latest.current = { runPipeline, runImplement, morphTo };
  });

  useEffect(() => {
    const r = runtime.current;
    measure();
    window.addEventListener("resize", measure);
    r.placeholderTimer = setInterval(() => {
      patch((prev) => ({ placeholderIdx: (prev.placeholderIdx + 1) % PLACEHOLDERS.length }));
    }, PLACEHOLDER_ROTATE_MS);
    return () => {
      if (r.stageObserver) r.stageObserver.disconnect();
      clearTimers();
      clearInterval(r.placeholderTimer);
      clearInterval(r.connectTimer);
      clearTimeout(r.morphTimer);
      clearTimeout(r.progScrollTimer);
      window.removeEventListener("resize", measure);
    };
  }, [clearTimers, measure, patch]);

  const onCodeInput = useCallback((e: ChangeEvent<HTMLTextAreaElement>) => {
    const value = e.target.value;
    patch({ codeInput: value });

    const githubUrlRegex = /https?:\/\/github\.com\/([a-zA-Z0-9_-]+)\/([a-zA-Z0-9_.-]+)/;
    const match = value.match(githubUrlRegex);

    if (match) {
      const repoUrl = match[0];
      patch({ suggestedRepoUrl: repoUrl });
    } else {
      patch({ suggestedRepoUrl: null });
    }
  }, [patch]);
  const onRepoUrlInput = useCallback((e: ChangeEvent<HTMLInputElement>) => {
    patch({ repoUrlInput: e.target.value });
  }, [patch]);
  const clearRepoUrlError = useCallback(() => patch({ repoUrlError: null }), [patch]);
  const disconnectRepo = useCallback(() => {
    patch({
      attached: false,
      sourceLabel: "",
      attachedFiles: [],
      repoId: null,
    });
  }, [patch]);

  const connectSuggestedRepo = useCallback(async (repoUrl: string) => {
    patch({ repoUrlInput: repoUrl, suggestedRepoUrl: null });

    await new Promise((resolve) => setTimeout(resolve, 50));

    patch({ repoUrlLoading: true, repoUrlError: null });

    try {
      const response = await fetch("http://localhost:8000/repositories", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ repo_url: repoUrl }),
      });

      const data = await response.json();

      if (data.status === "scan_pending_implementation") {
        let files: RepositoryFile[] = [];
        try {
          const urlParts = repoUrl.replace("https://github.com/", "").split("/");
          if (urlParts.length >= 2) {
            const owner = urlParts[0];
            const repo = urlParts[1];
            const filesResponse = await fetch(`https://api.github.com/repos/${owner}/${repo}/contents`, {
              headers: { "Accept": "application/vnd.github.v3+json" },
            });

            if (filesResponse.ok) {
              const filesList = await filesResponse.json();
              if (Array.isArray(filesList)) {
                const skipExtensions = [".md", ".txt", ".json", ".yml", ".yaml"];
                const skipFiles = [".gitignore", ".env.example"];
                const fileObjects = filesList.filter((f) => {
                  if (f.type !== "file") return false;
                  const name = f.name.toLowerCase();
                  if (skipFiles.some((sf) => name === sf || name.startsWith(".env"))) return false;
                  if (skipExtensions.some((ext) => name.endsWith(ext))) return false;
                  return true;
                });
                const hasMore = fileObjects.length > 5;

                const languageMap: Record<string, string> = {
                  js: "JavaScript",
                  ts: "TypeScript",
                  jsx: "JSX",
                  tsx: "TSX",
                  py: "Python",
                  rb: "Ruby",
                  go: "Go",
                  rs: "Rust",
                  java: "Java",
                  cs: "C#",
                  cpp: "C++",
                  c: "C",
                  html: "HTML",
                  css: "CSS",
                  json: "JSON",
                  yaml: "YAML",
                  yml: "YAML",
                  md: "Markdown",
                };

                files = fileObjects
                  .slice(0, 5)
                  .map((f) => {
                    const ext = f.name.split(".").pop() || "";
                    return {
                      name: f.name,
                      language: languageMap[ext] || ext.toUpperCase() || "File",
                    };
                  });

                if (hasMore) {
                  files.push({ name: "...", isEllipsis: true });
                }
              }
            }
          }
        } catch (err) {
          // Silently fail on file fetch
        }

        patch({
          repoUrlLoading: false,
          repoId: String(data.id),
          sourceLabel: repoUrl,
          attached: true,
          attachedFiles: files,
          repoUrlInput: "",
          sourceMenuOpen: false,
          codeInput: "",
        });
        runtime.current.inputEl?.focus();
      } else if (data.status === "rejected") {
        const friendlyErrors: Record<string, string> = {
          not_public_or_not_found: "Repository not found or not public",
          repo_too_large: "Repository is too large to scan",
          clone_failed: "Failed to clone repository",
          clone_timeout: "Repository clone timed out",
        };
        const errorMsg = friendlyErrors[data.rejection_reason] || data.rejection_reason || "Failed to connect repository";
        patch({ repoUrlLoading: false, repoUrlError: errorMsg });
      }
    } catch (err) {
      patch({ repoUrlLoading: false, repoUrlError: "Failed to connect to server" });
    }
  }, [patch]);
  const onComposerFocus = useCallback(() => patch({ composerFocused: true }), [patch]);
  const onComposerBlur = useCallback(() => patch({ composerFocused: false }), [patch]);
  const toggleSourceMenu = useCallback(
    () => patch((s) => ({ sourceMenuOpen: !s.sourceMenuOpen, scopeMenuOpen: false })),
    [patch],
  );
  const toggleScopeMenu = useCallback(
    () => patch((s) => ({ scopeMenuOpen: !s.scopeMenuOpen, sourceMenuOpen: false })),
    [patch],
  );
  const closeScopeMenu = useCallback(() => patch({ scopeMenuOpen: false }), [patch]);
  const toggleScope = useCallback(
    (key: string) => patch((s) => ({ scopeSelected: { ...s.scopeSelected, [key]: !s.scopeSelected[key] } })),
    [patch],
  );
  const toggleAllScope = useCallback(() => {
    const allOn = SCOPE_ITEMS.every((item) => stateRef.current.scopeSelected[item.key] !== false);
    const next: Record<string, boolean> = {};
    for (const item of SCOPE_ITEMS) next[item.key] = !allOn;
    patch({ scopeSelected: next });
  }, [patch]);
  const setInfo = useCallback((key: string | null) => patch({ infoOpen: key }), [patch]);

  const connectGithub = useCallback(() => {
    const r = runtime.current;
    clearInterval(r.connectTimer);
    patch({ sourceMenuOpen: false, connecting: true, connectStep: 0, sourceLabel: CONNECTED_REPO_LABEL });
    const start = Date.now();
    r.connectTimer = setInterval(() => {
      const step = Math.floor((Date.now() - start) / CONNECT_STEP_MS);
      if (step >= CONNECT_TOTAL_STEPS) {
        clearInterval(r.connectTimer);
        patch({ connecting: false, connectStep: CONNECT_TOTAL_STEPS, attached: true });
        r.inputEl?.focus();
        return;
      }
      patch({ connectStep: step });
    }, CONNECT_POLL_MS);
  }, [patch]);

  const submitRepoUrl = useCallback(async () => {
    const url = stateRef.current.repoUrlInput.trim();
    if (!url) return;

    patch({ repoUrlLoading: true, repoUrlError: null });

    try {
      const response = await fetch("http://localhost:8000/repositories", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ repo_url: url }),
      });

      const data = await response.json();

      if (data.status === "scan_pending_implementation") {
        let files: RepositoryFile[] = [];
        try {
          const urlParts = url.replace("https://github.com/", "").split("/");
          if (urlParts.length >= 2) {
            const owner = urlParts[0];
            const repo = urlParts[1];
            const filesResponse = await fetch(`https://api.github.com/repos/${owner}/${repo}/contents`, {
              headers: { "Accept": "application/vnd.github.v3+json" },
            });

            if (filesResponse.ok) {
              const filesList = await filesResponse.json();
              if (Array.isArray(filesList)) {
                const skipExtensions = [".md", ".txt", ".json", ".yml", ".yaml"];
                const skipFiles = [".gitignore", ".env.example"];
                const fileObjects = filesList.filter((f) => {
                  if (f.type !== "file") return false;
                  const name = f.name.toLowerCase();
                  if (skipFiles.some((sf) => name === sf || name.startsWith(".env"))) return false;
                  if (skipExtensions.some((ext) => name.endsWith(ext))) return false;
                  return true;
                });
                const hasMore = fileObjects.length > 5;

                const languageMap: Record<string, string> = {
                  js: "JavaScript",
                  ts: "TypeScript",
                  jsx: "JSX",
                  tsx: "TSX",
                  py: "Python",
                  rb: "Ruby",
                  go: "Go",
                  rs: "Rust",
                  java: "Java",
                  cs: "C#",
                  cpp: "C++",
                  c: "C",
                  html: "HTML",
                  css: "CSS",
                  json: "JSON",
                  yaml: "YAML",
                  yml: "YAML",
                  md: "Markdown",
                };

                files = fileObjects
                  .slice(0, 5)
                  .map((f) => {
                    const ext = f.name.split(".").pop() || "";
                    return {
                      name: f.name,
                      language: languageMap[ext] || ext.toUpperCase() || "File",
                    };
                  });

                if (hasMore) {
                  files.push({ name: "...", isEllipsis: true });
                }
              }
            }
          }
        } catch (err) {
          // Silently fail on file fetch
        }

        patch({
          repoUrlLoading: false,
          repoId: String(data.id),
          sourceLabel: url,
          attached: true,
          attachedFiles: files,
          repoUrlInput: "",
          sourceMenuOpen: false,
        });
        runtime.current.inputEl?.focus();
      } else if (data.status === "rejected") {
        const friendlyErrors: Record<string, string> = {
          not_public_or_not_found: "Repository not found or not public",
          repo_too_large: "Repository is too large to scan",
          clone_failed: "Failed to clone repository",
          clone_timeout: "Repository clone timed out",
        };
        const errorMsg = friendlyErrors[data.rejection_reason] || data.rejection_reason || "Failed to connect repository";
        patch({ repoUrlLoading: false, repoUrlError: errorMsg });
      }
    } catch (err) {
      patch({ repoUrlLoading: false, repoUrlError: "Failed to connect to server" });
    }
  }, [patch]);

  const pasteExample = useCallback(() => {
    patch({ sourceMenuOpen: false, codeInput: EXAMPLE_CODE });
    runtime.current.inputEl?.focus();
  }, [patch]);

  const submitComposer = useCallback(() => {
    const s = stateRef.current;
    if (!s.codeInput.trim() && !s.attached) return;
    const label = s.attached ? s.sourceLabel : `pasted ${detectLanguage(s.codeInput)}`;
    morphTo(1, {
      sourceLabel: label,
      scopeMenuOpen: false,
      sourceMenuOpen: false,
      pipelineTick: 0,
      pipelineDone: false,
    });
  }, [morphTo]);

  const goToFindings = useCallback(() => morphTo(2, { activeFindingIndex: 0 }), [morphTo]);

  const scrollStack = useCallback(
    (el: HTMLElement | null, index: number, key: "activeFindingIndex" | "activeDiffIndex") => {
      const r = runtime.current;
      patch({ [key]: index } as Partial<VibecheckState>);
      if (el) {
        r.programmaticScroll = true;
        el.scrollTo({ top: index * stateRef.current.stageH, behavior: "smooth" });
        clearTimeout(r.progScrollTimer);
        r.progScrollTimer = setTimeout(() => {
          r.programmaticScroll = false;
        }, PROGRAMMATIC_SCROLL_SETTLE_MS);
      }
    },
    [patch],
  );

  const handleFindingScroll = useCallback((e: UIEvent<HTMLElement>) => {
    if (runtime.current.programmaticScroll) return;
    const s = stateRef.current;
    const n = s.findings.length;
    if (n <= 1) return;
    const idx = Math.max(0, Math.min(n - 1, Math.round(e.currentTarget.scrollTop / s.stageH)));
    if (idx !== s.activeFindingIndex) patch({ activeFindingIndex: idx });
  }, [patch]);

  const handleDiffScroll = useCallback((e: UIEvent<HTMLElement>) => {
    if (runtime.current.programmaticScroll) return;
    const s = stateRef.current;
    const n = s.findings.filter((f) => f.status === "queued").length;
    if (n <= 1) return;
    const idx = Math.max(0, Math.min(n - 1, Math.round(e.currentTarget.scrollTop / s.stageH)));
    if (idx !== s.activeDiffIndex) patch({ activeDiffIndex: idx });
  }, [patch]);

  const setFindingStatus = useCallback(
    (id: number, status: FindingStatus, index: number) => {
      patch((prev) => ({ findings: prev.findings.map((f) => (f.id === id ? { ...f, status } : f)) }));
      const n = stateRef.current.findings.length;
      if (index + 1 < n) {
        setTimeout(() => scrollStack(runtime.current.scrollEl, index + 1, "activeFindingIndex"), 200);
      }
    },
    [patch, scrollStack],
  );

  const approveFixes = useCallback(() => {
    const queued = stateRef.current.findings.filter((f) => f.status === "queued");
    if (queued.length === 0) return;
    clearTimers();
    const steps: ImplementStep[] = [
      ...queued.map((f) => ({ status: "pending" as const, kind: "fix" as const, findingId: f.id })),
      { status: "pending" as const, kind: "validate" as const },
    ];
    steps[0] = { ...steps[0], status: "running" };
    morphTo(3, { implementDone: false, implementSteps: steps, activeDiffIndex: 0 });
  }, [clearTimers, morphTo]);

  const openPR = useCallback(() => morphTo(5), [morphTo]);

  const resetFlow = useCallback(() => {
    clearTimers();
    patch((prev) => ({
      screen: 0,
      codeInput: "",
      sourceLabel: "",
      attached: false,
      connecting: false,
      connectStep: 0,
      pipelineTick: 0,
      pipelineDone: false,
      implementDone: false,
      implementSteps: [],
      activeFindingIndex: 0,
      activeDiffIndex: 0,
      findings: prev.findings.map((f) => ({ ...f, status: "pending" as const })),
      repoUrlInput: "",
      repoUrlLoading: false,
      repoUrlError: null,
      repoId: null,
      attachedFiles: [],
      suggestedRepoUrl: null,
      scanResults: "",
      scanResultsLoading: false,
    }));
  }, [clearTimers, patch]);

  const scrollToFinding = useCallback(
    (index: number) => scrollStack(runtime.current.scrollEl, index, "activeFindingIndex"),
    [scrollStack],
  );
  const scrollToDiff = useCallback(
    (index: number) => scrollStack(runtime.current.diffScrollEl, index, "activeDiffIndex"),
    [scrollStack],
  );

  const actions = useMemo(
    () => ({
      onCodeInput,
      onRepoUrlInput,
      clearRepoUrlError,
      disconnectRepo,
      connectSuggestedRepo,
      onComposerFocus,
      onComposerBlur,
      toggleSourceMenu,
      toggleScopeMenu,
      closeScopeMenu,
      toggleScope,
      toggleAllScope,
      setInfo,
      connectGithub,
      submitRepoUrl,
      pasteExample,
      submitComposer,
      goToFindings,
      handleFindingScroll,
      handleDiffScroll,
      setFindingStatus,
      approveFixes,
      openPR,
      resetFlow,
      scrollToFinding,
      scrollToDiff,
      setMainRef,
      setStageRef,
      setInputRef,
      setScrollRef,
      setDiffScrollRef,
    }),
    [
      onCodeInput,
      onRepoUrlInput,
      clearRepoUrlError,
      disconnectRepo,
      connectSuggestedRepo,
      onComposerFocus,
      onComposerBlur,
      toggleSourceMenu,
      toggleScopeMenu,
      closeScopeMenu,
      toggleScope,
      toggleAllScope,
      setInfo,
      connectGithub,
      submitRepoUrl,
      pasteExample,
      submitComposer,
      goToFindings,
      handleFindingScroll,
      handleDiffScroll,
      setFindingStatus,
      approveFixes,
      openPR,
      resetFlow,
      scrollToFinding,
      scrollToDiff,
      setMainRef,
      setStageRef,
      setInputRef,
      setScrollRef,
      setDiffScrollRef,
    ],
  );

  return { state, actions };
}
