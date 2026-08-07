import { act, renderHook } from "@testing-library/react";
import type { ChangeEvent } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useVibecheckFlow } from "./useVibecheckFlow";

/**
 * The GitHub-free snippet-scan path (.claude/pipeline/20260807-snippet-remediation-no-github):
 * submitSnippetPaste (POST /snippets -> POST /snippets/{id}/scan -> GET
 * /snippets/{id}/findings), resetSnippetFlow, and this state's isolation
 * from the repo-scoped repoId/realFindings/codeInput fields.
 */

const API_BASE = "https://configured-backend.example";

function pasteChangeEvent(value: string): ChangeEvent<HTMLTextAreaElement> {
  return { target: { value } } as ChangeEvent<HTMLTextAreaElement>;
}

describe("useVibecheckFlow snippet-scan path", () => {
  beforeEach(() => {
    vi.stubEnv("VITE_VIBECHECK_API_URL", API_BASE);
  });

  afterEach(() => {
    vi.unstubAllEnvs();
    vi.restoreAllMocks();
  });

  it("does nothing when submitting empty/whitespace-only paste input", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch");
    const { result } = renderHook(() => useVibecheckFlow());

    act(() => result.current.actions.onSnippetPasteInput(pasteChangeEvent("   ")));
    await act(async () => {
      await result.current.actions.submitSnippetPaste();
    });

    expect(fetchSpy).not.toHaveBeenCalled();
    expect(result.current.state.screen).toBe(0);
  });

  it("submits pasted code, scans it, fetches findings, and jumps to the findings screen with zero GitHub calls", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockImplementation((async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url === `${API_BASE}/snippets`) {
        return { ok: true, json: async () => ({ id: 5, status: "scan_pending", rejection_reason: null }) } as Response;
      }
      if (url === `${API_BASE}/snippets/5/scan`) {
        return { ok: true, json: async () => ({ status: "scanned", scan_incomplete: false }) } as Response;
      }
      if (url === `${API_BASE}/snippets/5/findings`) {
        return { ok: true, json: async () => ({ findings: [{ id: 1, severity: "high", title: "t" }] }) } as Response;
      }
      throw new Error(`unexpected fetch url in test: ${url}`);
    }) as typeof fetch);

    const { result } = renderHook(() => useVibecheckFlow());
    act(() => result.current.actions.onSnippetPasteInput(pasteChangeEvent("password = 'admin'")));
    await act(async () => {
      await result.current.actions.submitSnippetPaste();
    });

    expect(result.current.state.snippetId).toBe("5");
    expect(result.current.state.snippetContent).toBe("password = 'admin'");
    expect(result.current.state.snippetFindings).toEqual([{ id: 1, severity: "high", title: "t" }]);
    expect(result.current.state.screen).toBe(2);
    expect(result.current.state.snippetPasteLoading).toBe(false);
    expect(result.current.state.snippetPasteError).toBeNull();
    // The paste input is cleared for the next scan, ready to reuse.
    expect(result.current.state.snippetPasteInput).toBe("");

    const calledUrls = fetchSpy.mock.calls.map((call) => String(call[0]));
    expect(calledUrls.some((u) => u.includes("github.com"))).toBe(false);

    // Fully isolated from the repository-scan path.
    expect(result.current.state.repoId).toBeNull();
    expect(result.current.state.realFindings).toEqual([]);
  });

  it("surfaces a friendly error and does not advance the screen when the snippet is rejected as empty", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue({
      ok: true,
      json: async () => ({ id: 6, status: "rejected", rejection_reason: "empty_content" }),
    } as Response);

    const { result } = renderHook(() => useVibecheckFlow());
    act(() => result.current.actions.onSnippetPasteInput(pasteChangeEvent("x")));
    await act(async () => {
      await result.current.actions.submitSnippetPaste();
    });

    expect(result.current.state.screen).toBe(0);
    expect(result.current.state.snippetPasteLoading).toBe(false);
    expect(result.current.state.snippetPasteError).toMatch(/empty/i);
    expect(result.current.state.snippetId).toBeNull();
  });

  it("surfaces an error when the scan request fails after a successful submit", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation((async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url === `${API_BASE}/snippets`) {
        return { ok: true, json: async () => ({ id: 7, status: "scan_pending", rejection_reason: null }) } as Response;
      }
      if (url === `${API_BASE}/snippets/7/scan`) {
        return { ok: false, status: 500 } as Response;
      }
      throw new Error(`unexpected fetch url in test: ${url}`);
    }) as typeof fetch);

    const { result } = renderHook(() => useVibecheckFlow());
    act(() => result.current.actions.onSnippetPasteInput(pasteChangeEvent("x = 1")));
    await act(async () => {
      await result.current.actions.submitSnippetPaste();
    });

    expect(result.current.state.screen).toBe(0);
    expect(result.current.state.snippetPasteError).toMatch(/scan failed/i);
  });

  it("clearSnippetPasteError clears a prior error", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue({
      ok: true,
      json: async () => ({ id: 8, status: "rejected", rejection_reason: "too_large" }),
    } as Response);

    const { result } = renderHook(() => useVibecheckFlow());
    act(() => result.current.actions.onSnippetPasteInput(pasteChangeEvent("x")));
    await act(async () => {
      await result.current.actions.submitSnippetPaste();
    });
    expect(result.current.state.snippetPasteError).toBeTruthy();

    act(() => result.current.actions.clearSnippetPasteError());
    expect(result.current.state.snippetPasteError).toBeNull();
  });

  it("resetSnippetFlow returns to the composer and clears every snippet-scoped field, leaving repo state untouched", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation((async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url === `${API_BASE}/snippets`) {
        return { ok: true, json: async () => ({ id: 9, status: "scan_pending", rejection_reason: null }) } as Response;
      }
      if (url === `${API_BASE}/snippets/9/scan`) {
        return { ok: true, json: async () => ({ status: "scanned", scan_incomplete: false }) } as Response;
      }
      if (url === `${API_BASE}/snippets/9/findings`) {
        return { ok: true, json: async () => ({ findings: [{ id: 1, severity: "low" }] }) } as Response;
      }
      throw new Error(`unexpected fetch url in test: ${url}`);
    }) as typeof fetch);

    const { result } = renderHook(() => useVibecheckFlow());
    act(() => result.current.actions.onSnippetPasteInput(pasteChangeEvent("y = 2")));
    await act(async () => {
      await result.current.actions.submitSnippetPaste();
    });
    expect(result.current.state.snippetId).toBe("9");

    act(() => result.current.actions.resetSnippetFlow());

    expect(result.current.state.screen).toBe(0);
    expect(result.current.state.snippetId).toBeNull();
    expect(result.current.state.snippetContent).toBe("");
    expect(result.current.state.snippetFindings).toEqual([]);
    expect(result.current.state.snippetPasteInput).toBe("");
    expect(result.current.state.snippetPasteError).toBeNull();
  });

  it("submitSnippetPaste never touches repoId/realFindings/codeInput, keeping the two flows' state fully separate", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation((async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url === `${API_BASE}/snippets`) {
        return { ok: true, json: async () => ({ id: 11, status: "scan_pending", rejection_reason: null }) } as Response;
      }
      if (url === `${API_BASE}/snippets/11/scan`) {
        return { ok: true, json: async () => ({ status: "scanned", scan_incomplete: false }) } as Response;
      }
      if (url === `${API_BASE}/snippets/11/findings`) {
        return { ok: true, json: async () => ({ findings: [] }) } as Response;
      }
      throw new Error(`unexpected fetch url in test: ${url}`);
    }) as typeof fetch);

    const { result } = renderHook(() => useVibecheckFlow());
    act(() => result.current.actions.onCodeInput(pasteChangeEvent("const x = 1") as unknown as ChangeEvent<HTMLTextAreaElement>));
    act(() => result.current.actions.onSnippetPasteInput(pasteChangeEvent("import os")));
    await act(async () => {
      await result.current.actions.submitSnippetPaste();
    });

    // codeInput (the fixture-demo/repo composer field) is untouched by the snippet path.
    expect(result.current.state.codeInput).toBe("const x = 1");
    expect(result.current.state.repoId).toBeNull();
    expect(result.current.state.realFindings).toEqual([]);
    expect(result.current.state.snippetId).toBe("11");
  });
});
