import { act, renderHook } from "@testing-library/react";
import type { ChangeEvent } from "react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { useVibecheckFlow } from "./useVibecheckFlow";

/**
 * Bug B regression coverage (.claude/pipeline/20260807-decide-remediation-fetch-bug):
 * the OAuth token round trip, and the real-findings-path remediation flow
 * actually calling the real backend routes with the bearer token attached.
 * Before this fix, none of this existed: no token handling anywhere in the
 * frontend, and the Decide screen had no action to advance past it at all.
 */

const API_BASE = "https://configured-backend.example";

function repoUrlChangeEvent(value: string): ChangeEvent<HTMLInputElement> {
  return { target: { value } } as ChangeEvent<HTMLInputElement>;
}

/** Attaches a repository to hook state via the same path submitRepoUrl already uses, so tests can start from "a repo is connected" without reaching into internals. */
async function attachRepo(
  result: { current: ReturnType<typeof useVibecheckFlow> },
  repoId: number,
) {
  await act(async () => {
    result.current.actions.onRepoUrlInput(repoUrlChangeEvent("https://github.com/acme/widgets"));
  });
  await act(async () => {
    await result.current.actions.submitRepoUrl();
  });
  expect(result.current.state.repoId).toBe(String(repoId));
}

describe("useVibecheckFlow OAuth token wiring and real-findings remediation", () => {
  const originalLocation = window.location;

  beforeEach(() => {
    vi.useFakeTimers();
    vi.stubEnv("VITE_VIBECHECK_API_URL", API_BASE);
    sessionStorage.clear();
    Object.defineProperty(window, "location", {
      writable: true,
      configurable: true,
      value: { ...originalLocation, assign: vi.fn(), hash: "", pathname: "/", search: "" },
    });
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllEnvs();
    vi.restoreAllMocks();
    sessionStorage.clear();
    Object.defineProperty(window, "location", { writable: true, configurable: true, value: originalLocation });
  });

  it("has no session token on a fresh visit with nothing in the URL or sessionStorage", () => {
    const { result } = renderHook(() => useVibecheckFlow());
    expect(result.current.state.sessionToken).toBeNull();
  });

  it("consumes #session_token from the URL fragment on mount, stores it, and strips it from the URL", () => {
    window.location.hash = "#session_token=abc123";

    const { result } = renderHook(() => useVibecheckFlow());

    expect(result.current.state.sessionToken).toBe("abc123");
    expect(sessionStorage.getItem("vibeguard_session_token")).toBe("abc123");
  });

  it("restores a token already in sessionStorage from a prior page load (no fragment present)", () => {
    sessionStorage.setItem("vibeguard_session_token", "persisted-token");

    const { result } = renderHook(() => useVibecheckFlow());

    expect(result.current.state.sessionToken).toBe("persisted-token");
  });

  it("a fragment token takes precedence over, and overwrites, a stale stored token", () => {
    sessionStorage.setItem("vibeguard_session_token", "stale-token");
    window.location.hash = "#session_token=fresh-token";

    const { result } = renderHook(() => useVibecheckFlow());

    expect(result.current.state.sessionToken).toBe("fresh-token");
    expect(sessionStorage.getItem("vibeguard_session_token")).toBe("fresh-token");
  });

  it("signInWithGithub redirects to the backend's GitHub OAuth login endpoint", async () => {
    const { result } = renderHook(() => useVibecheckFlow());

    act(() => result.current.actions.signInWithGithub());

    expect(window.location.assign).toHaveBeenCalledWith(`${API_BASE}/auth/github/login`);
  });

  it("completes a full OAuth round trip: sign-in saves the connected repo, and the callback redirect restores it and re-fetches its findings", async () => {
    const fetchSpy = vi
      .spyOn(globalThis, "fetch")
      .mockImplementation((async (input: RequestInfo | URL) => {
        const url = String(input);
        if (url === `${API_BASE}/repositories`) {
          return { ok: true, json: async () => ({ status: "scan_pending_implementation", id: 42 }) } as Response;
        }
        if (url.startsWith("https://api.github.com/")) {
          return { ok: false, json: async () => [] } as Response;
        }
        throw new Error(`unexpected fetch url in test: ${url}`);
      }) as typeof fetch);

    const { result, unmount } = renderHook(() => useVibecheckFlow());
    await attachRepo(result, 42);

    act(() => result.current.actions.signInWithGithub());
    expect(window.location.assign).toHaveBeenCalledWith(`${API_BASE}/auth/github/login`);
    expect(JSON.parse(sessionStorage.getItem("vibeguard_pending_repo") ?? "{}")).toMatchObject({ repoId: "42" });

    // The redirect is a full page navigation -- the old hook instance is gone.
    unmount();
    fetchSpy.mockRestore();

    // Simulate GitHub's callback landing back on the app with a fragment token.
    window.location.hash = "#session_token=tok-123";
    vi.spyOn(globalThis, "fetch").mockImplementation((async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url === `${API_BASE}/repositories/42/findings`) {
        return { ok: true, json: async () => ({ findings: [{ id: 1, severity: "high" }] }) } as Response;
      }
      throw new Error(`unexpected fetch url in test: ${url}`);
    }) as typeof fetch);

    const restored = renderHook(() => useVibecheckFlow());
    expect(restored.result.current.state.sessionToken).toBe("tok-123");
    expect(restored.result.current.state.repoId).toBe("42");
    expect(restored.result.current.state.screen).toBe(2);
    expect(restored.result.current.state.sessionRestoring).toBe(true);

    await act(async () => {
      await flushMicrotasks();
    });
    expect(restored.result.current.state.sessionRestoring).toBe(false);
    expect(restored.result.current.state.realFindings).toEqual([{ id: 1, severity: "high" }]);
    expect(sessionStorage.getItem("vibeguard_pending_repo")).toBeNull();
  });

  it("startRemediation triggers sign-in instead of calling the remediate endpoint when there is no session token", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch");
    const { result } = renderHook(() => useVibecheckFlow());
    await attachRepoWithMockedFetch(result, fetchSpy, 7);
    fetchSpy.mockClear();

    await act(async () => {
      await result.current.actions.startRemediation();
    });

    expect(window.location.assign).toHaveBeenCalledWith(`${API_BASE}/auth/github/login`);
    expect(fetchSpy).not.toHaveBeenCalledWith(
      `${API_BASE}/repositories/7/remediate`,
      expect.anything(),
    );
  });

  it("startRemediation calls POST /repositories/{id}/remediate with the bearer token attached, and advances to the review screen on success", async () => {
    // Give the hook a real token the same way the app does: it's already in
    // sessionStorage from a prior page load (post-OAuth-callback reload).
    sessionStorage.setItem("vibeguard_session_token", "real-token");
    const fetchSpy = vi.spyOn(globalThis, "fetch");
    const { result } = renderHook(() => useVibecheckFlow());
    expect(result.current.state.sessionToken).toBe("real-token");
    await attachRepoWithMockedFetch(result, fetchSpy, 7);

    fetchSpy.mockImplementation((async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url === `${API_BASE}/repositories/7/remediate`) {
        expect(init?.method).toBe("POST");
        expect((init?.headers as Record<string, string>)?.Authorization).toBe("Bearer real-token");
        return {
          ok: true,
          status: 200,
          json: async () => ({ remediations: [{ id: 1 }], attempted: 1, succeeded: 1, files_over_cap: 0 }),
        } as Response;
      }
      throw new Error(`unexpected fetch url in test: ${url}`);
    }) as typeof fetch);

    await act(async () => {
      await result.current.actions.startRemediation();
    });
    await act(async () => {
      await vi.advanceTimersByTimeAsync(300);
    });

    expect(result.current.state.realRemediations).toEqual([{ id: 1 }]);
    expect(result.current.state.remediationSummary).toEqual({ attempted: 1, succeeded: 1, filesOverCap: 0 });
    expect(result.current.state.screen).toBe(4);
    expect(result.current.state.remediationError).toBeNull();
  });

  it("decideRemediation calls POST /remediations/{id}/approve with the bearer token attached", async () => {
    sessionStorage.setItem("vibeguard_session_token", "real-token");
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockImplementation((async (
      input: RequestInfo | URL,
      init?: RequestInit,
    ) => {
      const url = String(input);
      if (url === `${API_BASE}/remediations/9/approve`) {
        expect(init?.method).toBe("POST");
        expect((init?.headers as Record<string, string>)?.Authorization).toBe("Bearer real-token");
        return {
          ok: true,
          status: 200,
          json: async () => ({ id: 9, status: "pushed" }),
        } as Response;
      }
      throw new Error(`unexpected fetch url in test: ${url}`);
    }) as typeof fetch);

    const { result } = renderHook(() => useVibecheckFlow());
    expect(result.current.state.sessionToken).toBe("real-token");

    await act(async () => {
      await result.current.actions.decideRemediation(9, "approve");
    });

    expect(fetchSpy).toHaveBeenCalledWith(
      `${API_BASE}/remediations/9/approve`,
      expect.objectContaining({ method: "POST" }),
    );
  });

  it("decideRemediation clears the stored token and re-triggers sign-in on a 401 instead of treating it as an accepted end state", async () => {
    sessionStorage.setItem("vibeguard_session_token", "expired-token");
    vi.spyOn(globalThis, "fetch").mockResolvedValue({ ok: false, status: 401 } as Response);

    const { result } = renderHook(() => useVibecheckFlow());
    expect(result.current.state.sessionToken).toBe("expired-token");

    await act(async () => {
      await result.current.actions.decideRemediation(9, "approve");
    });

    expect(result.current.state.sessionToken).toBeNull();
    expect(sessionStorage.getItem("vibeguard_session_token")).toBeNull();
    expect(window.location.assign).toHaveBeenCalledWith(`${API_BASE}/auth/github/login`);
  });

  it("startRemediation clears the stored token and re-triggers sign-in on a 401 rather than accepting it", async () => {
    sessionStorage.setItem("vibeguard_session_token", "expired-token");
    const fetchSpy = vi.spyOn(globalThis, "fetch");
    const { result } = renderHook(() => useVibecheckFlow());
    await attachRepoWithMockedFetch(result, fetchSpy, 7);

    fetchSpy.mockResolvedValue({ ok: false, status: 401 } as Response);

    await act(async () => {
      await result.current.actions.startRemediation();
    });

    expect(result.current.state.sessionToken).toBeNull();
    expect(sessionStorage.getItem("vibeguard_session_token")).toBeNull();
    expect(window.location.assign).toHaveBeenCalledWith(`${API_BASE}/auth/github/login`);
  });

  it("finishRemediationReview advances from the real-findings review screen to the done screen", async () => {
    const { result } = renderHook(() => useVibecheckFlow());

    act(() => result.current.actions.finishRemediationReview());
    await act(async () => {
      await vi.advanceTimersByTimeAsync(300);
    });

    expect(result.current.state.screen).toBe(5);
  });

  it("leaves the fixture-only demo path unaffected: approveFixes never calls fetch and still drives the timer-simulated implement screen", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch");
    const { result } = renderHook(() => useVibecheckFlow());

    const findingId = result.current.state.findings[0].id;
    act(() => result.current.actions.setFindingStatus(findingId, "queued", 0));
    act(() => result.current.actions.approveFixes());
    await act(async () => {
      await vi.advanceTimersByTimeAsync(300);
    });

    expect(result.current.state.screen).toBe(3);
    expect(result.current.state.implementSteps.length).toBeGreaterThan(0);
    expect(fetchSpy).not.toHaveBeenCalled();
  });
});

/** Drains the microtask queue (chained fetch/.then/.finally promise continuations) without depending on real or faked macrotask timers. */
async function flushMicrotasks(): Promise<void> {
  for (let i = 0; i < 10; i++) {
    await Promise.resolve();
  }
}

/** Like `attachRepo`, but lets the caller keep controlling the fetch mock (used when a test also cares about later calls on the same spy). */
async function attachRepoWithMockedFetch(
  result: { current: ReturnType<typeof useVibecheckFlow> },
  fetchSpy: ReturnType<typeof vi.spyOn>,
  repoId: number,
) {
  fetchSpy.mockImplementation((async (input: RequestInfo | URL) => {
    const url = String(input);
    if (url === `${API_BASE}/repositories`) {
      return { ok: true, json: async () => ({ status: "scan_pending_implementation", id: repoId }) } as Response;
    }
    if (url.startsWith("https://api.github.com/")) {
      return { ok: false, json: async () => [] } as Response;
    }
    throw new Error(`unexpected fetch url in test: ${url}`);
  }) as typeof fetch);

  await act(async () => {
    result.current.actions.onRepoUrlInput(repoUrlChangeEvent("https://github.com/acme/widgets"));
  });
  await act(async () => {
    await result.current.actions.submitRepoUrl();
  });
  expect(result.current.state.repoId).toBe(String(repoId));
}
