from evaluate import summarize, to_markdown

OK = dict(url="https://a.test", findings=10, proposed=8, approved=6, resolved=7, approved_resolved=6,
          remaining=3, introduced=0, failed_ops=0, scan_s=2.0, analyze_s=10.0, verify_s=3.0, error="")
BAD = dict(url="https://b.test", error="TimeoutError()")


def test_summary_ignores_failed_sites_and_computes_rates():
    s = summarize([OK, BAD])
    assert s["sites_ok"] == 1 and s["sites_failed"] == 1
    assert s["resolved_pct"] == 70.0 and s["approved_fix_success_pct"] == 100.0 and s["avg_total_s"] == 15.0


def test_empty_run_does_not_crash():
    s = summarize([BAD])
    assert s["resolved_pct"] is None
    assert "scan failed" in to_markdown([BAD], s, "meta")


def test_markdown_contains_row_and_totals():
    md = to_markdown([OK], summarize([OK]), "meta")
    assert "https://a.test" in md and "70.0%" in md
