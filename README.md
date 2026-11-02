---

title: AccessLens
emoji: 🔎
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
pinned: false
-------------

# AccessLens

### AI-Powered Website Accessibility Analysis & Remediation

**Scan. Detect. Explain. Fix. Verify.**

AccessLens is an AI-assisted web accessibility tool that identifies WCAG-related issues, explains their impact, proposes targeted improvements, and verifies whether approved fixes resolve the detected violations.

It combines automated accessibility testing with AI-generated explanations and constrained remediation, keeping human review at the center of the process.

---

## Overview

Website accessibility issues can prevent users from navigating and understanding digital content. However, identifying violations is only the first step—developers also need actionable explanations and reliable ways to validate improvements.

AccessLens addresses this workflow through a structured pipeline:

1. **Scan** – Analyze a target webpage using Playwright and axe-core.
2. **Detect** – Identify accessibility violations and capture relevant page information.
3. **Explain** – Use an LLM to explain detected issues and their potential impact.
4. **Propose** – Generate constrained, element-specific remediation suggestions.
5. **Review** – Allow users to inspect, edit, and approve proposed changes.
6. **Verify** – Re-run accessibility checks and compare the results.

## Key Features

* **Automated Accessibility Scanning:** Detects accessibility violations using axe-core.
* **AI-Assisted Explanations:** Converts technical findings into understandable descriptions.
* **Targeted Fix Suggestions:** Proposes constrained changes for elements flagged by the scanner.
* **Visual Inspection:** Displays screenshots with highlighted accessibility findings.
* **Human-in-the-Loop Review:** Users can edit and approve proposed changes before application.
* **Automated Verification:** Rechecks the modified snapshot to identify resolved, remaining, and newly introduced issues.
* **Downloadable Reports:** Provides before-and-after results in JSON format.
* **Security Controls:** Includes URL validation, network request restrictions, and allowlisted patch operations.

## Architecture

```text
             Target Website URL
                     |
                     v
             Playwright Scanner
                     |
                     v
              axe-core Engine
                     |
                     v
          Accessibility Findings
                     |
          +----------+----------+
          |                     |
          v                     v
    Page Screenshot       HTML Snapshot
          |                     |
          +----------+----------+
                     |
                     v
              AI Analysis
                     |
                     v
          Explanations & Proposed
               Remediations
                     |
                     v
              Human Review
                     |
                     v
          Approved Patch Operations
                     |
                     v
          Sanitized HTML Snapshot
                     |
                     v
           Accessibility Retest
                     |
                     v
          Before / After Report
```

## Technology Stack

| Component             | Technologies                 |
| --------------------- | ---------------------------- |
| Backend               | Python, FastAPI              |
| Browser Automation    | Playwright, Chromium         |
| Accessibility Testing | axe-core                     |
| AI Integration        | Google Gemini, Anthropic API |
| Frontend              | React, TypeScript            |
| Styling               | Tailwind CSS                 |
| Visualization         | Recharts                     |
| Deployment            | Docker                       |

## Project Structure

```text
AccessLens/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── scanner.py
│   │   ├── llm.py
│   │   ├── fixes.py
│   │   ├── patches.py
│   │   ├── security.py
│   │   ├── schemas.py
│   │   └── verify.py
│   ├── tests/
│   ├── requirements.txt
│   └── .env.example
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── App.tsx
│   │   └── api.ts
│   ├── package.json
│   └── vite.config.ts
│
├── Dockerfile
├── docker-compose.yml
├── setup.ps1
├── .gitignore
└── README.md
```

## Getting Started

### Prerequisites

* Python 3.10+
* Node.js 18+
* Chromium (installed through Playwright)
* Gemini or Anthropic API key for AI-assisted analysis

### 1. Clone the Repository

```bash
git clone https://github.com/PeerAhammad/AccessLens.git
cd AccessLens
```

### 2. Configure the Backend

On Windows PowerShell:

```powershell
.\setup.ps1
```

Alternatively, install manually:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
playwright install chromium
```

### 3. Configure Environment Variables

Copy `backend/.env.example` to `backend/.env` and configure your preferred AI provider.

Example:

```env
GEMINI_API_KEY=your_api_key
```

Alternatively, configure an Anthropic API key:

```env
ANTHROPIC_API_KEY=your_api_key
```

**Never commit API keys, credentials, or `.env` files to GitHub.**

### 4. Start the Backend

From the backend directory:

```powershell
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

On Windows, avoid `--reload` when running Playwright with its default event loop.

### 5. Start the Frontend

Open another terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open:

```text
http://localhost:5173
```

Ensure the backend is running on port `8000`.

## API Reference

| Method | Endpoint     | Description                                   |
| ------ | ------------ | --------------------------------------------- |
| POST   | `/scan`      | Scan a webpage for accessibility violations   |
| GET    | `/scan/{id}` | Retrieve an existing scan                     |
| POST   | `/analyze`   | Generate explanations and proposed fixes      |
| POST   | `/verify`    | Apply approved patches and verify the results |

### Example Requests

**Start a scan**

```json
{
  "url": "https://example.com"
}
```

**Verify approved patches**

```json
{
  "scan_id": "your_scan_id",
  "patches": []
}
```

## Testing

Run the automated test suite:

```powershell
cd backend
python -m pytest -q
```

For an end-to-end verification test:

```powershell
python run_verify.py
```

Or specify a target webpage:

```powershell
python run_verify.py https://example.com
```

For AI-assisted analysis:

```powershell
python run_day3.py
```

The AI-assisted test script automatically approves proposed changes and should be used only for testing.

## Security & Reliability

AccessLens incorporates several safeguards:

* **SSRF Protection:** DNS resolution checks and request-level route restrictions block private, loopback, and link-local destinations.
* **Constrained Remediation:** Patch operations use an allowlist of permitted attributes and CSS properties.
* **Finding-Based Targeting:** Proposed patches can only target elements identified by the accessibility scanner.
* **Sanitized Verification:** Verification removes scripts, iframes, and inline event handlers from the HTML snapshot.
* **Human Approval:** Proposed modifications are reviewed before application.
* **Isolated Changes:** The original live website is not modified.

Security is an ongoing development area. The current DNS validation approach has a DNS-rebinding limitation, and container isolation remains important.

## Deployment

AccessLens supports deployment as a single Docker container containing the FastAPI backend and built React frontend.

### Docker

Build the image:

```bash
docker build -t accesslens .
```

Run the container:

```bash
docker run -p 7860:7860 \
  -e GEMINI_API_KEY=your_api_key \
  accesslens
```

The application is served on port `7860`.

### Hugging Face Spaces

AccessLens can be deployed using a Docker-based Hugging Face Space.

1. Create a new Space.
2. Select **Docker** as the SDK.
3. Configure `GEMINI_API_KEY` under Space Secrets.
4. Add the Space as a Git remote:

```bash
git remote add space https://huggingface.co/spaces/YOUR_USERNAME/accesslens
```

5. Push the main branch:

```bash
git push space main
```

Use a Hugging Face write-access token when authenticating.

### Other Hosting Platforms

The Docker deployment can also be used with Render, Railway, or Fly.io.

Chromium requires sufficient memory; a 512 MB instance may not be adequate.

## Current Limitations

* Automated axe-core checks cannot identify every real-world accessibility barrier.
* AI-generated explanations and text suggestions still require human judgment.
* AccessLens is not a WCAG compliance certification tool.
* The current implementation scans one webpage at a time.
* Verification operates on a sanitized HTML snapshot and may not cover JavaScript-driven interface states.
* Scan results are stored in memory and are lost when the application restarts.
* DNS rebinding remains a known limitation in the current SSRF protection.

## Project Impact

AccessLens aims to make accessibility remediation more actionable by connecting automated detection, AI-assisted explanations, human review, and measurable verification in one workflow.

Rather than simply reporting violations, it helps developers understand what needs attention and evaluate whether proposed improvements actually resolve the detected issues.

## Future Scope

* Multi-page website scanning.
* Expanded WCAG coverage and accessibility auditing.
* Improved visual and keyboard-navigation analysis.
* Persistent scan history and reporting.
* More comprehensive browser-state verification.
* Enhanced remediation validation and security hardening.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

---

**AccessLens — Making the Web More Accessible, One Fix at a Time.**
