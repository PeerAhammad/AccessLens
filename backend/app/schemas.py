from typing import Literal, Optional
from pydantic import BaseModel
from .patches import PatchOp

Severity = Literal["critical", "serious", "moderate", "minor"]


class Finding(BaseModel):
    id: str                 # stable: f"{rule_id}:{al_id}"
    rule_id: str            # axe rule id, e.g. "image-alt"
    category: str           # alt_text | form_label | contrast | empty_name | heading | language
    severity: Severity
    wcag: list[str]
    selector: str
    al_id: str              # data-al-id tag, stable across copies
    html: str               # offending element outerHTML (truncated)
    message: str            # axe failure summary
    help_url: str
    crop_path: Optional[str] = None   # element screenshot (images only)
    bbox: Optional[dict[str, float]] = None   # x,y,w,h in the 1280x800 viewport screenshot


class ScanRequest(BaseModel):
    url: str


class ScanResult(BaseModel):
    scan_id: str
    url: str
    findings: list[Finding]
    screenshot_path: Optional[str] = None
    html_snapshot: str
    final_url: Optional[str] = None   # URL after redirects; the isolated copy is served at this address


class VerifyResult(BaseModel):
    scan_id: str
    before_count: int
    after_count: int
    resolved: list[str]
    remaining: list[str]
    introduced: list[str]
    failed_ops: list[str]
    before_screenshot: str
    after_screenshot: str
    live_only: list[str] = []       # issues in the live scan that the isolated copy did not reproduce
    snapshot_only: list[str] = []   # issues the isolated copy found that the live scan did not


class Explanation(BaseModel):
    what: str   # what is wrong
    why: str    # why it matters
    who: str    # who is affected
    how: str    # how to fix it


class FindingAnalysis(BaseModel):
    finding_id: str
    category: str
    explanation: Explanation
    patch: Optional[PatchOp] = None
    patch_source: Literal["deterministic", "llm", "none"] = "none"
    confidence: Literal["high", "medium", "low"] = "low"
    needs_human_review: bool = True
    evidence: str = ""
    original_html: Optional[str] = None
    proposed_html: Optional[str] = None
    note: str = ""


class AnalyzeResult(BaseModel):
    scan_id: str
    analyses: list[FindingAnalysis]
    source: Literal["live", "cache"] = "live"
    cached_at: Optional[str] = None
