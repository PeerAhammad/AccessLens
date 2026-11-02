"""Scan -> analyze (LLM) -> verify with ALL generated patches (auto-approve, for testing only).
Needs:  $env:ANTHROPIC_API_KEY = "sk-ant-..."     Usage: python run_day3.py [url]
"""
import asyncio
import sys
from app.scanner import scan
from app.llm import analyze
from app.verify import verify

URL = sys.argv[1] if len(sys.argv) > 1 else "https://www.w3.org/WAI/demos/bad/before/home.html"


async def main():
    s = await scan(URL)
    print(f"Scan found {len(s.findings)} findings")
    res = await analyze(s)
    patches = [a.patch for a in res.analyses if a.patch]
    print(f"{len(patches)} patches proposed, {sum(a.needs_human_review for a in res.analyses)} flagged for review\n")
    for a in [x for x in res.analyses if x.category != 'contrast'][:12]:
        print(f"[{a.category}] {a.finding_id}  src={a.patch_source} conf={a.confidence} review={a.needs_human_review}")
        print("   what:", a.explanation.what)
        if a.patch:
            print("   before:", (a.original_html or "")[:110])
            print("   after: ", (a.proposed_html or "")[:110])
        if a.note:
            print("   note:  ", a.note)
    from collections import Counter
    print("\nnotes summary:", dict(Counter(a.note[:60] or "ok" for a in res.analyses)))
    r = await verify(s, patches)
    print(f"\nbefore={r.before_count} after={r.after_count}")
    print(f"resolved={len(r.resolved)} remaining={len(r.remaining)} introduced={len(r.introduced)} failed_ops={r.failed_ops}")
    print("remaining:", r.remaining)
    print("introduced:", r.introduced)


if __name__ == "__main__":
    asyncio.run(main())
