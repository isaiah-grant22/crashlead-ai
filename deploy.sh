#!/bin/bash
# CrashLead AI — one-shot deploy to GitHub
cd "$(dirname "$0")"
git add -A
git commit -m "CrashLead AI v3.2 — Nationwide Edition"
gh repo create crashlead-ai --public --source=. --push
echo ""
echo "✅ Done! Now go to https://share.streamlit.io to deploy."
echo "   Select repo: crashlead-ai | branch: master | file: app.py"
