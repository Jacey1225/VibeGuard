export type Severity = "high" | "medium" | "low";

export interface SeverityInfo {
  label: string;
  color: string;
  soft: string;
  tint: string;
}

export type FindingStatus = "pending" | "queued" | "skipped";

export interface Finding {
  id: number;
  severity: Severity;
  title: string;
  plain: string;
  status: FindingStatus;
}

export interface FileFixture {
  name: string;
  short: string;
  lang: string;
  findingId: number | null;
  start: number;
  end: number;
  rows: number[];
}

export interface CodeSnippetLine {
  num: number;
  text: string;
}

export interface CodeSnippet {
  file: string;
  lines: string[];
  startLine: number;
  flagLine: number;
  fixedLine: string;
  fixSummary: string;
  doneSummary: string;
  working: string;
  achievement: string;
}

export interface ScopeItemDef {
  key: string;
  label: string;
  desc: string;
}

export type ImplementStepKind = "fix" | "validate";
export type ImplementStepStatus = "pending" | "running" | "done";

export interface ImplementStep {
  status: ImplementStepStatus;
  kind: ImplementStepKind;
  findingId?: number;
}
