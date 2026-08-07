import { render, screen } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { SnippetFindingCard } from "./SnippetFindingCard";
import type { SnippetFinding } from "../../hooks/useVibecheckFlow";

/**
 * SnippetFindingCard sources its code preview by slicing the snippet's own
 * text client-side (no `/repositories/{id}/files/preview` fetch), since a
 * snippet has no stored server-side file to preview.
 */

function makeFinding(overrides: Partial<SnippetFinding> = {}): SnippetFinding {
  return {
    id: 1,
    category: "injection",
    severity: "high",
    source: "heuristic_confirmed",
    title: "SQL injection via string concatenation",
    description: "User input is concatenated directly into a SQL query.",
    remediation: "Use parameterized queries.",
    relative_path: "snippet.py",
    line_number: 3,
    model: "test-model",
    created_at: "2026-01-01T00:00:00Z",
    ...overrides,
  };
}

const SNIPPET_CONTENT = ["line1", "line2", 'query = "SELECT * FROM users WHERE id = " + user_id', "line4", "line5"].join("\n");

beforeEach(() => {
  // SnippetFixControl (rendered on every card) does its own GET-on-mount
  // fix-existence check -- stub it out so these slicing-focused tests never
  // touch the real network, per testing-standards.
  vi.spyOn(globalThis, "fetch").mockResolvedValue({ ok: false, status: 404 } as Response);
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("SnippetFindingCard client-side context slicing", () => {
  it("never calls a file-preview-shaped endpoint -- code context comes purely from the snippetContent prop, not a server round trip", () => {
    const fetchSpy = globalThis.fetch as ReturnType<typeof vi.fn>;

    render(<SnippetFindingCard finding={makeFinding()} snippetContent={SNIPPET_CONTENT} snippetId="5" />);

    const calledUrls = fetchSpy.mock.calls.map((call) => String(call[0]));
    expect(calledUrls.every((u) => !u.includes("/files/preview"))).toBe(true);
  });

  it("slices and highlights the flagged line with surrounding context", () => {
    render(<SnippetFindingCard finding={makeFinding({ line_number: 3 })} snippetContent={SNIPPET_CONTENT} snippetId="5" />);

    expect(screen.getByText(/SELECT \* FROM users/)).toBeInTheDocument();
    expect(screen.getByText("line1")).toBeInTheDocument();
    expect(screen.getByText("line5")).toBeInTheDocument();
  });

  it("shows a fallback message and no code block when line_number is null", () => {
    render(<SnippetFindingCard finding={makeFinding({ line_number: null })} snippetContent={SNIPPET_CONTENT} snippetId="5" />);

    expect(screen.getByText(/no specific line reported/i)).toBeInTheDocument();
    expect(screen.queryByText("line1")).not.toBeInTheDocument();
  });

  it("shows the fallback message when the reported line is out of range for the current snippet text", () => {
    render(<SnippetFindingCard finding={makeFinding({ line_number: 999 })} snippetContent={SNIPPET_CONTENT} snippetId="5" />);

    expect(screen.getByText(/no specific line reported/i)).toBeInTheDocument();
  });

  it("renders the finding's severity label and title", () => {
    render(<SnippetFindingCard finding={makeFinding({ severity: "critical", title: "Hardcoded secret" })} snippetContent={SNIPPET_CONTENT} snippetId="5" />);

    expect(screen.getByText("Critical")).toBeInTheDocument();
    expect(screen.getByText("Hardcoded secret")).toBeInTheDocument();
  });
});
