import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { SnippetFixControl } from "./SnippetFixControl";

/**
 * SnippetFixControl's idle/editing/saving/submitted lifecycle, its
 * GET-on-mount existence check, the edit/resubmit flow, and error handling
 * on a failed submission.
 */

const API_BASE = "https://configured-backend.example";
const FIX_URL = `${API_BASE}/snippets/5/findings/1/fix`;

beforeEach(() => {
  vi.stubEnv("VITE_VIBECHECK_API_URL", API_BASE);
});

afterEach(() => {
  vi.unstubAllEnvs();
  vi.restoreAllMocks();
});

describe("SnippetFixControl", () => {
  it("GETs the fix on mount and shows the idle 'Submit your fix' affordance on a 404 (no fix yet)", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockResolvedValue({ ok: false, status: 404 } as Response);

    render(<SnippetFixControl snippetId="5" findingId={1} />);

    await waitFor(() => expect(fetchSpy).toHaveBeenCalledWith(FIX_URL));
    expect(await screen.findByText("Submit your fix")).toBeInTheDocument();
  });

  it("GETs the fix on mount and shows the read-only submitted view when one already exists", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue({
      ok: true,
      json: async () => ({
        id: 1,
        snippet_finding_id: 1,
        fixed_content: "def safe(): pass",
        created_at: "2026-01-01T00:00:00Z",
        updated_at: "2026-01-01T00:00:00Z",
      }),
    } as Response);

    render(<SnippetFixControl snippetId="5" findingId={1} />);

    expect(await screen.findByText("Fix submitted")).toBeInTheDocument();
    expect(screen.getByText("def safe(): pass")).toBeInTheDocument();
    expect(screen.getByText("Edit")).toBeInTheDocument();
  });

  it("clicking 'Submit your fix' opens the editor, and Cancel from a fresh (no prior submission) editor returns to idle", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue({ ok: false, status: 404 } as Response);

    render(<SnippetFixControl snippetId="5" findingId={1} />);
    fireEvent.click(await screen.findByText("Submit your fix"));

    expect(screen.getByLabelText("Your fixed code")).toBeInTheDocument();

    fireEvent.click(screen.getByText("Cancel"));

    expect(await screen.findByText("Submit your fix")).toBeInTheDocument();
    expect(screen.queryByLabelText("Your fixed code")).not.toBeInTheDocument();
  });

  it("submits a new fix: POSTs fixed_content, then shows the submitted view with the response content", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockImplementation((async (
      input: RequestInfo | URL,
      init?: RequestInit,
    ) => {
      if (String(input) === FIX_URL && (!init || init.method === undefined)) {
        return { ok: false, status: 404 } as Response;
      }
      if (String(input) === FIX_URL && init?.method === "POST") {
        const body = JSON.parse(init.body as string);
        expect(body).toEqual({ fixed_content: "def safe(): pass" });
        return {
          ok: true,
          json: async () => ({
            id: 1,
            snippet_finding_id: 1,
            fixed_content: "def safe(): pass",
            created_at: "2026-01-01T00:00:00Z",
            updated_at: "2026-01-01T00:00:00Z",
          }),
        } as Response;
      }
      throw new Error(`unexpected fetch in test: ${String(input)} ${init?.method}`);
    }) as typeof fetch);

    render(<SnippetFixControl snippetId="5" findingId={1} />);
    fireEvent.click(await screen.findByText("Submit your fix"));

    fireEvent.change(screen.getByLabelText("Your fixed code"), { target: { value: "def safe(): pass" } });
    fireEvent.click(screen.getByText("Submit fix"));

    await waitFor(() => expect(screen.getByText("Fix submitted")).toBeInTheDocument());
    expect(screen.getByText("def safe(): pass")).toBeInTheDocument();
    expect(fetchSpy).toHaveBeenCalledWith(FIX_URL, expect.objectContaining({ method: "POST" }));
  });

  it("the Submit fix button is disabled while the draft is empty/whitespace-only", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue({ ok: false, status: 404 } as Response);

    render(<SnippetFixControl snippetId="5" findingId={1} />);
    fireEvent.click(await screen.findByText("Submit your fix"));

    const submitButton = screen.getByText("Submit fix") as HTMLButtonElement;
    expect(submitButton.disabled).toBe(true);

    fireEvent.change(screen.getByLabelText("Your fixed code"), { target: { value: "   " } });
    expect(submitButton.disabled).toBe(true);

    fireEvent.change(screen.getByLabelText("Your fixed code"), { target: { value: "real content" } });
    expect(submitButton.disabled).toBe(false);
  });

  it("edit-and-resubmit: clicking Edit on a submitted fix prefills the textarea, and resubmitting overwrites the shown content", async () => {
    const fetchSpy = vi.spyOn(globalThis, "fetch").mockImplementation((async (
      input: RequestInfo | URL,
      init?: RequestInit,
    ) => {
      if (String(input) === FIX_URL && !init) {
        return {
          ok: true,
          json: async () => ({
            id: 1,
            snippet_finding_id: 1,
            fixed_content: "first attempt",
            created_at: "2026-01-01T00:00:00Z",
            updated_at: "2026-01-01T00:00:00Z",
          }),
        } as Response;
      }
      if (String(input) === FIX_URL && init?.method === "POST") {
        return {
          ok: true,
          json: async () => ({
            id: 1,
            snippet_finding_id: 1,
            fixed_content: "second attempt",
            created_at: "2026-01-01T00:00:00Z",
            updated_at: "2026-01-01T00:01:00Z",
          }),
        } as Response;
      }
      throw new Error(`unexpected fetch in test: ${String(input)} ${init?.method}`);
    }) as typeof fetch);

    render(<SnippetFixControl snippetId="5" findingId={1} />);
    expect(await screen.findByText("first attempt")).toBeInTheDocument();

    fireEvent.click(screen.getByText("Edit"));
    const textarea = screen.getByLabelText("Your fixed code") as HTMLTextAreaElement;
    expect(textarea.value).toBe("first attempt");

    fireEvent.change(textarea, { target: { value: "second attempt" } });
    fireEvent.click(screen.getByText("Submit fix"));

    await waitFor(() => expect(screen.getByText("second attempt")).toBeInTheDocument());
    expect(screen.queryByText("first attempt")).not.toBeInTheDocument();
    expect(fetchSpy).toHaveBeenCalledWith(FIX_URL, expect.objectContaining({ method: "POST" }));
  });

  it("Cancel while editing an existing submission returns to the read-only submitted view (not idle)", async () => {
    vi.spyOn(globalThis, "fetch").mockResolvedValue({
      ok: true,
      json: async () => ({
        id: 1,
        snippet_finding_id: 1,
        fixed_content: "already submitted",
        created_at: "2026-01-01T00:00:00Z",
        updated_at: "2026-01-01T00:00:00Z",
      }),
    } as Response);

    render(<SnippetFixControl snippetId="5" findingId={1} />);
    expect(await screen.findByText("Fix submitted")).toBeInTheDocument();

    fireEvent.click(screen.getByText("Edit"));
    fireEvent.change(screen.getByLabelText("Your fixed code"), { target: { value: "a draft edit" } });
    fireEvent.click(screen.getByText("Cancel"));

    expect(screen.getByText("Fix submitted")).toBeInTheDocument();
    expect(screen.getByText("already submitted")).toBeInTheDocument();
    expect(screen.queryByText("Submit your fix")).not.toBeInTheDocument();
  });

  it("shows the backend's error detail and preserves the draft when a submission fails", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation((async (input: RequestInfo | URL, init?: RequestInit) => {
      if (String(input) === FIX_URL && !init) {
        return { ok: false, status: 404 } as Response;
      }
      if (String(input) === FIX_URL && init?.method === "POST") {
        return { ok: false, status: 422, json: async () => ({ detail: "fixed_content must not be empty" }) } as Response;
      }
      throw new Error(`unexpected fetch in test: ${String(input)}`);
    }) as typeof fetch);

    render(<SnippetFixControl snippetId="5" findingId={1} />);
    fireEvent.click(await screen.findByText("Submit your fix"));

    fireEvent.change(screen.getByLabelText("Your fixed code"), { target: { value: "a draft the user typed" } });
    fireEvent.click(screen.getByText("Submit fix"));

    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent("fixed_content must not be empty"));
    // The draft the user typed must survive the failed submission so they don't have to retype it.
    expect((screen.getByLabelText("Your fixed code") as HTMLTextAreaElement).value).toBe("a draft the user typed");
  });

  it("shows a network-failure error message and preserves the draft when fetch itself rejects", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation((async (input: RequestInfo | URL, init?: RequestInit) => {
      if (String(input) === FIX_URL && !init) {
        return { ok: false, status: 404 } as Response;
      }
      throw new TypeError("Failed to fetch");
    }) as typeof fetch);

    render(<SnippetFixControl snippetId="5" findingId={1} />);
    fireEvent.click(await screen.findByText("Submit your fix"));

    fireEvent.change(screen.getByLabelText("Your fixed code"), { target: { value: "my draft" } });
    fireEvent.click(screen.getByText("Submit fix"));

    await waitFor(() => expect(screen.getByRole("alert")).toBeInTheDocument());
    expect((screen.getByLabelText("Your fixed code") as HTMLTextAreaElement).value).toBe("my draft");
  });

  it("falls back to the idle state without throwing when VITE_VIBECHECK_API_URL is unset", async () => {
    vi.unstubAllEnvs();
    vi.stubEnv("VITE_VIBECHECK_API_URL", "");
    const fetchSpy = vi.spyOn(globalThis, "fetch");

    render(<SnippetFixControl snippetId="5" findingId={1} />);

    expect(await screen.findByText("Submit your fix")).toBeInTheDocument();
    expect(fetchSpy).not.toHaveBeenCalled();
  });
});
