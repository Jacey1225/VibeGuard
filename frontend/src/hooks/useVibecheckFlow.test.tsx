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

  it("resetFlow returns to the composer with every finding back to pending", () => {
    const { result } = renderHook(() => useVibecheckFlow());
    act(() => result.current.actions.setFindingStatus(1, "skipped", 0));
    act(() => result.current.actions.resetFlow());
    expect(result.current.state.screen).toBe(0);
    expect(result.current.state.codeInput).toBe("");
    expect(result.current.state.findings.every((f) => f.status === "pending")).toBe(true);
  });
});
