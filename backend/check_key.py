import os
import pathlib
from dotenv import dotenv_values

raw = pathlib.Path(".env").read_bytes()
print("file bytes:", len(raw), "| BOM:", raw[:3] == b"\xef\xbb\xbf", "| UTF-16:", raw[:2] in (b"\xff\xfe", b"\xfe\xff"))

def describe(v):
    if not v:
        return "not set"
    flags = []
    if v != v.strip(): flags.append("LEADING/TRAILING SPACE")
    if any(c in v for c in "\"'"): flags.append("HAS QUOTES")
    if " " in v.strip(): flags.append("HAS INNER SPACE")
    if not v.isascii(): flags.append("NON-ASCII")
    return f"len={len(v)} starts={v[:4]!r} {' '.join(flags) or 'looks clean'}"

vals = dotenv_values(".env")
for name in ("GEMINI_API_KEY", "GOOGLE_API_KEY"):
    print(f"{name}: .env -> {describe(vals.get(name))} | window env var -> {describe(os.environ.get(name))}")

key = (vals.get("GEMINI_API_KEY") or "").strip().strip("\"'")
if key:
    try:
        from google import genai
        next(iter(genai.Client(api_key=key).models.list()))
        print("RESULT: key from .env is VALID")
    except Exception as e:
        print("RESULT: key from .env FAILED:", str(e)[:120])