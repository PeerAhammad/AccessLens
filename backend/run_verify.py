"""End-to-end test of scan -> patch -> verify, no server and no LLM.
Usage (from backend/, venv active):  python run_verify.py [url]
"""
import asyncio
import sys
from app.scanner import scan
from app.verify import verify
from app.patches import PatchOp
from app.fixes import contrast_patch

URL = sys.argv[1] if len(sys.argv) > 1 else "https://www.w3.org/WAI/demos/bad/before/home.html"


async def main():
    s = await scan(URL)
    print(f"Scan found {len(s.findings)} findings")
    patches = []
    for f in s.findings:
        if f.category == "contrast":
            p = contrast_patch(f)
            if p:
                patches.append(p)
        elif f.rule_id == "html-has-lang":
            patches.append(PatchOp(finding_id=f.id, al_id=f.al_id, op="set_attribute",
                                   name="lang", value="en", explanation="Declare page language"))
        elif f.rule_id == "image-alt":
            # TEST ONLY: decorative assumption. Day 3 replaces this with LLM/vision output.
            patches.append(PatchOp(finding_id=f.id, al_id=f.al_id, op="set_attribute",
                                   name="alt", value="", explanation="Mark as decorative"))
    print(f"Applying {len(patches)} patches")
    r = await verify(s, patches)
    print(f"before={r.before_count} after={r.after_count}")
    print(f"resolved={len(r.resolved)} remaining={len(r.remaining)} introduced={len(r.introduced)}")
    print("remaining:", r.remaining)
    print("introduced:", r.introduced)
    print("failed_ops:", r.failed_ops)


if __name__ == "__main__":
    asyncio.run(main())
