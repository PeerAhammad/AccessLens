import asyncio
import json
from app.llm import analyze, parse_batch, element_context
from app.schemas import Finding, ScanResult
from app.patches import preview_pair

HTML = ('<html data-al-id="al0"><head data-al-id="al1"><title data-al-id="al2">Shop</title></head>'
        '<body data-al-id="al3"><p data-al-id="al4" style="color:#999;background:#aaa">Welcome to the shop today</p>'
        '<a data-al-id="al5" href="/cart"><img data-al-id="al6" src="cart.png"></a>'
        '<input data-al-id="al7" name="email" placeholder="Your email">'
        '<h4 data-al-id="al8">Skipped</h4></body></html>')


def F(rule, cat, al, msg="x", sev="serious"):
    return Finding(id=f"{rule}:{al}", rule_id=rule, category=cat, severity=sev, wcag=["1.1.1"],
                   selector="s", al_id=al, html="<x>", message=msg, help_url="u")


CONTRAST_MSG = ("Element has insufficient color contrast of 2.0 (foreground color: #999999, "
                "background color: #aaaaaa, font size: 12pt). Expected contrast ratio of 4.5:1")
SCAN = ScanResult(scan_id="t1", url="https://x.test", html_snapshot=HTML, findings=[
    F("html-has-lang", "language", "al0"), F("color-contrast", "contrast", "al4", CONTRAST_MSG),
    F("image-alt", "alt_text", "al6", sev="critical"), F("label", "form_label", "al7"),
    F("heading-order", "heading", "al8", sev="moderate")])


def reply(value, conf="high", review=False):
    return json.dumps({"explanation": {"what": "w", "why": "y", "who": "u", "how": "h"},
                       "patch": None if value is None else {"value": value},
                       "confidence": conf, "needs_human_review": review, "evidence": "e"})


def fake_llm(by_cat, calls=None):
    """by_cat: category -> JSON string for one item (without id). Responds in batch format."""
    async def llm(system, user, images):
        if calls is not None:
            calls.append(user)
        d = json.loads(user)
        items = []
        for f in d["findings"]:
            item = json.loads(by_cat.get(f["category"], reply(None)))
            item["id"] = f["id"]
            items.append(item)
        return json.dumps({"items": items})
    return llm


def run(llm, scan=SCAN):
    return {a.finding_id: a for a in asyncio.run(analyze(scan, llm)).analyses}


def test_happy_path_forces_target_and_attribute():
    out = run(fake_llm({"alt_text": reply("Shopping cart icon"), "form_label": reply("Email address"),
                        "language": reply("en")}))
    a = out["image-alt:al6"]
    assert a.patch.al_id == "al6" and a.patch.name == "alt" and a.patch.value == "Shopping cart icon"
    assert 'alt="Shopping cart icon"' in a.proposed_html and "data-al-id" not in a.proposed_html
    assert out["label:al7"].patch.name == "aria-label"
    assert out["html-has-lang:al0"].patch.value == "en"
    assert out["html-has-lang:al0"].proposed_html.startswith('<html lang="en"')


def test_all_findings_batched_into_one_call():
    calls = []
    run(fake_llm({}, calls))
    assert len(calls) == 1


def test_contrast_is_deterministic_and_heading_has_no_patch():
    out = run(fake_llm({}))
    c = out["color-contrast:al4"]
    assert c.patch_source == "deterministic" and c.patch.op == "add_style"
    h = out["heading-order:al8"]
    assert h.patch is None and h.needs_human_review


def test_bad_items_are_rejected_individually():
    out = run(fake_llm({"alt_text": reply("<script>alert(1)</script>"), "form_label": '{"bad": true}',
                        "language": reply("english please")}))
    assert out["image-alt:al6"].patch is None
    assert out["label:al7"].patch is None and out["label:al7"].needs_human_review
    assert "omitted" in out["label:al7"].note
    assert out["html-has-lang:al0"].patch is None


def test_llm_exception_falls_back_gracefully():
    async def boom(*a):
        raise RuntimeError("no key")
    out = run(boom)
    assert all(a.explanation.what for a in out.values())
    assert out["color-contrast:al4"].patch is not None      # deterministic still works
    assert out["image-alt:al6"].patch is None and "LLM unavailable" in out["image-alt:al6"].note


def test_low_confidence_flagged_and_decorative_allowed():
    out = run(fake_llm({"alt_text": reply("", conf="low")}))
    a = out["image-alt:al6"]
    assert a.patch is not None and a.patch.value == "" and a.needs_human_review


def test_alternate_patch_shapes_are_accepted():
    for shape in ({"alt": "Shopping cart"}, "Shopping cart", {"value": "Shopping cart"},
                  {"value": '<img alt="Shopping cart">'}, {"value": 'alt="Shopping cart"'}):
        body = json.loads(reply("x")); body["patch"] = shape
        out = run(fake_llm({"alt_text": json.dumps(body)}))
        assert out["image-alt:al6"].patch.value == "Shopping cart", shape


def test_rejection_reason_is_reported():
    body = json.loads(reply("x")); body["patch"] = {"foo": 1}
    a = run(fake_llm({"alt_text": json.dumps(body)}))["image-alt:al6"]
    assert a.patch is None and "no usable value" in a.note


def test_parse_batch_tolerates_fences_and_bare_list():
    item = {"id": "a", "explanation": {"what": "w", "why": "y", "who": "u", "how": "h"}}
    assert "a" in parse_batch("```json\n" + json.dumps({"items": [item]}) + "\n```")
    assert "a" in parse_batch(json.dumps([item]))


def test_context_and_preview():
    ctx = element_context(HTML, "al6")
    assert "data-al-id" not in ctx["parent_html"] and "/cart" in ctx["parent_html"]
    assert element_context(HTML, "al99") is None
    assert preview_pair(HTML, "al99", None) == (None, None)


def test_attribute_wrapper_is_unwrapped():
    out = run(fake_llm({"alt_text": json.dumps({**json.loads(reply("x")), "patch": {"value": 'alt=""'}}),
                        "empty_name": reply("x")}))
    assert out["image-alt:al6"].patch.value == ""


def test_failed_batch_is_retried_and_split():
    import app.llm as m
    m.RETRY_PAUSE = 0
    state = {"n": 0}
    inner = fake_llm({"alt_text": reply("Cart"), "form_label": reply("Email"), "language": reply("en")})

    async def flaky(system, user, images):
        state["n"] += 1
        if state["n"] == 1:
            raise RuntimeError("503 UNAVAILABLE")
        return await inner(system, user, images)
    out = run(flaky)
    assert state["n"] >= 3                       # first call failed, then two halves
    assert out["image-alt:al6"].patch.value == "Cart" and out["label:al7"].patch.value == "Email"
