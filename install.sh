#!/usr/bin/env bash
# ILLIP AI — one-line installer
# curl -fsSL https://raw.githubusercontent.com/Yashwanth-pilli/ILLIP/main/install.sh | bash

set -e

REPO_URL="${ILLIP_REPO:-https://github.com/Yashwanth-pilli/ILLIP.git}"
INSTALL_DIR="${ILLIP_DIR:-./illip_ai}"
PYTHON="${ILLIP_PYTHON:-python3}"

echo "=== ILLIP AI Installer ==="
echo "This installer will:"
echo "  1) Download ILLIP source code from GitHub (or update an existing install)"
echo "  2) Create a Python virtual environment -> keeps ILLIP's packages off your system Python"
echo "  3) Install Python packages           -> web app, memory, agents"
echo "  4) Create .env and data folders       -> your settings and ILLIP's memory live here"
echo ""
echo "It does NOT download any AI model by itself. After install you pick one:"
echo "  - Ollama (ollama.com): free local model, private, works offline"
echo "  - Or a cloud key (OpenRouter/Groq) in .env: no big download, needs internet"
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
  echo "=== ONE STEP LEFT: pick your AI brain ==="
  echo "Edit .env and set ONE of these:"
  echo "  Local + free + private : install Ollama from ollama.com, then 'ollama pull llama3.2'"
  echo "  Cloud key              : OpenRouter or Groq API key (no big download)"
  echo "Optional extras (set env vars to enable): Telegram, Discord, Slack, Email."
  echo "=========================================="
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
