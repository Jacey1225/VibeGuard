import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { AttachmentChips } from "./AttachmentChips";

/**
 * Regression coverage for intake spec 20260807-repo-file-preview-truncated:
 * AttachmentChips used to fall back to three hardcoded fixture filenames
 * (`db.js`, `login.js`, `profile.js` -- see `src/data/fixtures.ts`'s
 * `FILES`) whenever it received no files, which is exactly what a
 * connected repository's now-removed GitHub API preview call produced in
 * the common case. It now takes a truthful backend-derived summary
 * instead of a per-file list, so there is no fixture data left to fall
 * back to.
 */
describe("AttachmentChips", () => {
  it("renders nothing, and no fixture filenames, when there is no summary yet", () => {
    render(<AttachmentChips summary={null} />);
    expect(screen.queryByText(/db\.js/)).not.toBeInTheDocument();
    expect(screen.queryByText(/login\.js/)).not.toBeInTheDocument();
    expect(screen.queryByText(/profile\.js/)).not.toBeInTheDocument();
  });

  it("renders a truthful file-count chip from the backend-derived summary", () => {
    render(<AttachmentChips summary={{ totalFiles: 142, filesTruncated: false }} />);
    expect(screen.getByText("142 files ready to scan")).toBeInTheDocument();
    expect(screen.queryByText(/db\.js/)).not.toBeInTheDocument();
  });

  it("singularizes the count for exactly one file", () => {
    render(<AttachmentChips summary={{ totalFiles: 1, filesTruncated: false }} />);
    expect(screen.getByText("1 file ready to scan")).toBeInTheDocument();
  });

  it("surfaces a truncation note when the backend reports files_truncated", () => {
    render(<AttachmentChips summary={{ totalFiles: 20000, filesTruncated: true }} />);
    expect(screen.getByText(/some files were skipped/)).toBeInTheDocument();
  });
});
