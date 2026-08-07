import { act, renderHook } from "@testing-library/react";
import type { ChangeEvent } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useVibecheckFlow } from "./useVibecheckFlow";

function changeEvent(value: string): ChangeEvent<HTMLTextAreaElement> {
  return { target: { value } } as ChangeEvent<HTMLTextAreaElement>;
}

describe("useVibecheckFlow", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });
  afterEach(() => {
    vi.useRealTimers();
  });

  it("starts on the composer screen with every finding pending", () => {
    const { result } = renderHook(() => useVibecheckFlow());
    expect(result.current.state.screen).toBe(0);
    expect(result.current.state.findings).toHaveLength(3);
    expect(result.current.state.findings.every((f) => f.status === "pending")).toBe(true);
  });

  it("toggleAllScope clears then reselects every scope item", () => {
    const { result } = renderHook(() => useVibecheckFlow());
    act(() => result.current.actions.toggleAllScope());
    expect(Object.values(result.current.state.scopeSelected).every((v) => v === false)).toBe(true);
    act(() => result.current.actions.toggleAllScope());
    expect(Object.values(result.current.state.scopeSelected).every((v) => v === true)).toBe(true);
  });

  it("queues, then un-queues, a finding via setFindingStatus", () => {
    const { result } = renderHook(() => useVibecheckFlow());
    const findingId = result.current.state.findings[0].id;
    act(() => result.current.actions.setFindingStatus(findingId, "queued", 0));
    expect(result.current.state.findings.find((f) => f.id === findingId)?.status).toBe("queued");
    act(() => result.current.actions.setFindingStatus(findingId, "pending", 0));
    expect(result.current.state.findings.find((f) => f.id === findingId)?.status).toBe("pending");
  });

  it("does nothing when submitting an empty, unattached composer", () => {
    const { result } = renderHook(() => useVibecheckFlow());
    act(() => result.current.actions.submitComposer());
    expect(result.current.state.screen).toBe(0);
    expect(result.current.state.morphing).toBe(false);
  });

  it("submitComposer with pasted code morphs to the scanning screen and labels the source", () => {
    const { result } = renderHook(() => useVibecheckFlow());
    act(() => result.current.actions.onCodeInput(changeEvent("const x = require('y')")));
    act(() => result.current.actions.submitComposer());
    expect(result.current.state.morphing).toBe(true);
    act(() => {
      vi.advanceTimersByTime(300);
    });
    expect(result.current.state.screen).toBe(1);
    expect(result.current.state.sourceLabel).toBe("pasted JavaScript");
  });

  it("connectGithub simulates a staged connect and then attaches the repo", () => {
    const { result } = renderHook(() => useVibecheckFlow());
    act(() => result.current.actions.connectGithub());
    expect(result.current.state.connecting).toBe(true);
    act(() => {
      vi.advanceTimersByTime(2200);
    });
    expect(result.current.state.connecting).toBe(false);
    expect(result.current.state.attached).toBe(true);
    expect(result.current.state.sourceLabel).toBe("acme-corp/internal-ops");
  });

  it("runs the scan pipeline to completion once on the scanning screen", () => {
    const { result } = renderHook(() => useVibecheckFlow());
    act(() => result.current.actions.pasteExample());
    act(() => result.current.actions.submitComposer());
    act(() => {
      vi.advanceTimersByTime(300);
    });
    expect(result.current.state.screen).toBe(1);
    act(() => {
      vi.advanceTimersByTime(7000);
    });
    expect(result.current.state.pipelineDone).toBe(true);
    expect(result.current.state.pipelineTick).toBe(7);
  });

  it("submitRepoUrl reads the backend origin from VITE_VIBECHECK_API_URL", async () => {
    vi.stubEnv("VITE_VIBECHECK_API_URL", "https://configured-backend.example");
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue({
      ok: true,
      json: async () => ({ status: "rejected", rejection_reason: "not_public_or_not_found" }),
    } as Response);

    const { result } = renderHook(() => useVibecheckFlow());
    act(() => result.current.actions.onRepoUrlInput(({ target: { value: "https://github.com/acme/widgets" } }) as ChangeEvent<HTMLInputElement>));
    await act(async () => {
      await result.current.actions.submitRepoUrl();
    });

    expect(fetchSpy).toHaveBeenCalledWith(
      "https://configured-backend.example/repositories",
      expect.objectContaining({ method: "POST" }),
    );

    fetchSpy.mockRestore();
    vi.unstubAllEnvs();
  });

  it("submitRepoUrl surfaces an error and never calls fetch when VITE_VIBECHECK_API_URL is unset", async () => {
    vi.stubEnv("VITE_VIBECHECK_API_URL", "");
    const fetchSpy = vi.spyOn(globalThis, "fetch");

    const { result } = renderHook(() => useVibecheckFlow());
    act(() => result.current.actions.onRepoUrlInput(({ target: { value: "https://github.com/acme/widgets" } }) as ChangeEvent<HTMLInputElement>));
    await act(async () => {
      await result.current.actions.submitRepoUrl();
    });

    expect(fetchSpy).not.toHaveBeenCalled();
    expect(result.current.state.repoUrlLoading).toBe(false);
    expect(result.current.state.repoUrlError).toBeTruthy();

    fetchSpy.mockRestore();
    vi.unstubAllEnvs();
  });

  it("connectSuggestedRepo reads the backend origin from VITE_VIBECHECK_API_URL", async () => {
    vi.stubEnv("VITE_VIBECHECK_API_URL", "https://configured-backend.example");
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue({
      ok: true,
      json: async () => ({ status: "rejected", rejection_reason: "not_public_or_not_found" }),
    } as Response);

    const { result } = renderHook(() => useVibecheckFlow());
    await act(async () => {
      const pending = result.current.actions.connectSuggestedRepo("https://github.com/acme/widgets");
      await vi.advanceTimersByTimeAsync(60);
      await pending;
    });

    expect(fetchSpy).toHaveBeenCalledWith(
      "https://configured-backend.example/repositories",
      expect.objectContaining({ method: "POST" }),
    );

    fetchSpy.mockRestore();
    vi.unstubAllEnvs();
  });

  it("connectSuggestedRepo surfaces an error and never calls fetch when VITE_VIBECHECK_API_URL is unset", async () => {
    vi.stubEnv("VITE_VIBECHECK_API_URL", "");
    const fetchSpy = vi.spyOn(globalThis, "fetch");

    const { result } = renderHook(() => useVibecheckFlow());
    await act(async () => {
      const pending = result.current.actions.connectSuggestedRepo("https://github.com/acme/widgets");
      await vi.advanceTimersByTimeAsync(60);
      await pending;
    });

    expect(fetchSpy).not.toHaveBeenCalled();
    expect(result.current.state.repoUrlLoading).toBe(false);
    expect(result.current.state.repoUrlError).toBeTruthy();

    fetchSpy.mockRestore();
    vi.unstubAllEnvs();
  });

  it("runPipeline's scan and findings requests route through VITE_VIBECHECK_API_URL, while the GitHub file listing stays on api.github.com", async () => {
    vi.stubEnv("VITE_VIBECHECK_API_URL", "https://configured-backend.example");
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockImplementation((async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url === "https://configured-backend.example/repositories") {
        return { ok: true, json: async () => ({ status: "scan_pending_implementation", id: 42 }) } as Response;
      }
      if (url.startsWith("https://api.github.com/")) {
        return { ok: false, json: async () => [] } as Response;
      }
      if (url === "https://configured-backend.example/repositories/42/scan") {
        return {
          ok: true,
          json: async () => ({
            owner: "acme",
            name: "widgets",
            updated_at: "2026-01-01",
            total_files_stored: 3,
            status: "completed",
          }),
        } as Response;
      }
      if (url === "https://configured-backend.example/repositories/42/findings") {
        return { ok: true, json: async () => ({ findings: [] }) } as Response;
      }
      throw new Error(`unexpected fetch url in test: ${url}`);
    }) as typeof fetch);

    const { result } = renderHook(() => useVibecheckFlow());
    act(() =>
      result.current.actions.onRepoUrlInput(
        ({ target: { value: "https://github.com/acme/widgets" } }) as ChangeEvent<HTMLInputElement>,
      ),
    );
    await act(async () => {
      await result.current.actions.submitRepoUrl();
    });
    expect(result.current.state.repoId).toBe("42");

    act(() => result.current.actions.submitComposer());
    await act(async () => {
      await vi.advanceTimersByTimeAsync(300); // morph onto the scanning screen, kicks off runPipeline
    });
    await act(async () => {
      await vi.advanceTimersByTimeAsync(7100); // pipeline ticks to completion, then fetchScanResults runs
    });

    const calledUrls = fetchSpy.mock.calls.map((call) => String(call[0]));
    expect(calledUrls).toContain("https://configured-backend.example/repositories/42/scan");
    expect(calledUrls).toContain("https://configured-backend.example/repositories/42/findings");
    expect(calledUrls.some((u) => u.startsWith("https://api.github.com/repos/acme/widgets/contents"))).toBe(true);

    fetchSpy.mockRestore();
    vi.unstubAllEnvs();
  });

  it("resetFlow returns to the composer with every finding back to pending", () => {
    const { result } = renderHook(() => useVibecheckFlow());
    act(() => result.current.actions.setFindingStatus(1, "skipped", 0));
    act(() => result.current.actions.resetFlow());
    expect(result.current.state.screen).toBe(0);
    expect(result.current.state.codeInput).toBe("");
    expect(result.current.state.findings.every((f) => f.status === "pending")).toBe(true);
  });
});
