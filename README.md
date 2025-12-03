# 🔍 ErrorLens

Lightweight error recording tool for QA engineers. Capture browser errors and get AI-powered analysis — no extensions, no registration, works everywhere.

## What is this?

ErrorLens is a bookmarklet that records browser errors in real-time. When you're testing a web application and encounter a bug, just click the bookmarklet to start recording, reproduce the error, click again to stop — and get instant AI analysis of what went wrong.

Perfect for QA engineers who are tired of manually copying console logs and network errors.

## Features

- 🎯 **One-click recording** — No setup, no installation, just drag a bookmark
- 📝 **Captures everything** — Console logs, network errors, JS exceptions
- 🤖 **AI analysis** — Get instant insights about what went wrong and how to fix it
- 📋 **Export ready** — Copy results in Markdown format for Jira/GitHub issues
- 🔒 **Privacy first** — Your data is analyzed and discarded, we don't store anything

## Quick Start

1. Go to [errorlens.github.io](https://mdyuzhev.github.io/errorlens) (coming soon)
2. Drag the "ErrorLens" button to your bookmarks bar
3. Open the page you want to test
4. Click the bookmark to start recording
5. Reproduce the bug
6. Click the floating button to stop and analyze

## Project Status

🚧 **Work in Progress** — See [ROADMAP.md](ROADMAP.md) for current progress.

## Tech Stack

- **Frontend:** Vanilla JavaScript (bookmarklet)
- **Backend:** Python / FastAPI
- **AI:** Google Gemini / Groq (free tier)
- **Hosting:** Vercel / Railway + GitHub Pages

## Local Development

```bash
# Clone the repo
git clone https://github.com/Mdyuzhev/errorlens.git
cd errorlens

# Backend
cd backend
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -r requirements.txt
uvicorn app.main:app --reload

# The bookmarklet is just a JS file, no build needed
```

## Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) before submitting PRs.

## License

MIT — see [LICENSE](LICENSE) for details.
