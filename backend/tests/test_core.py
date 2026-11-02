import pytest
from app.fixes import fix_color, ratio, contrast_patch, _h2r
from app.patches import PatchOp
from app.schemas import Finding
from app.security import validate_url
from app.verify import sanitize


def test_fix_color_reaches_target():
    new = fix_color("#41545d", "#a9b8bf", 4.5)
    assert new is not None
    assert ratio(_h2r(new), _h2r("#a9b8bf")) >= 4.5


def test_contrast_patch_from_axe_message():
    f = Finding(id="color-contrast:al231", rule_id="color-contrast", category="contrast",
                severity="serious", wcag=["1.4.3"], selector="b", al_id="al231", html="<b>x</b>",
                message="Fix any of the following:\n  Element has insufficient color contrast of 3.88 "
                        "(foreground color: #41545d, background color: #a9b8bf, font size: 9.8pt (13px), "
                        "font weight: bold). Expected contrast ratio of 4.5:1", help_url="x")
    p = contrast_patch(f)
    assert p is not None and p.op == "add_style"


@pytest.mark.parametrize("kwargs", [
    dict(al_id="x1", op="set_attribute", name="alt", value="a"),
    dict(al_id="al1", op="set_attribute", name="onclick", value="alert(1)"),
    dict(al_id="al1", op="add_style", value="background:url(http://evil)"),
    dict(al_id="al1", op="set_text", value="a" * 301),
])
def test_patch_rejects_unsafe(kwargs):
    with pytest.raises(Exception):
        PatchOp(finding_id="f", **kwargs)


def test_patch_accepts_valid():
    PatchOp(finding_id="f", al_id="al5", op="set_attribute", name="alt", value="Logo")
    PatchOp(finding_id="f", al_id="al5", op="add_style", value="color: #112233")


@pytest.mark.parametrize("url", ["http://127.0.0.1", "http://localhost:8000",
                                 "http://169.254.169.254/latest/meta-data", "file:///etc/passwd",
                                 "ftp://example.com", "http://10.0.0.1"])
def test_ssrf_blocked(url):
    with pytest.raises(ValueError):
        validate_url(url)


def test_sanitize_strips_scripts_and_handlers():
    html = '<html><head></head><body><script>x()</script><img src=a onerror="y()" data-al-id="al1"></body></html>'
    out = sanitize(html, "https://example.com/")
    assert "<script" not in out and "onerror" not in out
    assert 'data-al-id="al1"' in out and '<base href="https://example.com/"' in out
