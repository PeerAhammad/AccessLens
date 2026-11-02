"""Deterministic fixes (no LLM): contrast correction."""
import re
from typing import Optional
from .patches import PatchOp
from .schemas import Finding


def _lin(c: float) -> float:
    c /= 255
    return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4


def _lum(rgb) -> float:
    r, g, b = rgb
    return 0.2126 * _lin(r) + 0.7152 * _lin(g) + 0.0722 * _lin(b)


def ratio(a, b) -> float:
    la, lb = _lum(a), _lum(b)
    return (max(la, lb) + 0.05) / (min(la, lb) + 0.05)


def _h2r(h: str):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _r2h(rgb) -> str:
    return "#%02x%02x%02x" % tuple(rgb)


def fix_color(fg_hex: str, bg_hex: str, target: float) -> Optional[str]:
    """Smallest shift of fg toward black or white that reaches the target ratio."""
    fg, bg = _h2r(fg_hex), _h2r(bg_hex)
    best = None
    for end in ((0, 0, 0), (255, 255, 255)):
        for step in range(101):
            t = step / 100
            c = tuple(round(fg[i] + (end[i] - fg[i]) * t) for i in range(3))
            if ratio(c, bg) >= target + 0.05:
                if best is None or step < best[0]:
                    best = (step, c)
                break
    return _r2h(best[1]) if best else None


CONTRAST_RE = re.compile(
    r"foreground color: (#[0-9a-fA-F]{6}), background color: (#[0-9a-fA-F]{6}).*?"
    r"Expected contrast ratio of ([\d.]+):1", re.S)


def contrast_patch(f: Finding) -> Optional[PatchOp]:
    m = CONTRAST_RE.search(f.message)
    if not m:
        return None
    fg, bg, target = m.group(1), m.group(2), float(m.group(3))
    new = fix_color(fg, bg, target)
    if not new:
        return None
    return PatchOp(
        finding_id=f.id, al_id=f.al_id, op="add_style", value=f"color: {new}",
        explanation=f"Changed text color {fg} to {new} on background {bg} "
                    f"to reach the required {target}:1 contrast ratio.")
