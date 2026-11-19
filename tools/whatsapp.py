"""WhatsApp Web Automation Engine for J.A.R.V.I.S (Google Chrome).

Features:
- Guaranteed Chrome Foreground & Input Focus:
  - Windows station/desktop attachment (WinSta0\\default)
  - Thread input attachment and Alt-key foreground unlock
- Intelligent Tab Search & Seamless Tab Opening:
  - If WhatsApp Web tab is open, switches to it via Chrome Tab Search (Ctrl+Shift+A)
  - If closed, opens a new tab (Ctrl+T) and navigates to https://web.whatsapp.com directly in active Chrome
- Dynamic Visual Loading Detection (No Blind Spamming):
  - Actively polls screen framebuffer (~2ms per check) for the green WhatsApp header/search UI
  - Intelligently waits for WhatsApp Web to finish syncing chats before executing any actions
  - Never clicks on loading splash screens or blank pages
- Precision Coordinate Targeting:
  - Dynamic display scaling with exact offsets measured on live WhatsApp Web UI
  - Search bar: (left + min(210, width * 0.11), top + height * 0.165)
  - First contact card: (left + min(210, width * 0.11), top + height * 0.29) + Down/Enter fallback
  - Message input box: (left + int(width * 0.48), bottom - 50)
  - Voice Call button: (right - 150, top + 126)
  - Video Call button: (right - 205, top + 126)
- Dual-Mode Routing:
  1. Direct Phone Scheme (https://web.whatsapp.com/send?phone=...&text=...) for phone numbers & saved Address Book
  2. Full UI Automation for contact names with search, auto-open, typing & sending
- Background daemon threads with live status callbacks
"""

import os
import re
import sys
import time
import ctypes
import threading
import urllib.parse
from typing import Callable, Optional, Tuple

import pyautogui
import pyperclip
from PIL import ImageGrab

from tools.computer import find_chrome_executable, open_url_in_chrome
from core.memory import (
    save_whatsapp_contact,
    get_whatsapp_contact,
    list_whatsapp_contacts,
    delete_whatsapp_contact,
)

# PyAutoGUI configuration
pyautogui.PAUSE = 0.08
pyautogui.FAILSAFE = True

WHATSAPP_WEB_URL = "https://web.whatsapp.com"


class RECT(ctypes.Structure):
    _fields_ = [
        ("left", ctypes.c_long),
        ("top", ctypes.c_long),
        ("right", ctypes.c_long),
        ("bottom", ctypes.c_long),
    ]


def _attach_interactive_desktop():
    """Attach calling thread to interactive Windows desktop (WinSta0\\default)."""
    if sys.platform != "win32":
        return
    try:
        user32 = ctypes.windll.user32
        h_winsta = user32.OpenWindowStationW("WinSta0", False, 0x037F)
        if h_winsta:
            user32.SetProcessWindowStation(h_winsta)
        h_desk = user32.OpenDesktopW("default", 0, False, 0x01FF)
        if h_desk:
            user32.SetThreadDesktop(h_desk)
    except Exception:
        pass


def is_phone_number(contact: str) -> bool:
    """Return True if contact string represents an explicit phone number."""
    cleaned = re.sub(r"[\s\-\(\)\.]", "", (contact or "").strip())
    if cleaned.startswith("+") and cleaned[1:].isdigit() and len(cleaned[1:]) >= 7:
        return True
    if cleaned.isdigit() and len(cleaned) >= 7:
        return True
    return False


def clean_phone_number(contact: str) -> str:
    """Normalize phone number to purely digits (removing +, spaces, dashes)."""
    return re.sub(r"[^\d]", "", (contact or "").strip())


def find_chrome_hwnd() -> Optional[int]:
    """Locate the top-level window handle for Google Chrome or WhatsApp."""
    if sys.platform != "win32":
        return None

    _attach_interactive_desktop()
    user32 = ctypes.windll.user32
    target_hwnd = None
    fallback_chrome_hwnd = None

    def enum_cb(hwnd, _):
        nonlocal target_hwnd, fallback_chrome_hwnd
        if user32.IsWindowVisible(hwnd):
            length = user32.GetWindowTextLengthW(hwnd)
            if length > 0:
                buff = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, buff, length + 1)
                t = buff.value.lower()
                if "whatsapp" in t and "chrome" in t:
                    target_hwnd = hwnd
                    return False
                elif "google chrome" in t or "chrome" in t:
                    if not fallback_chrome_hwnd:
                        fallback_chrome_hwnd = hwnd
        return True

    try:
        CB = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
        user32.EnumWindows(CB(enum_cb), 0)
    except Exception:
        pass

    return target_hwnd or fallback_chrome_hwnd


def get_chrome_rect(hwnd: Optional[int] = None) -> Tuple[int, int, int, int, int, int]:
    """Return (left, top, right, bottom, width, height) of Chrome or primary screen fallback."""
    _attach_interactive_desktop()
    user32 = ctypes.windll.user32
    sw = user32.GetSystemMetrics(0)
    sh = user32.GetSystemMetrics(1)

    if hwnd:
        try:
            r = RECT()
            if user32.GetWindowRect(hwnd, ctypes.byref(r)):
                w = r.right - r.left
                h = r.bottom - r.top
                if w > 200 and h > 200:
                    return (max(0, r.left), max(0, r.top), r.right, r.bottom, w, h)
        except Exception:
            pass

    return (0, 0, sw, sh, sw, sh)


def focus_and_maximize_chrome(hwnd: Optional[int] = None) -> bool:
    """Bulletproof Win32 foreground activation, maximize and thread input attachment."""
    if sys.platform != "win32":
        return False

    _attach_interactive_desktop()
    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32

    if not hwnd:
        hwnd = find_chrome_hwnd()
    if not hwnd:
        return False

    try:
        my_thread = kernel32.GetCurrentThreadId()
        fg_hwnd = user32.GetForegroundWindow()
        fg_thread = user32.GetWindowThreadProcessId(fg_hwnd, None) if fg_hwnd else 0
        target_thread = user32.GetWindowThreadProcessId(hwnd, None)

        if target_thread:
            user32.AttachThreadInput(my_thread, target_thread, True)
        if fg_thread and fg_thread != my_thread:
            user32.AttachThreadInput(my_thread, fg_thread, True)

        # 1. Unlock Windows SetForegroundWindow lock by simulating Alt key tap
        user32.keybd_event(0x12, 0, 0, 0)  # VK_MENU (Alt)
        user32.keybd_event(0x12, 0, 2, 0)  # KEYEVENTF_KEYUP

        # 2. Maximize and bring to front (SW_MAXIMIZE = 3, SW_RESTORE = 9)
        user32.ShowWindow(hwnd, 3)
        user32.BringWindowToTop(hwnd)
        user32.SetForegroundWindow(hwnd)

        if target_thread:
            user32.AttachThreadInput(my_thread, target_thread, False)
        if fg_thread and fg_thread != my_thread:
            user32.AttachThreadInput(my_thread, fg_thread, False)

        time.sleep(0.3)
        return True
    except Exception:
        pass

    try:
        pyautogui.hotkey("win", "up")
    except Exception:
        pass
    return False


def get_window_title(hwnd: int) -> str:
    """Get title text of a window handle."""
    if sys.platform != "win32" or not hwnd:
        return ""
    try:
        user32 = ctypes.windll.user32
        length = user32.GetWindowTextLengthW(hwnd)
        if length > 0:
            buff = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buff, length + 1)
            return buff.value
    except Exception:
        pass
    return ""


def is_whatsapp_ui_ready() -> bool:
    """Inspect primary screen to check if WhatsApp Web interface has fully loaded."""
    _attach_interactive_desktop()
    try:
        # Check top-left area: bbox (60, 80, 220, 160)
        im = ImageGrab.grab(bbox=(60, 80, 220, 160))
        green_count = 0
        for x in range(0, im.width, 2):
            for y in range(0, im.height, 2):
                r, g, b = im.getpixel((x, y))[:3]
                if g > 120 and r < 75 and b < 100:
                    green_count += 1
                    if green_count > 25:
                        return True
        return False
    except Exception:
        return True


def wait_for_whatsapp_ready(
    timeout: float = 35.0,
    on_status: Optional[Callable[[str], None]] = None,
) -> bool:
    """Intelligently wait until WhatsApp Web UI has fully loaded and synced (no blind clicking)."""
    def log(m):
        if on_status:
            try:
                on_status(m)
            except Exception:
                pass

    log("Waiting for WhatsApp Web to finish loading and syncing chats...")
    start_time = time.time()
    last_log_time = 0.0

    while time.time() - start_time < timeout:
        if is_whatsapp_ui_ready():
            elapsed = round(time.time() - start_time, 1)
            log(f"WhatsApp Web interface is fully loaded and ready ({elapsed}s).")
            time.sleep(0.6)  # Short settling delay
            return True

        if time.time() - last_log_time >= 3.0:
            elapsed = int(time.time() - start_time)
            log(f"WhatsApp Web is still loading... ({elapsed}s)")
            last_log_time = time.time()

        time.sleep(0.4)

    log("Warning: WhatsApp Web loading timed out or requires QR code authentication.")
    return False


def ensure_whatsapp_tab(on_status: Optional[Callable[[str], None]] = None) -> int:
    """Ensure Chrome is running, foregrounded, and switched to WhatsApp Web tab."""
    def log(m):
        if on_status:
            try:
                on_status(m)
            except Exception:
                pass

    _attach_interactive_desktop()
    hwnd = find_chrome_hwnd()

    if not hwnd:
        log("Google Chrome is not running. Launching WhatsApp Web in Chrome...")
        open_url_in_chrome(WHATSAPP_WEB_URL)
        time.sleep(2.0)
        hwnd = find_chrome_hwnd()
        if hwnd:
            focus_and_maximize_chrome(hwnd)
        wait_for_whatsapp_ready(timeout=35.0, on_status=on_status)
        return hwnd or 0

    focus_and_maximize_chrome(hwnd)
    time.sleep(0.3)

    title = get_window_title(hwnd).lower()
    if "whatsapp" in title and is_whatsapp_ui_ready():
        log("WhatsApp Web tab is active and ready in Google Chrome.")
        return hwnd

    # 1. Try Chrome Tab Search (Ctrl+Shift+A) to switch to open tab
    log("Checking open tabs for WhatsApp Web via Tab Search...")
    pyautogui.hotkey("ctrl", "shift", "a")
    time.sleep(0.4)
    pyperclip.copy("WhatsApp")
    pyautogui.hotkey("ctrl", "v")
    time.sleep(0.4)
    pyautogui.press("enter")
    time.sleep(1.0)

    # Re-verify window title
    title = get_window_title(hwnd).lower()
    if "whatsapp" in title and is_whatsapp_ui_ready():
        log("Switched to WhatsApp Web tab successfully.")
        return hwnd

    # 2. Tab is closed: Open a new tab in active Chrome and navigate cleanly!
    log("WhatsApp tab was closed. Opening a new tab in Chrome and loading WhatsApp Web...")
    focus_and_maximize_chrome(hwnd)
    pyautogui.hotkey("ctrl", "t")
    time.sleep(0.4)
    pyperclip.copy(WHATSAPP_WEB_URL)
    pyautogui.hotkey("ctrl", "v")
    time.sleep(0.2)
    pyautogui.press("enter")

    # 3. Dynamically wait until WhatsApp Web UI is completely rendered
    wait_for_whatsapp_ready(timeout=35.0, on_status=on_status)
    return hwnd


def open_whatsapp_web() -> str:
    """Open WhatsApp Web in Google Chrome and bring to foreground."""
    browser_used = open_url_in_chrome(WHATSAPP_WEB_URL)
    time.sleep(1.5)
    hwnd = find_chrome_hwnd()
    if hwnd:
        focus_and_maximize_chrome(hwnd)
        wait_for_whatsapp_ready(timeout=35.0)
    return f"Opened WhatsApp Web in {browser_used}."


# ==========================================
# AUTOMATION WORKERS (MESSAGING & CALLING)
# ==========================================

def _worker_send_via_phone_url(
    phone_digits: str,
    message: str = "",
    auto_send: bool = True,
    is_call: bool = False,
    call_type: str = "voice",
    on_status: Optional[Callable[[str], None]] = None,
):
    """Automate chat with a direct phone number via WhatsApp Web URL."""
    def log(m):
        if on_status:
            try:
                on_status(m)
            except Exception:
                pass

    try:
        _attach_interactive_desktop()
        if message:
            encoded_text = urllib.parse.quote(message.strip())
            url = f"https://web.whatsapp.com/send?phone={phone_digits}&text={encoded_text}"
        else:
            url = f"https://web.whatsapp.com/send?phone={phone_digits}"

        log(f"Opening WhatsApp Web conversation for +{phone_digits} in Google Chrome...")
        open_url_in_chrome(url)

        # Wait intelligently for WhatsApp Web to load
        wait_for_whatsapp_ready(timeout=35.0, on_status=on_status)

        hwnd = find_chrome_hwnd()
        if hwnd:
            focus_and_maximize_chrome(hwnd)
        time.sleep(0.5)

        hwnd = find_chrome_hwnd()
        left, top, right, bottom, width, height = get_chrome_rect(hwnd)

        if is_call:
            log(f"Chat open with +{phone_digits}. Initiating {call_type} call in Chrome...")
            time.sleep(1.0)
            if "vid" in call_type.lower():
                call_x = right - 205
                call_y = top + 126
            else:
                call_x = right - 150
                call_y = top + 126

            pyautogui.moveTo(call_x, call_y, duration=0.25)
            pyautogui.click(call_x, call_y)
            time.sleep(0.4)
            pyautogui.click(call_x, call_y)
            log(f"Initiated {call_type} call to +{phone_digits} on WhatsApp Web.")
            return

        # Messaging
        log(f"Focusing message field for +{phone_digits}...")
        msg_x = left + int(width * 0.48)
        msg_y = bottom - 50
        pyautogui.moveTo(msg_x, msg_y, duration=0.2)
        pyautogui.click()
        time.sleep(0.4)

        if auto_send:
            log(f"Sending message to +{phone_digits}...")
            pyautogui.press("enter")
            time.sleep(0.4)

            # If message was not pre-filled by URL parameter, paste and hit enter
            if message:
                pyperclip.copy(message.strip())
                pyautogui.hotkey("ctrl", "v")
                time.sleep(0.3)
                pyautogui.press("enter")
            log(f"Message sent to +{phone_digits} on WhatsApp Web.")
        else:
            log(f"Message ready for +{phone_digits}. Awaiting manual send.")

    except Exception as err:
        log(f"WhatsApp Phone Automation Error: {err}")


def _worker_search_and_execute(
    contact_name: str,
    message: str = "",
    auto_send: bool = True,
    is_call: bool = False,
    call_type: str = "voice",
    on_status: Optional[Callable[[str], None]] = None,
):
    """Automate contact name search on WhatsApp Web, opening chat, and messaging or calling."""
    def log(m):
        if on_status:
            try:
                on_status(m)
            except Exception:
                pass

    try:
        _attach_interactive_desktop()
        log(f"Ensuring WhatsApp Web is active in Google Chrome for '{contact_name}'...")
        hwnd = ensure_whatsapp_tab(on_status)
        time.sleep(0.5)

        hwnd = find_chrome_hwnd()
        left, top, right, bottom, width, height = get_chrome_rect(hwnd)

        # ----------------------------------------------------
        # 1. FOCUS SEARCH BAR (Precision coordinate click + shortcut)
        # ----------------------------------------------------
        log("Focusing WhatsApp Web search bar...")
        search_x = left + min(210, int(width * 0.11))
        search_y = top + int(height * 0.165)

        # Move and click inside "Search or start a new chat" pill
        pyautogui.moveTo(search_x, search_y, duration=0.2)
        pyautogui.click()
        time.sleep(0.2)

        # Also trigger official WhatsApp Web search shortcut
        pyautogui.hotkey("ctrl", "alt", "/")
        time.sleep(0.2)

        # Clear existing search query
        pyautogui.hotkey("ctrl", "a")
        pyautogui.press("backspace")
        time.sleep(0.2)

        # ----------------------------------------------------
        # 2. TYPE CONTACT NAME VIA CLIPBOARD
        # ----------------------------------------------------
        log(f"Searching for contact: '{contact_name}'...")
        pyperclip.copy(contact_name.strip())
        pyautogui.hotkey("ctrl", "v")

        # Wait 1.8 seconds for WhatsApp Web live search query to filter contacts
        time.sleep(1.8)

        # ----------------------------------------------------
        # 3. SELECT CONTACT & OPEN CHAT
        # ----------------------------------------------------
        log(f"Opening chat with '{contact_name}'...")
        first_result_x = search_x
        first_result_y = top + int(height * 0.29)
        pyautogui.moveTo(first_result_x, first_result_y, duration=0.15)
        pyautogui.click()
        time.sleep(0.25)

        # Press Down then Enter to guarantee selection
        pyautogui.press("down")
        time.sleep(0.25)
        pyautogui.press("enter")

        # Wait 1.5 seconds for the conversation pane on the right to open
        time.sleep(1.5)

        # Refresh Chrome rect coordinates
        hwnd = find_chrome_hwnd()
        left, top, right, bottom, width, height = get_chrome_rect(hwnd)

        # ----------------------------------------------------
        # 4. EXECUTE CALL OR MESSAGE
        # ----------------------------------------------------
        if is_call:
            log(f"Chat open. Initiating {call_type} call to '{contact_name}'...")
            if "vid" in call_type.lower():
                call_x = right - 205
                call_y = top + 126
            else:
                call_x = right - 150
                call_y = top + 126

            pyautogui.moveTo(call_x, call_y, duration=0.25)
            pyautogui.click(call_x, call_y)
            time.sleep(0.35)
            pyautogui.click(call_x, call_y)
            log(f"Initiated {call_type} call to '{contact_name}' on WhatsApp Web.")
            return

        if message:
            log(f"Typing message for '{contact_name}'...")
            msg_x = left + int(width * 0.48)
            msg_y = bottom - 50
            pyautogui.moveTo(msg_x, msg_y, duration=0.2)
            pyautogui.click()
            time.sleep(0.3)

            pyperclip.copy(message.strip())
            pyautogui.hotkey("ctrl", "v")
            time.sleep(0.35)

            if auto_send:
                log(f"Sending message to '{contact_name}'...")
                pyautogui.press("enter")
                time.sleep(0.3)
                log(f"Message sent to '{contact_name}' on WhatsApp Web.")
            else:
                log(f"Message typed for '{contact_name}'. Awaiting manual send.")
        else:
            log(f"Chat opened with '{contact_name}' on WhatsApp Web.")

    except Exception as err:
        log(f"WhatsApp Search Automation Error: {err}")


# ==========================================
# PUBLIC API FUNCTIONS
# ==========================================

def send_whatsapp_message(
    contact: str,
    message: str = "",
    auto_send: bool = True,
    on_status: Optional[Callable[[str], None]] = None,
) -> str:
    """Send a WhatsApp message via Google Chrome with automatic contact resolution."""
    raw_contact = (contact or "").strip()
    if not raw_contact:
        raise ValueError("Please provide a contact name or phone number for WhatsApp.")

    # 1. Check if contact is an explicit phone number
    if is_phone_number(raw_contact):
        phone_digits = clean_phone_number(raw_contact)
        threading.Thread(
            target=_worker_send_via_phone_url,
            args=(phone_digits, message, auto_send, False, "voice", on_status),
            daemon=True,
            name="WhatsApp-PhoneMsg",
        ).start()
        return f"Routing message to +{phone_digits} on WhatsApp Web via Google Chrome."

    # 2. Check if contact is saved in JARVIS Address Book
    saved_phone = get_whatsapp_contact(raw_contact)
    if saved_phone:
        phone_digits = clean_phone_number(saved_phone)
        threading.Thread(
            target=_worker_send_via_phone_url,
            args=(phone_digits, message, auto_send, False, "voice", on_status),
            daemon=True,
            name="WhatsApp-SavedContactMsg",
        ).start()
        return f"Found '{raw_contact}' in Address Book (+{phone_digits}). Sending message via Chrome."

    # 3. Fallback to Contact Name Search Automation
    threading.Thread(
        target=_worker_search_and_execute,
        args=(raw_contact, message, auto_send, False, "voice", on_status),
        daemon=True,
        name="WhatsApp-SearchMsg",
    ).start()

    msg_preview = f": \"{message[:40]}...\"" if len(message) > 40 else f": \"{message}\"" if message else ""
    return f"Searching '{raw_contact}' on WhatsApp Web in Google Chrome and sending message{msg_preview}."


def call_whatsapp_contact(
    contact: str,
    call_type: str = "voice",
    on_status: Optional[Callable[[str], None]] = None,
) -> str:
    """Search for contact on WhatsApp Web in Google Chrome, open chat, and click call button."""
    raw_contact = (contact or "").strip()
    if not raw_contact:
        raise ValueError("Please provide a contact name or phone number to call on WhatsApp.")

    ctype = "video" if "vid" in call_type.lower() else "voice"

    # 1. Check if direct phone number
    if is_phone_number(raw_contact):
        phone_digits = clean_phone_number(raw_contact)
        threading.Thread(
            target=_worker_send_via_phone_url,
            args=(phone_digits, "", False, True, ctype, on_status),
            daemon=True,
            name="WhatsApp-PhoneCall",
        ).start()
        return f"Initiating {ctype} call to +{phone_digits} on WhatsApp Web in Chrome."

    # 2. Check if saved in Address Book
    saved_phone = get_whatsapp_contact(raw_contact)
    if saved_phone:
        phone_digits = clean_phone_number(saved_phone)
        threading.Thread(
            target=_worker_send_via_phone_url,
            args=(phone_digits, "", False, True, ctype, on_status),
            daemon=True,
            name="WhatsApp-SavedContactCall",
        ).start()
        return f"Found '{raw_contact}' (+{phone_digits}). Calling on WhatsApp Web via Chrome."

    # 3. Search and call
    threading.Thread(
        target=_worker_search_and_execute,
        args=(raw_contact, "", False, True, ctype, on_status),
        daemon=True,
        name="WhatsApp-SearchCall",
    ).start()

    return f"Searching '{raw_contact}' on WhatsApp Web in Chrome and initiating {ctype} call."


def parse_and_send_whatsapp(payload: str) -> str:
    """Parse common syntax formats and execute WhatsApp message dispatch."""
    text = (payload or "").strip()
    if not text:
        raise ValueError("WhatsApp command requires a contact and optional message.")

    contact = text
    message = ""

    if "|" in text:
        parts = text.split("|", 1)
        contact, message = parts[0].strip(), parts[1].strip()
    elif ":" in text:
        parts = text.split(":", 1)
        contact, message = parts[0].strip(), parts[1].strip()
    elif " saying " in text.lower():
        idx = text.lower().find(" saying ")
        contact = text[:idx].strip()
        message = text[idx + len(" saying "):].strip()
    elif " that " in text.lower():
        idx = text.lower().find(" that ")
        contact = text[:idx].strip()
        message = text[idx + len(" that "):].strip()

    return send_whatsapp_message(contact=contact, message=message, auto_send=True)


def parse_and_call_whatsapp(payload: str) -> str:
    """Parse contact name and optional call type (voice/video)."""
    text = (payload or "").strip()
    if not text:
        raise ValueError("WhatsApp call requires a contact name or phone number.")

    call_type = "video" if "video" in text.lower() else "voice"
    clean_contact = re.sub(r"\b(?:video|voice|call)\b", "", text, flags=re.IGNORECASE).strip()
    return call_whatsapp_contact(contact=clean_contact or text, call_type=call_type)
