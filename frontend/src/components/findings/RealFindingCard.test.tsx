import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { RealFindingCard } from "./RealFindingCard";
import type { RealFinding } from "../../hooks/useVibecheckFlow";

/**
 * Bug A regression coverage: RealFindingCard's preview used to call
 * api.github.com directly and surface the browser's literal "failed to
 * fetch" TypeError message on any network-level failure. It now calls
 * the backend's GET /repositories/{id}/files/preview and must surface
 * that backend's specific `detail` message instead -- these tests fail
 * before the fix (bare "failed to fetch") and pass after.
 */

function makeFinding(overrides: Partial<RealFinding> = {}): RealFinding {
  return {
    id: 1,
    category: "injection",
    severity: "high",
    source: "heuristic_confirmed",
    title: "SQL injection via string concatenation",
    description: "User input is concatenated directly into a SQL query.",
    remediation: "Use parameterized queries.",
    relative_path: "src/app.py",
    line_number: 42,
    model: "test-model",
    created_at: "2026-01-01T00:00:00Z",
    ...overrides,
  };
}

afterEach(() => {
  vi.unstubAllEnvs();
  vi.restoreAllMocks();
});

describe("RealFindingCard preview error handling", () => {
  it("surfaces the backend's specific detail message for a 404 (file not found), not a bare network error", async () => {
    vi.stubEnv("VITE_VIBECHECK_API_URL", "https://configured-backend.example");
    vi.spyOn(globalThis, "fetch").mockResolvedValue({
      ok: false,
      status: 404,
      json: async () => ({ detail: "no file at 'src/app.py' was stored for repository 7" }),
    } as Response);

    render(<RealFindingCard finding={makeFinding()} repoId="7" checked onToggle={() => {}} />);

    await waitFor(() => {
      expect(screen.getByText(/no file at 'src\/app\.py' was stored for repository 7/)).toBeInTheDocument();
    });
    expect(screen.queryByText(/failed to fetch/i)).not.toBeInTheDocument();
  });

  it("surfaces the backend's specific detail message for a 422 (binary/oversized file skipped at intake)", async () => {
    vi.stubEnv("VITE_VIBECHECK_API_URL", "https://configured-backend.example");
    vi.spyOn(globalThis, "fetch").mockResolvedValue({
      ok: false,
      status: 422,
      json: async () => ({ detail: "'assets/logo.png' was skipped during intake (binary) and has no stored content" }),
    } as Response);

    render(<RealFindingCard finding={makeFinding({ relative_path: "assets/logo.png" })} repoId="7" checked onToggle={() => {}} />);

    await waitFor(() => {
      expect(screen.getByText(/skipped during intake \(binary\)/)).toBeInTheDocument();
    });
  });

  it("surfaces the backend's specific detail message for a 422 (line out of range)", async () => {
    vi.stubEnv("VITE_VIBECHECK_API_URL", "https://configured-backend.example");
    vi.spyOn(globalThis, "fetch").mockResolvedValue({
      ok: false,
      status: 422,
      json: async () => ({ detail: "line 42 is outside the file's current length (10 lines)" }),
    } as Response);

    render(<RealFindingCard finding={makeFinding()} repoId="7" checked onToggle={() => {}} />);

    await waitFor(() => {
      expect(screen.getByText(/outside the file's current length/)).toBeInTheDocument();
    });
  });

  it("still renders a clear error affordance (not a hang) on a genuine network-level failure reaching the backend", async () => {
    // A real network failure against our own backend is now the *only*
    // path that can produce the browser's literal TypeError message --
    // distinct from the old per-card, unauthenticated api.github.com
    // calls, which failed this way on ordinary rate-limiting. Confirm
    // the card still resolves to a specific, non-hanging error state.
    vi.stubEnv("VITE_VIBECHECK_API_URL", "https://configured-backend.example");
    vi.spyOn(globalThis, "fetch").mockRejectedValue(new TypeError("Failed to fetch"));

    render(<RealFindingCard finding={makeFinding()} repoId="7" checked onToggle={() => {}} />);

    await waitFor(() => {
      expect(screen.queryByText(/loading code preview/i)).not.toBeInTheDocument();
    });
    expect(screen.getByText(/see the full file: src\/app\.py/)).toBeInTheDocument();
  });

  it("renders a windowed, highlighted preview on success", async () => {
    vi.stubEnv("VITE_VIBECHECK_API_URL", "https://configured-backend.example");
    vi.spyOn(globalThis, "fetch").mockResolvedValue({
      ok: true,
      json: async () => ({
        relative_path: "src/app.py",
        lines: [
          { number: 41, text: "def run():" },
          { number: 42, text: "    query(user_input)" },
          { number: 43, text: "    return" },
        ],
        highlight_line: 42,
      }),
    } as Response);

    render(<RealFindingCard finding={makeFinding()} repoId="7" checked onToggle={() => {}} />);

    await waitFor(() => {
      expect(screen.getByText("query(user_input)")).toBeInTheDocument();
    });
  });

  it("calls the backend preview endpoint with the repository id, not a direct api.github.com URL", async () => {
    vi.stubEnv("VITE_VIBECHECK_API_URL", "https://configured-backend.example");
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue({
      ok: true,
      json: async () => ({ relative_path: "src/app.py", lines: [], highlight_line: 42 }),
    } as Response);

    render(<RealFindingCard finding={makeFinding()} repoId="7" checked onToggle={() => {}} />);

    await waitFor(() => expect(fetchSpy).toHaveBeenCalled());
    const calledUrl = String(fetchSpy.mock.calls[0][0]);
    expect(calledUrl).toBe(
      "https://configured-backend.example/repositories/7/files/preview?path=src%2Fapp.py&line=42",
    );
    expect(calledUrl).not.toContain("api.github.com");
  });
});
