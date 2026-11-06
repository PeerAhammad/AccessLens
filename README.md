---
title: AccessLens
emoji: 🔎
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
---

# AccessLens (backend: scan, analyze, verify)

Scan -> Detect -> Explain -> Fix -> Verify.

## Setup (Windows PowerShell)
    .\setup.ps1
or manually:
    cd backend
    python -m venv .venv
    .\.venv\Scripts\Activate.ps1
    pip install -r requirements.txt
    playwright install chromium

## Run
    uvicorn app.main:app          # no --reload on Windows (Playwright needs the default event loop)

## Tests
    python -m pytest -q                      # offline unit tests
    python run_verify.py                     # real scan + patch + verify (needs internet + Chromium)
    python run_verify.py https://example.com
    $env:ANTHROPIC_API_KEY = "sk-ant-..."   # never commit this
    python run_day3.py                       # scan + LLM analysis + verify (auto-approves, testing only)

## API
- POST /scan    {"url": "..."}                       -> ScanResult (findings + html snapshot)
- GET  /scan/{id}
- POST /analyze {"scan_id": "..."}                    -> explanations + proposed patches + before/after HTML
- POST /verify  {"scan_id": "...", "patches": [...]} -> VerifyResult (resolved / remaining / introduced)

## Security notes
- SSRF: DNS resolution check + per-request route guard (blocks private/loopback/link-local).
  Known gap: DNS rebinding between check and connect.
- Patches are allowlisted PatchOp objects (attrs: alt, lang, aria-label, title, role, for, id;
  styles: color/background-color hex only) and may only target elements axe flagged.
- Verification runs on a sanitized snapshot (scripts, iframes, inline handlers removed).

## LLM notes
- Provider auto-selected: Gemini if GEMINI_API_KEY is set (default model gemini-3.8-flash), else Anthropic (ANTHROPIC_API_KEY).
- Override with ACCESSLENS_PROVIDER / ACCESSLENS_MODEL. Put keys in backend/.env (copy .env.example); it is git-ignored.
- The LLM never picks the target element or attribute; contrast fixes are computed, not generated; headings are explain-only.

## Frontend (React + TypeScript + Tailwind + Recharts)
Needs Node 18+.

    cd frontend
    npm install
    npm run dev          # http://localhost:5173   (backend must be running on :8000)

Point it at a deployed backend with `frontend/.env.local`:  `VITE_API_URL=https://your-backend`

Flow: enter URL -> scan -> AI analysis -> review issues (screenshot highlights, explanation, original vs proposed code,
editable text) -> approve -> Apply & verify -> before/after report (downloadable JSON).

## Deployment (single Docker container: API + built React app)
`Dockerfile` builds the frontend, installs Chromium, and serves everything from one URL on port 7860 (or $PORT).

Environment variables (set as secrets in the host, never in git):
- `GEMINI_API_KEY` (required for AI fixes; without it the app still scans and shows fallback explanations)
- `ACCESSLENS_MODEL` (optional), `ACCESSLENS_RATE_PER_HOUR` (default 30 per IP), `ACCESSLENS_MAX_BROWSERS` (default 2)

### Hugging Face Spaces (free, 16 GB RAM)
1. Create a Space: SDK = Docker, blank template.
2. Space -> Settings -> Variables and secrets -> new secret `GEMINI_API_KEY`.
3. Push this repo to the Space (`git remote add space https://huggingface.co/spaces/<user>/accesslens; git push space main`).
   Use a Hugging Face write token as the password. The first build takes several minutes.

### Render / Railway / Fly.io
Create a web service from the repo using the Dockerfile and set the same variables. Chromium needs about 1 GB RAM,
so Render's free 512 MB tier is too small.

## Known limitations
- Axe-core verifies rule violations disappear; it cannot judge whether AI-written text is good. Humans approve and can edit every change.
- Not a WCAG compliance certificate: automated tools find only a portion of real accessibility barriers.
- Chromium runs with `--no-sandbox` inside the container (the container is the isolation boundary).
- SSRF guard resolves DNS then connects (DNS-rebinding gap); scans and results are held in memory and lost on restart.
- Scans a single page with scripts enabled; verification runs on a script-free snapshot, so JS-driven UI states are not covered.

## Static demo (free hosting, no server)
A free static host cannot run Chromium, so `npm run build:demo` produces a backend-free site that replays a REAL recorded run
(scan + AI analysis + verification) of the W3C "before" demo page. The page labels itself as a recording.

    cd backend
    python export_demo.py            # records the run into frontend/public/demo (uses the analysis cache; verification runs live)
    cd ../frontend
    npm run build:demo               # output in frontend/dist (relative paths; any static host)

Host `frontend/dist` on a Hugging Face *Static* Space, Netlify Drop, or GitHub Pages. The live app (scan any URL) is the Docker image.

## Theme and accessibility of the app itself
Light theme by default with a dark-mode toggle (preference stored in the browser). The interface was spot-checked with axe-core
(WCAG 2.0/2.1 A and AA rules, including colour contrast) on the landing, review and report pages in both themes using sample data:
no violations. This is an automated check only; it is not a full accessibility audit.

### Render free tier (512 MB)
Web Service -> Docker -> instance type Free -> health check path `/health`. Environment variables:
`GEMINI_API_KEY` (secret), `ACCESSLENS_MODEL=gemini-3.1-flash-lite`, `ACCESSLENS_FALLBACK_MODELS=gemini-3.8-flash,gemini-3.7-flash,gemini-3.6-flash`,
`ACCESSLENS_MAX_BROWSERS=1`, `ACCESSLENS_LOW_MEMORY=1`, `ACCESSLENS_NAV_TIMEOUT_S=45`, `ACCESSLENS_RATE_PER_HOUR=20`.
The free instance sleeps after ~15 minutes idle (first request then takes ~1 minute) and may run out of memory on heavy pages.
