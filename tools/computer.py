"""Desktop Automation Engine for JARVIS (2.1 - 2.9)."""

import os
import re
import sys
import ctypes
import shutil
import subprocess
import webbrowser
import urllib.parse
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SCREENSHOT_DIR = BASE_DIR / "data" / "screenshots"
SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)


# ==========================================
# 2.1 OPEN APPLICATIONS
# ==========================================

APP_ALIASES = {
    "notepad": ["notepad.exe"],
    "calculator": ["calc.exe"],
    "calc": ["calc.exe"],
    "paint": ["mspaint.exe"],
    "mspaint": ["mspaint.exe"],
    "explorer": ["explorer.exe"],
    "files": ["explorer.exe"],
    "cmd": ["cmd.exe"],
    "terminal": ["powershell.exe"],
    "powershell": ["powershell.exe"],
    "task manager": ["taskmgr.exe"],
    "taskmgr": ["taskmgr.exe"],
    "vscode": ["code"],
    "code": ["code"],
    "chrome": ["chrome"],
    "edge": ["msedge"],
    "settings": ["ms-settings:"],
    "word": ["winword"],
    "excel": ["excel"],
    "spotify": ["spotify"],
}


def find_chrome_executable() -> str | None:
    """Locate Google Chrome executable on Windows (or PATH) so JARVIS always prefers Chrome."""
    candidates = [
        shutil.which("chrome"),
        shutil.which("google-chrome"),
        os.path.join(os.environ.get("ProgramFiles", r"C:\Program Files"), "Google", "Chrome", "Application", "chrome.exe"),
        os.path.join(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"), "Google", "Chrome", "Application", "chrome.exe"),
        os.path.join(os.environ.get("LOCALAPPDATA", ""), "Google", "Chrome", "Application", "chrome.exe"),
    ]
    for path in candidates:
        if path and os.path.isfile(path):
            return path

    if sys.platform == "win32":
        try:
            import winreg

            for root_hive in (winreg.HKEY_LOCAL_MACHINE, winreg.HKEY_CURRENT_USER):
                try:
                    with winreg.OpenKey(root_hive, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\chrome.exe") as k:
                        val, _ = winreg.QueryValueEx(k, None)
                        if val and os.path.isfile(val):
                            return val
                except OSError:
                    continue
        except Exception:
            pass
    return None


def open_url_in_chrome(url: str) -> str:
    """Always open URL in Google Chrome (falling back to default browser only if Chrome isn't installed)."""
    chrome_exe = find_chrome_executable()
    if chrome_exe:
        subprocess.Popen([chrome_exe, url], shell=False)
        return "Google Chrome"
    webbrowser.open(url)
    return "default browser"


def open_application(app_name: str) -> str:
    """Safely launch a known application or executable path."""
    raw = (app_name or "").strip()
    if not raw:
        raise ValueError("Please specify an application name.")

    key = raw.lower()
    if key in ("chrome", "google chrome"):
        chrome_exe = find_chrome_executable()
        if chrome_exe:
            subprocess.Popen([chrome_exe], shell=False)
            return f"Launched Google Chrome ({chrome_exe})"

    if key in APP_ALIASES:
        target = APP_ALIASES[key][0]
        if target.endswith(":"):
            os.startfile(target)
            return f"Opened Windows {raw}."
        try:
            subprocess.Popen([target], shell=False)
            return f"Launched application: {raw} ({target})"
        except FileNotFoundError:
            os.startfile(target)
            return f"Opened application: {raw}"

    # Direct file path check
    candidate = Path(raw)
    if candidate.exists():
        os.startfile(str(candidate))
        return f"Opened: {candidate}"

    # Fallback: try PATH lookup without arbitrary shell injection
    resolved = shutil.which(raw)
    if resolved:
        subprocess.Popen([resolved], shell=False)
        return f"Launched: {resolved}"

    raise FileNotFoundError(
        f"Could not find application '{raw}'. Try one of: {', '.join(sorted(APP_ALIASES.keys()))}"
    )


# ==========================================
# 2.2 OPEN WEBSITES
# ==========================================

SITE_SHORTCUTS = {
    "google": "https://www.google.com",
    "youtube": "https://www.youtube.com",
    "github": "https://github.com",
    "gmail": "https://mail.google.com",
    "stackoverflow": "https://stackoverflow.com",
    "wikipedia": "https://www.wikipedia.org",
    "reddit": "https://www.reddit.com",
    "linkedin": "https://www.linkedin.com",
    "owasp": "https://owasp.org/www-project-top-ten/",
    "portswigger": "https://portswigger.net/web-security",
    "tryhackme": "https://tryhackme.com",
    "hackthebox": "https://www.hackthebox.com",
}


def open_website(url_or_name: str) -> str:
    raw = (url_or_name or "").strip()
    if not raw:
        raise ValueError("Please specify a website URL or name.")

    key = raw.lower()
    if key in SITE_SHORTCUTS:
        url = SITE_SHORTCUTS[key]
    else:
        if any(ch.isspace() for ch in raw):
            raise ValueError(f"Invalid website URL (contains whitespace): {raw}")

        # Reject explicit non-HTTP(S) schemes like javascript:, file:, data:, vbscript:
        scheme_match = re.match(r"^([a-zA-Z][a-zA-Z0-9+.-]*):", raw)
        if scheme_match and scheme_match.group(1).lower() not in ("http", "https"):
            raise ValueError(f"Blocked unsupported URL scheme: {scheme_match.group(1)}:")

        url = raw if raw.startswith(("http://", "https://")) else "https://" + raw

    parsed = urllib.parse.urlparse(url)
    host = (parsed.hostname or "").lower()
    if (
        parsed.scheme not in ("http", "https")
        or not host
        or (host != "localhost" and "." not in host)
        or not re.fullmatch(r"[a-z0-9.-]+", host)
    ):
        raise ValueError(f"Invalid website URL: {url}")

    browser_used = open_url_in_chrome(url)
    return f"Opened in {browser_used}: {url}"


# ==========================================
# 2.3 SEARCH GOOGLE AND YOUTUBE
# ==========================================

def search_google(query: str) -> str:
    query = (query or "").strip()
    if not query:
        raise ValueError("Search query cannot be empty.")
    url = f"https://www.google.com/search?q={urllib.parse.quote_plus(query)}"
    browser_used = open_url_in_chrome(url)
    return f"Opened Google search in {browser_used} for: {query}"


def search_youtube(query: str) -> str:
    query = (query or "").strip()
    if not query:
        raise ValueError("YouTube query cannot be empty.")
    url = f"https://www.youtube.com/results?search_query={urllib.parse.quote_plus(query)}"
    browser_used = open_url_in_chrome(url)
    return f"Opened YouTube search in {browser_used} for: {query}"


# ==========================================
# 2.4 CREATE FILES AND FOLDERS
# ==========================================

def create_folder(folder_path: str) -> str:
    raw = (folder_path or "").strip()
    if not raw:
        raise ValueError("Folder path cannot be empty.")
    path = Path(raw)
    if not path.is_absolute():
        path = BASE_DIR / "workspace_files" / path
    path.mkdir(parents=True, exist_ok=True)
    return f"Folder created: {path}"


def create_file(file_path: str, content: str = "") -> str:
    raw = (file_path or "").strip()
    if not raw:
        raise ValueError("File path cannot be empty.")
    path = Path(raw)
    if not path.is_absolute():
        path = BASE_DIR / "workspace_files" / path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content or "", encoding="utf-8")
    return f"File created: {path} ({len(content or '')} chars)"


# ==========================================
# 2.5 READ AND ORGANIZE DOCUMENTS
# ==========================================

FILE_CATEGORIES = {
    "Documents": {".pdf", ".doc", ".docx", ".txt", ".md", ".rtf", ".odt", ".csv", ".xlsx", ".xls", ".pptx"},
    "Images": {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".svg", ".ico"},
    "Code": {".py", ".js", ".ts", ".jsx", ".tsx", ".html", ".css", ".json", ".yaml", ".yml", ".xml", ".sql", ".sh", ".ps1", ".c", ".cpp", ".java", ".go", ".rs"},
    "Audio_Video": {".mp3", ".wav", ".flac", ".ogg", ".mp4", ".mkv", ".avi", ".mov", ".webm"},
    "Archives": {".zip", ".rar", ".7z", ".tar", ".gz", ".bz2"},
}


def plan_folder_organization(folder_path: str) -> list:
    """Return a dry-run list of (source_path, dest_path) moves for files directly inside folder_path."""
    folder = Path(folder_path)
    if not folder.is_dir():
        raise FileNotFoundError(f"Directory not found: {folder}")

    moves = []
    for item in folder.iterdir():
        if not item.is_file():
            continue
        ext = item.suffix.lower()
        target_cat = "Other"
        for cat, exts in FILE_CATEGORIES.items():
            if ext in exts:
                target_cat = cat
                break
        dest_dir = folder / target_cat
        dest_file = dest_dir / item.name
        moves.append((item, dest_file))
    return moves


def execute_folder_organization(folder_path: str) -> str:
    """Organize files in folder_path into categorized subfolders without overwriting existing files."""
    moves = plan_folder_organization(folder_path)
    if not moves:
        return f"No loose files found in {folder_path}."

    moved_count = 0
    for src, dest in moves:
        dest.parent.mkdir(parents=True, exist_ok=True)
        final_dest = dest
        counter = 1
        while final_dest.exists():
            final_dest = dest.with_name(f"{dest.stem}_{counter}{dest.suffix}")
            counter += 1
        shutil.move(str(src), str(final_dest))
        moved_count += 1

    return f"Organized {moved_count} files inside {folder_path}."


# ==========================================
# 2.7 CONTROL SYSTEM VOLUME (Windows)
# ==========================================

VK_VOLUME_MUTE = 0xAD
VK_VOLUME_DOWN = 0xAE
VK_VOLUME_UP = 0xAF
KEYEVENTF_KEYUP = 0x0002


def _send_vk(vk_code: int, repeat: int = 1):
    if sys.platform != "win32":
        raise RuntimeError("System volume control is implemented for Windows.")
    user32 = ctypes.windll.user32
    for _ in range(max(1, repeat)):
        user32.keybd_event(vk_code, 0, 0, 0)
        user32.keybd_event(vk_code, 0, KEYEVENTF_KEYUP, 0)


def volume_up(steps: int = 5) -> str:
    _send_vk(VK_VOLUME_UP, repeat=steps)
    return f"Volume increased (+{steps * 2}% approx)."


def volume_down(steps: int = 5) -> str:
    _send_vk(VK_VOLUME_DOWN, repeat=steps)
    return f"Volume decreased (-{steps * 2}% approx)."


def volume_mute_toggle() -> str:
    _send_vk(VK_VOLUME_MUTE, repeat=1)
    return "Toggled system mute."


def set_volume_percent(percent: int) -> str:
    """Set approximate Windows system volume (0-100%) using reliable media key steps."""
    percent = max(0, min(100, int(percent)))
    # Reset to 0 then step up in 2% increments
    _send_vk(VK_VOLUME_DOWN, repeat=50)
    steps = round(percent / 2)
    if steps > 0:
        _send_vk(VK_VOLUME_UP, repeat=steps)
    return f"System volume set to approximately {percent}%."


# ==========================================
# 2.8 TAKE SCREENSHOTS (Called AFTER explicit GUI permission)
# ==========================================

def capture_screenshot_qapp(qapp) -> Path:
    """Capture primary screen using Qt after user grants permission."""
    screen = qapp.primaryScreen()
    if screen is None:
        raise RuntimeError("No display screen available to capture.")
    pixmap = screen.grabWindow(0)
    filename = f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    output_path = SCREENSHOT_DIR / filename
    if not pixmap.save(str(output_path), "PNG"):
        raise RuntimeError("Failed to save screenshot PNG.")
    return output_path


# ==========================================
# 2.9 EXECUTE APPROVED TERMINAL COMMANDS
# ==========================================

DANGEROUS_PATTERNS = (
    re.compile(r"\brm\s+[^\n]*(-[a-z]*r[a-z]*f|-[a-z]*f[a-z]*r|-r\s+-f|-f\s+-r|--recursive)", re.IGNORECASE),
    re.compile(r"\bremove-item\b[^\n]*(-recurse|-force)", re.IGNORECASE),
    re.compile(r"\b(?:del|erase)\b[^\n]*/[a-z]*s", re.IGNORECASE),
    re.compile(r"\b(?:rd|rmdir)\b[^\n]*/[a-z]*s", re.IGNORECASE),
    re.compile(r"\b(?:stop-computer|restart-computer|clear-disk|format-volume)\b", re.IGNORECASE),
    re.compile(r"\b(?:format|shutdown|reboot|diskpart|bcdedit)\b", re.IGNORECASE),
    re.compile(r"\breg\s+delete\b|\bcipher\s+/w\b", re.IGNORECASE),
)


def is_potentially_dangerous_command(command: str) -> bool:
    text = (command or "").strip()
    return any(pat.search(text) for pat in DANGEROUS_PATTERNS)


def run_approved_command(command: str, timeout: int = 30, cwd=None) -> dict:
    """Execute a terminal command AFTER the user explicitly approved it in the UI."""
    command = (command or "").strip()
    if not command:
        raise ValueError("Command cannot be empty.")

    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command", command] if sys.platform == "win32" else command,
        shell=(sys.platform != "win32"),
        capture_output=True,
        text=True,
        timeout=timeout,
        cwd=cwd or str(BASE_DIR),
    )
    return {
        "returncode": result.returncode,
        "stdout": result.stdout.strip(),
        "stderr": result.stderr.strip(),
    }

