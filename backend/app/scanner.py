import os
import re
import uuid
import pathlib
from playwright.async_api import async_playwright
from .security import validate_url
from .schemas import Finding, ScanResult

AXE = (pathlib.Path(__file__).parent / "axe.min.js").read_text(encoding="utf-8")
OUT = pathlib.Path("scans")
OUT.mkdir(exist_ok=True)
# In a container the OS sandbox usually can't start; the container itself is the isolation boundary.
LAUNCH_ARGS = ["--no-sandbox", "--disable-dev-shm-usage"] if os.environ.get("ACCESSLENS_NO_SANDBOX") else []
if os.environ.get("ACCESSLENS_LOW_MEMORY"):   # for 512 MB hosts: fewer Chromium processes, no GPU/extension overhead
    LAUNCH_ARGS += ["--disable-gpu", "--disable-extensions", "--disable-background-networking",
                    "--disable-features=site-per-process,TranslateUI", "--renderer-process-limit=1",
                    "--js-flags=--max-old-space-size=192"]
NAV_TIMEOUT_MS = int(float(os.environ.get("ACCESSLENS_NAV_TIMEOUT_S", "20")) * 1000)   # raise on slow hosts

RULES = {  # axe rule id -> our category
    "image-alt": "alt_text", "label": "form_label", "select-name": "form_label",
    "color-contrast": "contrast", "button-name": "empty_name", "link-name": "empty_name",
    "heading-order": "heading", "empty-heading": "heading", "page-has-heading-one": "heading",
    "html-has-lang": "language", "html-lang-valid": "language",
}
WCAG = {"alt_text": ["1.1.1"], "form_label": ["1.3.1", "4.1.2"], "contrast": ["1.4.3"],
        "empty_name": ["4.1.2"], "heading": ["1.3.1", "2.4.6"], "language": ["3.1.1"]}
TAG_JS = """() => { let i = 0; document.querySelectorAll('*').forEach(e => e.setAttribute('data-al-id', 'al' + (i++))); }"""


async def run_axe(page):
    if not await page.evaluate("typeof axe !== 'undefined'"):
        await page.evaluate(AXE)
    return await page.evaluate(
        "async () => await axe.run(document, {runOnly:{type:'rule', values:%s}})" % list(RULES))


def _al_id(html: str) -> str:
    m = re.search(r'data-al-id="(al\d+)"', html)
    return m.group(1) if m else "unknown"


def findings_from_axe(results) -> list[Finding]:
    findings = []
    for v in results["violations"]:
        cat = RULES[v["id"]]
        for n in v["nodes"]:
            snip = n["html"][:500]
            al = _al_id(snip)
            findings.append(Finding(
                id=f'{v["id"]}:{al}', rule_id=v["id"], category=cat,
                severity=v.get("impact") or "moderate", wcag=WCAG[cat],
                selector=" ".join(str(t) for t in n["target"]), al_id=al, html=snip,
                message=n.get("failureSummary", "")[:400], help_url=v["helpUrl"]))
    return findings


async def scan(url: str) -> ScanResult:
    validate_url(url)
    scan_id = uuid.uuid4().hex[:8]
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(args=LAUNCH_ARGS)
        ctx = await browser.new_context(viewport={"width": 1280, "height": 800})
        page = await ctx.new_page()

        async def guard(route):
            try:
                validate_url(route.request.url)
                await route.continue_()
            except ValueError:
                await route.abort()
        await page.route("**/*", guard)

        await page.goto(url, wait_until="load", timeout=NAV_TIMEOUT_MS)
        await page.evaluate(TAG_JS)
        results = await run_axe(page)
        shot = OUT / f"{scan_id}.png"
        await page.screenshot(path=str(shot))
        final_url = page.url
        findings = findings_from_axe(results)
        for f in findings[:80]:   # positions for the on-screenshot overlay (must precede element crops)
            try:
                bb = await page.locator(f'[data-al-id="{f.al_id}"]').first.bounding_box(timeout=1500)
                if bb and bb["width"] > 0 and bb["height"] > 0 and bb["y"] < 800 and bb["x"] < 1280:
                    f.bbox = {"x": bb["x"], "y": bb["y"], "w": bb["width"], "h": bb["height"]}
            except Exception:
                pass
        n_crops = 0
        for f in findings:   # element crops let a vision model actually see the image
            if f.rule_id == "image-alt" and n_crops < 12:
                crop = OUT / f"{scan_id}_{f.al_id}.png"
                try:
                    await page.locator(f'[data-al-id="{f.al_id}"]').first.screenshot(
                        path=str(crop), timeout=3000)
                    f.crop_path = str(crop)
                    n_crops += 1
                except Exception:
                    pass
        html = await page.content()
        await browser.close()
    return ScanResult(scan_id=scan_id, url=url, findings=findings,
                      screenshot_path=str(shot), html_snapshot=html, final_url=final_url)
