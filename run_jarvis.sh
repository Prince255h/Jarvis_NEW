#!/usr/bin/env bash
# ==============================================================================
# J.A.R.V.I.S AI Assistant Launcher for Linux and macOS
# ==============================================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "====================================================="
echo "         J.A.R.V.I.S AI ASSISTANT LAUNCHER"
echo "====================================================="
echo ""

# 1. Locate suitable Python 3.10+ executable
PYTHON_BIN=""
for candidate in python3 python python3.12 python3.11 python3.10; do
    if command -v "$candidate" >/dev/null 2>&1; then
        VER=$("$candidate" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null || true)
        MAJOR=$(echo "$VER" | cut -d. -f1)
        MINOR=$(echo "$VER" | cut -d. -f2)
        if [ "$MAJOR" -eq 3 ] && [ "$MINOR" -ge 10 ]; then
            PYTHON_BIN="$candidate"
            break
        fi
    fi
done

if [ -z "$PYTHON_BIN" ]; then
    echo "[ERROR] Python 3.10+ was not found in PATH."
    echo "Please install Python 3.10+ using your package manager:"
    echo "  Ubuntu/Debian: sudo apt update && sudo apt install -y python3 python3-venv python3-pip"
    echo "  Fedora:        sudo dnf install -y python3 python3-pip"
    echo "  Arch Linux:    sudo pacman -S python python-pip"
    echo "  macOS (brew):  brew install python@3.12"
    exit 1
fi

echo "[INFO] Using Python: $($PYTHON_BIN --version) ($PYTHON_BIN)"

# 2. Create virtual environment if missing
VENV_DIR="$SCRIPT_DIR/venv"
VENV_PY="$VENV_DIR/bin/python"

if [ ! -f "$VENV_PY" ]; then
    echo "[1/3] Creating Python virtual environment in '$VENV_DIR'..."
    "$PYTHON_BIN" -m venv "$VENV_DIR" || {
        echo "[ERROR] Failed to create virtual environment."
        echo "Make sure 'python3-venv' or 'python3-virtualenv' is installed."
        exit 1
    }
fi

# 3. Check and install dependencies
NEED_INSTALL=0
if [ "$1" == "--reinstall" ]; then
    NEED_INSTALL=1
fi

if [ "$NEED_INSTALL" -eq 0 ]; then
    if ! "$VENV_PY" -c "import PySide6, google.genai, groq, dotenv, requests, psutil, edge_tts, pygame, cryptography, numpy, pyautogui, pyperclip" >/dev/null 2>&1; then
        NEED_INSTALL=1
    fi
fi

if [ "$NEED_INSTALL" -eq 1 ]; then
    echo "[2/3] Installing Python dependencies from requirements.txt..."
    "$VENV_PY" -m pip install --upgrade pip
    "$VENV_PY" -m pip install -r requirements.txt || {
        echo ""
        echo "[ERROR] Failed to install pip requirements."
        echo "If PySide6 or PyAutoGUI failed, make sure system libraries are present:"
        echo "  Ubuntu/Debian: sudo apt install -y libgl1 libegl1 libxkbcommon-x11-0 libdbus-1-3 python3-tk"
        echo "  Fedora:        sudo dnf install -y mesa-libGL libxkbcommon-x11 dbus-libs python3-tkinter"
        echo "  Arch Linux:    sudo pacman -S mesa libxkbcommon dbus tk"
        exit 1
    }
    echo "[INFO] Dependencies installed successfully!"
else
    echo "[2/3] All dependencies are already installed."
fi

# 4. Create starter .env if missing
if [ ! -f "$SCRIPT_DIR/.env" ]; then
    echo "[INFO] Creating starter .env configuration..."
    cat << 'EOF' > "$SCRIPT_DIR/.env"
GEMINI_API_KEY=
GROQ_API_KEY=
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=qwen3.5:4b
EOF
    echo "[NOTE] Add your GEMINI_API_KEY or GROQ_API_KEY to .env for cloud AI features."
fi

# 5. Launch J.A.R.V.I.S GUI
echo "[3/3] Starting J.A.R.V.I.S AI Assistant..."
echo ""
exec "$VENV_PY" -m interface.chat "$@"
