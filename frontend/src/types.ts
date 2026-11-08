export type Severity = "critical" | "serious" | "moderate" | "minor";

export interface Finding {
  id: string;
  rule_id: string;
  category: string;
  severity: Severity;
  wcag: string[];
  selector: string;
  al_id: string;
  html: string;
  message: string;
  help_url: string;
  crop_path?: string | null;
  bbox?: { x: number; y: number; w: number; h: number } | null;
}

export interface ScanResult {
  scan_id: string;
  url: string;
  findings: Finding[];
  screenshot_path?: string | null;
}

export interface PatchOp {
  finding_id: string;
  al_id: string;
  op: "set_attribute" | "set_text" | "add_style";
  name?: string | null;
  value: string;
  explanation: string;
}

export interface Explanation {
  what: string;
  why: string;
  who: string;
  how: string;
}

export interface FindingAnalysis {
  finding_id: string;
  category: string;
  explanation: Explanation;
  patch?: PatchOp | null;
  patch_source: "deterministic" | "llm" | "none";
  confidence: "high" | "medium" | "low";
  needs_human_review: boolean;
  evidence: string;
  original_html?: string | null;
  proposed_html?: string | null;
  note: string;
}

export interface VerifyResult {
  scan_id: string;
  before_count: number;
  after_count: number;
  resolved: string[];
  remaining: string[];
  introduced: string[];
  failed_ops: string[];
  before_screenshot: string;
  after_screenshot: string;
  live_only?: string[];
  snapshot_only?: string[];
}
