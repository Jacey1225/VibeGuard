import { CODE_SNIPPETS } from "../data/fixtures";
import type { CodeSnippetLine } from "../types";

export interface SplitSnippet {
  file: string;
  before: CodeSnippetLine[];
  flag: CodeSnippetLine;
  after: CodeSnippetLine[];
  fixedLine: string;
  fixSummary: string;
  doneSummary: string;
  working: string;
  achievement: string;
}

/** Splits a code snippet fixture into the lines before/at/after its flagged line. */
export function splitSnippet(id: number): SplitSnippet {
  const s = CODE_SNIPPETS[id];
  const numbered = s.lines.map((text, i) => ({ num: s.startLine + i, text }));
  const flagIdx = numbered.findIndex((l) => l.num === s.flagLine);
  return {
    file: s.file,
    before: numbered.slice(0, flagIdx),
    flag: numbered[flagIdx],
    after: numbered.slice(flagIdx + 1),
    fixedLine: s.fixedLine,
    fixSummary: s.fixSummary,
    doneSummary: s.doneSummary,
    working: s.working,
    achievement: s.achievement,
  };
}

export function mapContextLine(l: CodeSnippetLine): CodeSnippetLine {
  return { num: l.num, text: l.text === "" ? " " : l.text };
}

export interface SlicedContext {
  beforeLines: CodeSnippetLine[];
  afterLines: CodeSnippetLine[];
}

/** Trims a snippet's before/after context lines down to fit the given row budget. */
export function sliceAround(snip: SplitSnippet, contextRows: number): SlicedContext {
  const ctx = Math.max(1, contextRows);
  const before = Math.min(snip.before.length, Math.max(1, Math.ceil(ctx * 0.6)));
  const after = Math.max(0, Math.min(snip.after.length, ctx - before));
  return {
    beforeLines: snip.before.slice(snip.before.length - before).map(mapContextLine),
    afterLines: snip.after.slice(0, after).map(mapContextLine),
  };
}
