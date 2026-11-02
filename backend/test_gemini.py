import json
import urllib.error
import urllib.request
from dotenv import dotenv_values

v = dotenv_values(".env")
print("entries in .env (name: value length):", {k: len(x or "") for k, x in v.items()})
key = (v.get("GEMINI_API_KEY") or "").strip()
if not key:
    raise SystemExit("GEMINI_API_KEY is missing or empty in .env")

req = urllib.request.Request(
    "https://generativelanguage.googleapis.com/v1beta/models?pageSize=200",
    headers={"x-goog-api-key": key})
try:
    with urllib.request.urlopen(req, timeout=20) as r:
        data = json.load(r)
    print("KEY OK. Flash models that support generateContent:")
    for m in data.get("models", []):
        if "generateContent" in m.get("supportedGenerationMethods", []) and "flash" in m["name"]:
            print("  ", m["name"])
except urllib.error.HTTPError as e:
    print("HTTP", e.code, e.read().decode()[:300])