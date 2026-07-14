#!/usr/bin/env bash
# ILLIP AI — one-line installer
# curl -fsSL https://raw.githubusercontent.com/Yashwanth-pilli/ILLIP/main/install.sh | bash

set -e

REPO_URL="${ILLIP_REPO:-https://github.com/Yashwanth-pilli/ILLIP.git}"
INSTALL_DIR="${ILLIP_DIR:-./illip_ai}"
PYTHON="${ILLIP_PYTHON:-python3}"

echo "=== ILLIP AI Installer ==="
echo "This installer will:"
echo "  1) Download or update ILLIP source code from GitHub"
echo "  2) Create a Python virtual environment (optional, default on)"
echo "  3) Install Python dependencies from requirements.txt"
echo "  4) Create .env and data folders for first run"
echo ""

# Check Python
if ! command -v "$PYTHON" &>/dev/null; then
  echo "ERROR: python3 not found. Install Python 3.11+ first."
  exit 1
fi
PY_VER=$("$PYTHON" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
echo "Python $PY_VER found."

# Check git
if ! command -v git &>/dev/null; then
  echo "ERROR: git not found. Install git first."
  exit 1
fi

# Clone
if [ -d "$INSTALL_DIR/.git" ]; then
  echo "Directory $INSTALL_DIR exists — pulling latest code from $REPO_URL ..."
  git -C "$INSTALL_DIR" pull --ff-only origin main
elif [ -d "$INSTALL_DIR" ]; then
  echo "ERROR: $INSTALL_DIR already exists but is not a git repository."
  echo "Please remove it or set ILLIP_DIR to a different folder."
  exit 1
else
  echo "Downloading ILLIP source code from $REPO_URL ..."
  git clone --depth=1 "$REPO_URL" "$INSTALL_DIR"
fi

cd "$INSTALL_DIR"

# Virtualenv (optional but recommended)
if "$PYTHON" -m venv --help >/dev/null 2>&1 && [ "${ILLIP_VENV:-1}" = "1" ]; then
  if [ ! -d ".venv" ]; then
    echo "Creating virtualenv..."
    "$PYTHON" -m venv .venv
  fi
  source .venv/bin/activate
  PYTHON=python
fi

# Install deps
echo "Installing Python dependencies from requirements.txt (downloads may take a few minutes)..."
"$PYTHON" -m pip install -r requirements.txt

# Setup .env
if [ ! -f ".env" ]; then
  cp .env.example .env
  echo ""
  echo "=== SETUP REQUIRED ==="
  echo "Edit .env to configure your model provider (Ollama/OpenRouter/Groq)."
  echo "Telegram, Discord, Slack, Email — all optional, set env vars to enable."
  echo "======================"
fi

# Create data dirs
"$PYTHON" -c "from app.config import settings; settings.ensure_directories()" 2>/dev/null || mkdir -p data/{memory,logs,tasks,workspaces,snapshots,connectors}

echo ""
echo "ILLIP AI installed at: $(pwd)"
echo ""
echo "Start:    python -m uvicorn app.main:app --host 0.0.0.0 --port 8000"
echo "Or:       python app/main.py"
echo ""
echo "Add integrations from URL (no download needed):"
echo "  POST /api/skills/install  {\"url\": \"https://raw.github.com/.../skill.py\"}"
echo ""
