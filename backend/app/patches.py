import re
from typing import Literal, Optional
from bs4 import BeautifulSoup
from pydantic import BaseModel, model_validator

ALLOWED_ATTRS = {"alt", "lang", "aria-label", "title", "role", "for", "id"}
STYLE_RE = re.compile(r"^(color|background-color)\s*:\s*#[0-9a-fA-F]{6}\s*;?$")


class PatchOp(BaseModel):
    """A single, validated modification. The only way an LLM may change the page."""
    finding_id: str
    al_id: str
    op: Literal["set_attribute", "set_text", "add_style"]
    name: Optional[str] = None      # attribute name for set_attribute
    value: str
    explanation: str = ""

    @model_validator(mode="after")
    def validate_op(self):
        if not re.fullmatch(r"al\d+", self.al_id):
            raise ValueError("invalid al_id")
        if len(self.value) > 300:
            raise ValueError("value too long")
        if self.op == "set_attribute" and self.name not in ALLOWED_ATTRS:
            raise ValueError(f"attribute not allowed: {self.name}")
        if self.op == "add_style" and not STYLE_RE.match(self.value):
            raise ValueError("only color/background-color hex styles allowed")
        return self


_AL_ATTR = re.compile(r'\s*data-al-id="al\d+"')


def clean_html(s: str) -> str:
    """Remove our internal data-al-id tags from anything shown to users or the LLM."""
    return _AL_ATTR.sub("", s)


def _open_tag(el) -> str:
    attrs = "".join(f' {k}="{v if isinstance(v, str) else " ".join(v)}"'
                    for k, v in el.attrs.items() if k != "data-al-id")
    return f"<{el.name}{attrs}>"


def _show(el) -> str:
    return _open_tag(el) if el.name in ("html", "body") else clean_html(str(el))


def preview_pair(snapshot: str, al_id: str, patch: Optional[PatchOp]):
    """Return (original_html, proposed_html) for one element, for the diff view."""
    soup = BeautifulSoup(snapshot, "html.parser")
    el = soup.find(attrs={"data-al-id": al_id})
    if el is None:
        return None, None
    original = _show(el)[:800]
    if patch is None:
        return original, None
    if patch.op == "set_attribute":
        el[patch.name] = patch.value
    elif patch.op == "set_text":
        el.string = patch.value
    elif patch.op == "add_style":
        prop, val = [x.strip() for x in patch.value.rstrip(";").split(":", 1)]
        old = (el.get("style") or "").strip().rstrip(";")
        el["style"] = (old + "; " if old else "") + f"{prop}: {val}"
    return original, _show(el)[:800]
