from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
from .scanner import run_axe, findings_from_axe, OUT, LAUNCH_ARGS
from .security import validate_url
from .patches import PatchOp
from .schemas import ScanResult, VerifyResult


def sanitize(html: str, base_url: str) -> str:
    """Strip scripts/embeds/inline handlers so the untrusted snapshot is inert."""
    soup = BeautifulSoup(html, "html.parser")
    for t in soup(["script", "iframe", "object", "embed"]):
        t.decompose()
    for el in soup.find_all(True):
        for a in list(el.attrs):
            if a.lower().startswith("on"):
                del el.attrs[a]
    if soup.head is not None:
        soup.head.insert(0, soup.new_tag("base", href=base_url))
    return str(soup)


APPLY_JS = """(ops) => {
  const failed = [];
  for (const o of ops) {
    const el = document.querySelector('[data-al-id="' + o.al_id + '"]');
    if (!el) { failed.push(o.al_id); continue; }
    if (o.op === 'set_attribute') el.setAttribute(o.name, o.value);
    else if (o.op === 'set_text') el.textContent = o.value;
    else if (o.op === 'add_style') {
      const [p, v] = o.value.replace(/;\\s*$/, '').split(':');
      el.style.setProperty(p.trim(), v.trim(), 'important');
    }
  }
  return failed;
}"""


async def verify(scan: ScanResult, patches: list[PatchOp]) -> VerifyResult:
    html = sanitize(scan.html_snapshot, scan.url)
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(args=LAUNCH_ARGS)
        ctx = await browser.new_context(viewport={"width": 1280, "height": 800})
        page = await ctx.new_page()

        async def guard(route):
            u = route.request.url
            if u.startswith("data:") or u.startswith("about:"):
                return await route.continue_()
            try:
                validate_url(u)
                await route.continue_()
            except ValueError:
                await route.abort()
        await page.route("**/*", guard)

        await page.set_content(html, wait_until="load", timeout=20000)
        before = findings_from_axe(await run_axe(page))
        b_shot = OUT / f"{scan.scan_id}_before.png"
        await page.screenshot(path=str(b_shot))

        failed = await page.evaluate(APPLY_JS, [p.model_dump() for p in patches])
        after = findings_from_axe(await run_axe(page))
        a_shot = OUT / f"{scan.scan_id}_after.png"
        await page.screenshot(path=str(a_shot))
        await browser.close()

    b, a = {f.id for f in before}, {f.id for f in after}
    return VerifyResult(
        scan_id=scan.scan_id, before_count=len(b), after_count=len(a),
        resolved=sorted(b - a), remaining=sorted(b & a), introduced=sorted(a - b),
        failed_ops=failed, before_screenshot=str(b_shot), after_screenshot=str(a_shot))
