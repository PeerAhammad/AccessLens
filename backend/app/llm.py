"""Evidence-grounded explanations + patch generation (batched).

Rules enforced in code (not just in the prompt):
- The LLM never chooses the target element or the attribute: we force both from the finding.
- Output must validate against a schema, or the finding falls back to a static explanation
  and is flagged for human review.
- Generated values are checked (length, no markup, lang-code format) before becoming a PatchOp.
- Contrast fixes are computed deterministically (fixes.py); the LLM only explains them.
- Findings are sent in batches (5-8 per call) to minimise API calls and overload exposure.
"""
import asyncio
import base64
import json
import os
import pathlib
import re
from typing import Any, Awaitable, Callable, Literal, Optional

from bs4 import BeautifulSoup
from dotenv import load_dotenv
from pydantic import BaseModel

from .fixes import contrast_patch
from .patches import PatchOp, clean_html, preview_pair
from .schemas import AnalyzeResult, Explanation, Finding, FindingAnalysis, ScanResult

load_dotenv(pathlib.Path(__file__).resolve().parents[1] / ".env")   # backend/.env (git-ignored)


def _has(*names):
    return any(os.environ.get(n) for n in names)


PROVIDER = os.environ.get("ACCESSLENS_PROVIDER") or ("gemini" if _has("GEMINI_API_KEY", "GOOGLE_API_KEY") else "anthropic")
MODEL = os.environ.get("ACCESSLENS_MODEL") or ("gemini-3.8-flash" if PROVIDER == "gemini" else "claude-sonnet-5-5")

# category -> attribute the LLM is allowed to propose (None = explain only)
PATCH_ATTR = {"alt_text": "alt", "form_label": "aria-label", "empty_name": "aria-label",
              "language": "lang", "contrast": None, "heading": None}
LLM_PATCH_CATEGORIES = {"alt_text", "form_label", "empty_name", "language"}
RULE_LEVEL_CATEGORIES = {"contrast", "heading"}   # one explanation per rule, not per element

FIELD_GUIDE = {
    "alt_text": 'alt: plain-text description (max 125 chars) of the image\'s purpose. If an image is attached, '
                'describe what you actually see. Use "" ONLY if the image is purely decorative '
                '(spacer, border, ornament). If you cannot tell, set patch to null.',
    "form_label": "aria-label: short plain-text label for the field's purpose, derived ONLY from nearby text, "
                  "placeholder, name/id attributes or options shown in the context.",
    "empty_name": "aria-label: plain-text description of what the link/button does, derived ONLY from href, "
                  "child content, or nearby text in the context.",
    "language": "lang: BCP-47 code (e.g. en, fr, hi) of the page's primary language, from the page text sample.",
    "contrast": "patch must be null (computed elsewhere).",
    "heading": "patch must be null (heading changes alter meaning; a human must decide).",
}

SYSTEM = """You are an accessibility engineer. You explain WCAG failures and propose minimal fixes.
You receive a list of findings. Return exactly ONE item per finding, using the same "id" you were given.
STRICT RULES:
- Use ONLY the evidence provided for that finding (element HTML, parent HTML, axe message, page text, attached image).
- Never invent page content. If the evidence is insufficient, set "patch" to null and "needs_human_review" to true.
- "patch" value is PLAIN TEXT only: never HTML, never markup, never angle brackets.
- "confidence" is "high" only when the evidence directly supports the fix, "medium" if reasonable, otherwise "low".
- Keep explanation fields to 1-2 plain-language sentences each.
- Images are attached in order, each preceded by a label naming the finding id it belongs to.
- Respond with ONLY one JSON object, no markdown, in exactly this shape:
{"items":[{"id":"<id as given>",
  "explanation":{"what":"","why":"","who":"","how":""},
  "patch":{"value":"<plain text>"} or null,
  "confidence":"high|medium|low",
  "needs_human_review":false,
  "evidence":"which provided evidence supports this"}]}"""

FALLBACK = {
    "alt_text": Explanation(what="An image has no text alternative.", why="Screen readers cannot convey what the image shows.",
                            who="Blind and low-vision users, users on slow connections.", how="Add a descriptive alt attribute, or alt=\"\" if decorative."),
    "form_label": Explanation(what="A form field has no accessible label.", why="Assistive technology cannot tell users what to enter.",
                              who="Screen reader and voice-control users.", how="Associate a visible <label> or add an aria-label."),
    "contrast": Explanation(what="Text does not have enough contrast with its background.", why="Low-contrast text is hard or impossible to read.",
                            who="Low-vision users, colour-blind users, anyone in bright light.", how="Darken or lighten the text colour to reach the required ratio."),
    "empty_name": Explanation(what="A link or button has no accessible name.", why="Screen readers announce it as just 'link' or 'button'.",
                              who="Screen reader and voice-control users.", how="Add visible text or an aria-label describing its purpose."),
    "heading": Explanation(what="The heading structure has a problem.", why="Headings are how many users navigate and understand a page.",
                           who="Screen reader users and keyboard navigators.", how="Use heading levels in a logical, non-skipping order."),
    "language": Explanation(what="The page does not declare its language.", why="Screen readers may use the wrong pronunciation rules.",
                            who="Screen reader users, translation tools.", how="Add a lang attribute to the <html> element."),
}


class LLMOut(BaseModel):
    explanation: Explanation
    patch: Optional[Any] = None
    confidence: Literal["high", "medium", "low"] = "low"
    needs_human_review: bool = False
    evidence: str = ""


# llm(system, user_text, images) -> raw text.  images = [(label, png_path), ...]
LLMFn = Callable[[str, str, list], Awaitable[str]]


async def anthropic_call(system: str, user_text: str, images: Optional[list] = None) -> str:
    from anthropic import AsyncAnthropic   # reads ANTHROPIC_API_KEY from the environment
    client = AsyncAnthropic(timeout=90)
    content = []
    for label, path in images or []:
        if pathlib.Path(path).exists():
            data = base64.b64encode(pathlib.Path(path).read_bytes()).decode()
            content.append({"type": "text", "text": f"Image for finding {label}:"})
            content.append({"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": data}})
    content.append({"type": "text", "text": user_text})
    resp = await client.messages.create(model=MODEL, max_tokens=4000, system=system,
                                        messages=[{"role": "user", "content": content}])
    return "".join(b.text for b in resp.content if b.type == "text")


async def gemini_call(system: str, user_text: str, images: Optional[list] = None,
                      model: Optional[str] = None) -> str:
    model = model or MODEL
    from google import genai   # reads GEMINI_API_KEY (or GOOGLE_API_KEY) from the environment
    from google.genai import types
    client = genai.Client(http_options=types.HttpOptions(timeout=90000))
    parts = []
    for label, path in images or []:
        if pathlib.Path(path).exists():
            parts.append(f"Image for finding {label}:")
            parts.append(types.Part.from_bytes(data=pathlib.Path(path).read_bytes(), mime_type="image/png"))
    parts.append(user_text)

    def cfg(thinking_off: bool):
        kw = dict(system_instruction=system, response_mime_type="application/json",
                  temperature=0.2, max_output_tokens=6000)
        if thinking_off:
            kw["thinking_config"] = types.ThinkingConfig(thinking_budget=0)
        return types.GenerateContentConfig(**kw)

    try:
        resp = await client.aio.models.generate_content(model=model, contents=parts, config=cfg(True))
    except Exception as e:
        if "thinking" not in str(e).lower():
            raise
        # newer models may reject thinking_budget=0: retry with model defaults
        resp = await client.aio.models.generate_content(model=model, contents=parts, config=cfg(False))
    return resp.text or ""


FALLBACK_MODELS = [m.strip() for m in os.environ.get(
    "ACCESSLENS_FALLBACK_MODELS", "gemini-flash-latest,gemini-3.5-flash,gemini-3.1-flash-lite").split(",") if m.strip()]
RETRYABLE = ("503", "504", "500", "429", "UNAVAILABLE", "DEADLINE_EXCEEDED", "INTERNAL", "RESOURCE_EXHAUSTED",
             "overloaded", "high demand", "timed out", "Timeout", "disconnected")


def _retryable(e: Exception) -> bool:
    return any(t.lower() in str(e).lower() for t in RETRYABLE)


async def call_with_fallback(call, models: list[str], attempts: int = 3, delay: float = 2.0) -> str:
    """Try each model in order; retry transient errors (overload/rate limit); skip to the next model on 404."""
    last: Optional[Exception] = None
    for model in models:
        for attempt in range(attempts):
            try:
                return await call(model)
            except Exception as e:
                last = e
                if "404" in str(e) or "NOT_FOUND" in str(e):
                    break                               # model unavailable to us: next model
                if not _retryable(e):
                    raise                               # bad key / bad request: fail fast
                await asyncio.sleep(delay * (attempt + 1))
    raise last if last else RuntimeError("no models configured")


async def default_call(system: str, user_text: str, images: Optional[list] = None) -> str:
    if PROVIDER == "gemini":
        models = [MODEL] + [m for m in FALLBACK_MODELS if m != MODEL]
        return await call_with_fallback(lambda m: gemini_call(system, user_text, images, m), models)
    return await anthropic_call(system, user_text, images)


def element_context(snapshot: str, al_id: str) -> Optional[dict]:
    soup = BeautifulSoup(snapshot, "html.parser")
    el = soup.find(attrs={"data-al-id": al_id})
    if el is None:
        return None
    parent = el.parent if (el.parent is not None and el.parent.name not in ("[document]", "html")) else el
    body = soup.body.get_text(" ", strip=True) if soup.body else ""
    return {"element_html": clean_html(str(el))[:600], "parent_html": clean_html(str(parent))[:1000],
            "page_title": soup.title.get_text(strip=True) if soup.title else "", "page_text_sample": body[:400]}


def build_batch_prompt(entries: list) -> str:
    """entries: [(Finding, ctx, has_image)]"""
    items = []
    for f, ctx, has_image in entries:
        item = {"id": f.id, "category": f.category, "rule_id": f.rule_id, "wcag": f.wcag,
                "severity": f.severity, "axe_message": f.message[:300],
                "element_html": ctx["element_html"], "parent_html": ctx["parent_html"],
                "image_attached": has_image, "allowed_patch": FIELD_GUIDE[f.category]}
        if f.category == "language":
            item["page_text_sample"] = ctx["page_text_sample"]
            item["page_title"] = ctx["page_title"]
        items.append(item)
    return json.dumps({"findings": items}, ensure_ascii=False)


def parse_batch(raw: str) -> dict:
    """Parse the model's batch response into {finding_id: LLMOut}. Invalid items are simply omitted."""
    text = re.sub(r"^```(?:json)?|```$", "", raw.strip(), flags=re.M).strip()
    starts = [i for i in (text.find("{"), text.find("[")) if i != -1]
    if not starts:
        raise ValueError("no JSON in response")
    data, _ = json.JSONDecoder().raw_decode(text[min(starts):])
    items = data.get("items") if isinstance(data, dict) else data
    if not isinstance(items, list):
        raise ValueError("no items list in response")
    out = {}
    for it in items:
        if not isinstance(it, dict) or "id" not in it:
            continue
        try:
            out[str(it["id"])] = LLMOut.model_validate({k: v for k, v in it.items() if k != "id"})
        except Exception:
            continue
    return out


LANG_RE = re.compile(r"^[a-z]{2,3}(-[A-Za-z0-9]{2,8})*$")


def _extract_value(patch, attr: str):
    """Models don't always follow the exact shape; accept the common variants."""
    if isinstance(patch, str):
        return patch
    if isinstance(patch, dict):
        for k in ("value", attr, "alt", "aria-label", "aria_label", "lang", "label", "text"):
            if k in patch:
                return patch[k]
    return None


def _unwrap_attr(value: str, attr: str) -> str:
    """Models sometimes answer `alt="Home"` instead of `Home`: strip the attribute wrapper."""
    m = re.fullmatch(r"""\s*%s\s*=\s*(["'])(.*)\1\s*""" % re.escape(attr), value, re.S)
    return m.group(2).strip() if m else value


def try_patch(f: Finding, out: LLMOut):
    """Return (PatchOp or None, reason-if-rejected). The reason is shown to the user for transparency."""
    attr = PATCH_ATTR.get(f.category)
    if attr is None or out.patch is None:
        return None, ""
    value = _extract_value(out.patch, attr)
    if not isinstance(value, str):
        return None, f"patch had no usable value: {str(out.patch)[:80]}"
    value = _unwrap_attr(value.strip(), attr)
    if "<" in value:   # model returned an HTML snippet: pull out the attribute we asked for
        tag = BeautifulSoup(value, "html.parser").find(True)
        extracted = tag.get(attr) if tag is not None else None
        if not isinstance(extracted, str):
            return None, "value contained markup"
        value = _unwrap_attr(extracted.strip(), attr)
    if "<" in value or ">" in value:
        return None, "value contained markup"
    if len(value) > 150:
        return None, "value too long (>150 chars)"
    if attr == "lang" and not LANG_RE.match(value):
        return None, f"invalid language code: {value[:20]}"
    if attr != "alt" and not value:
        return None, "empty value not allowed for this attribute"
    try:
        return PatchOp(finding_id=f.id, al_id=f.al_id, op="set_attribute", name=attr,
                       value=value, explanation=out.explanation.how), ""
    except Exception as e:
        return None, f"patch rejected by validator: {str(e)[:80]}"


def validated_patch(f: Finding, out: LLMOut) -> Optional[PatchOp]:
    return try_patch(f, out)[0]


def _finish(f: Finding, snapshot: str, expl: Explanation, patch: Optional[PatchOp], source: str,
            confidence: str, review: bool, evidence: str, note: str) -> FindingAnalysis:
    original, proposed = preview_pair(snapshot, f.al_id, patch)
    return FindingAnalysis(finding_id=f.id, category=f.category, explanation=expl, patch=patch,
                           patch_source=source if patch else "none", confidence=confidence,
                           needs_human_review=review or patch is None, evidence=evidence,
                           original_html=original, proposed_html=proposed, note=note)


RETRY_PAUSE = float(os.environ.get("ACCESSLENS_RETRY_PAUSE", "6"))
RETRY_ROUNDS = 2


def _chunks(seq: list, n: int):
    for i in range(0, len(seq), n):
        yield seq[i:i + n]


async def analyze(scan: ScanResult, llm: LLMFn = default_call, max_findings: int = 80) -> AnalyzeResult:
    order = {"critical": 0, "serious": 1, "moderate": 2, "minor": 3}
    findings = sorted(scan.findings, key=lambda f: order[f.severity])
    snap = scan.html_snapshot

    rule_rep: dict[str, Finding] = {}
    elem: list[Finding] = []
    for f in findings:
        if f.category in RULE_LEVEL_CATEGORIES:
            rule_rep.setdefault(f.rule_id, f)
        elif f.category in LLM_PATCH_CATEGORIES:
            elem.append(f)
    over_budget = {f.id for f in elem[max_findings:]}
    elem = elem[:max_findings]

    entries, no_ctx = [], set()
    for f in list(rule_rep.values()) + elem:
        ctx = element_context(snap, f.al_id)
        if ctx is None:
            no_ctx.add(f.id)
            continue
        has_image = bool(f.category == "alt_text" and f.crop_path and pathlib.Path(f.crop_path).exists())
        entries.append((f, ctx, has_image))

    parsed: dict[str, LLMOut] = {}
    errors: dict[str, str] = {}
    sem = asyncio.Semaphore(int(os.environ.get("ACCESSLENS_CONCURRENCY", "2")))

    async def run_chunk(chunk) -> bool:
        """True if the call itself succeeded (individual items may still be missing)."""
        for f, _, _ in chunk:
            errors.pop(f.id, None)
        images = [(f.id, f.crop_path) for f, _, has_img in chunk if has_img]
        try:
            async with sem:
                raw = await llm(SYSTEM, build_batch_prompt(chunk), images)
            got = parse_batch(raw)
        except Exception as e:
            for f, _, _ in chunk:
                errors[f.id] = f"LLM unavailable: {repr(e)[:160]}"
            return False
        parsed.update(got)
        for f, _, _ in chunk:
            if f.id not in got:
                errors[f.id] = "Model omitted or returned an invalid result for this finding"
        return True

    async def process(chunks):
        results = await asyncio.gather(*(run_chunk(c) for c in chunks))
        return [c for c, ok in zip(chunks, results) if not ok]

    with_img = [e for e in entries if e[2]]
    without_img = [e for e in entries if not e[2]]
    pending = await process(list(_chunks(with_img, 5)) + list(_chunks(without_img, 8)))
    for _ in range(RETRY_ROUNDS):          # second pass: pause, split failed batches, retry
        if not pending:
            break
        await asyncio.sleep(RETRY_PAUSE)
        smaller = []
        for c in pending:
            if len(c) > 1:
                mid = len(c) // 2
                smaller += [c[:mid], c[mid:]]
            else:
                smaller.append(c)
        pending = await process(smaller)

    analyses = []
    for f in findings:
        if f.category in RULE_LEVEL_CATEGORIES:
            rep = rule_rep[f.rule_id]
            out, err = parsed.get(rep.id), errors.get(rep.id, "")
            expl = out.explanation if out else FALLBACK[f.category]
            ev = out.evidence if out else ""
            if f.category == "contrast":
                p = contrast_patch(f)
                analyses.append(_finish(f, snap, expl, p, "deterministic", "high", p is None,
                                        ev or "WCAG contrast ratio computed from axe-reported colours",
                                        err or ("" if p else "Could not compute a passing colour")))
            else:
                analyses.append(_finish(f, snap, expl, None, "none", "medium", True, ev,
                                        err or "Heading fixes change meaning; human review required"))
            continue
        if f.id in over_budget:
            analyses.append(_finish(f, snap, FALLBACK[f.category], None, "none", "low", True, "",
                                    "Skipped: finding limit reached"))
        elif f.id in no_ctx:
            analyses.append(_finish(f, snap, FALLBACK[f.category], None, "none", "low", True, "",
                                    "Element not found in snapshot"))
        elif f.id in parsed:
            out = parsed[f.id]
            patch, why = try_patch(f, out)
            note = why or ("" if patch or out.patch is not None else "Model found insufficient evidence for a fix")
            analyses.append(_finish(f, snap, out.explanation, patch, "llm", out.confidence,
                                    out.needs_human_review or out.confidence == "low", out.evidence, note))
        else:
            analyses.append(_finish(f, snap, FALLBACK[f.category], None, "none", "low", True, "",
                                    errors.get(f.id, "No LLM result")))
    return AnalyzeResult(scan_id=scan.scan_id, analyses=analyses)
