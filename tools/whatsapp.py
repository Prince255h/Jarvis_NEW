"""WhatsApp Web Automation Engine for J.A.R.V.I.S (Google Chrome).

Features:
- Dual-Mode Routing:
  1. Direct Phone Scheme (https://web.whatsapp.com/send?phone=...&text=...) for phone numbers and saved contacts
  2. Full UI Automation with robust Win32 focus, coordinate targeting & keyboard shortcuts for contact names
- Actual Voice & Video Calling via header button coordinate detection & click
- Built-in Contact Book (Name -> Phone) for zero-latency direct messaging
- Background daemon threads with live progress logging
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

from tools.computer import find_chrome_executable, open_url_in_chrome
from core.memory import (
    save_whatsapp_contact,
    get_whatsapp_contact,
    list_whatsapp_contacts,
    delete_whatsapp_contact,
)

# PyAutoGUI tuning
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

    user32 = ctypes.windll.user32
    target_hwnd = None

    def enum_cb(hwnd, _):
        nonlocal target_hwnd
        if user32.IsWindowVisible(hwnd):
            length = user32.GetWindowTextLengthW(hwnd)
            if length > 0:
                buff = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, buff, length + 1)
                t = buff.value.lower()
                if "whatsapp" in t or "google chrome" in t or "chrome" in t:
                    target_hwnd = hwnd
                    return False
        return True

    try:
        CB = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
        user32.EnumWindows(CB(enum_cb), 0)
    except Exception:
        pass
    return target_hwnd


def get_chrome_rect(hwnd: Optional[int] = None) -> Tuple[int, int, int, int, int, int]:
    """Return (left, top, right, bottom, width, height) of Chrome or primary screen fallback."""
    user32 = ctypes.windll.user32
    sw = user32.GetSystemMetrics(0)
    sh = user32.GetSystemMetrics(1)

    if hwnd:
        try:
            r = RECT()
            if user32.GetWindowRect(hwnd, ctypes.byref(r)):
                # If window is valid and on screen
                w = r.right - r.left
                h = r.bottom - r.top
                if w > 200 and h > 200:
                    return (max(0, r.left), max(0, r.top), r.right, r.bottom, w, h)
        except Exception:
            pass

    return (0, 0, sw, sh, sw, sh)


def focus_and_maximize_chrome() -> bool:
    """Bulletproof Win32 foreground activation and maximize for Google Chrome."""
    if sys.platform != "win32":
        return False

    user32 = ctypes.windll.user32
    hwnd = find_chrome_hwnd()

    if hwnd:
        try:
            # 1. Unlock Windows SetForegroundWindow lock by simulating Alt key tap
            user32.keybd_event(0x12, 0, 0, 0)  # VK_MENU (Alt)
            user32.keybd_event(0x12, 0, 2, 0)  # KEYEVENTF_KEYUP

            # 2. Attach thread input of current foreground window to our thread
            fore_hwnd = user32.GetForegroundWindow()
            fore_thread = user32.GetWindowThreadProcessId(fore_hwnd, None)
            curr_thread = user32.GetCurrentThreadId()

            if fore_thread != curr_thread:
                user32.AttachThreadInput(curr_thread, fore_thread, True)

            # 3. Maximize and bring to front (SW_MAXIMIZE = 3, SW_RESTORE = 9)
            user32.ShowWindow(hwnd, 3)
            user32.BringWindowToTop(hwnd)
            user32.SetForegroundWindow(hwnd)

            if fore_thread != curr_thread:
                user32.AttachThreadInput(curr_thread, fore_thread, False)

            time.sleep(0.3)
            return True
        except Exception:
            pass

    # Fallback: simulate Win+Up hotkey to maximize active window
    try:
        pyautogui.hotkey("win", "up")
    except Exception:
        pass
    return False


def open_whatsapp_web() -> str:
    """Open WhatsApp Web in Google Chrome and bring to foreground."""
    browser_used = open_url_in_chrome(WHATSAPP_WEB_URL)
    time.sleep(1.0)
    focus_and_maximize_chrome()
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
        if message:
            encoded_text = urllib.parse.quote(message.strip())
            url = f"https://web.whatsapp.com/send?phone={phone_digits}&text={encoded_text}"
        else:
            url = f"https://web.whatsapp.com/send?phone={phone_digits}"

        log(f"Opening WhatsApp Web conversation for +{phone_digits} in Google Chrome...")
        open_url_in_chrome(url)

        # Allow WhatsApp Web to load the conversation (needs ~7-8 seconds on initial load)
        time.sleep(7.0)
        focus_and_maximize_chrome()
        time.sleep(0.5)

        hwnd = find_chrome_hwnd()
        left, top, right, bottom, width, height = get_chrome_rect(hwnd)

        if is_call:
            log(f"Chat open with +{phone_digits}. Initiating {call_type} call in Chrome...")
            time.sleep(1.0)
            # Call button coordinates in top-right header
            if "vid" in call_type.lower():
                call_x = right - 175
                call_y = top + int(min(125, height * 0.11))
            else:
                call_x = right - 125
                call_y = top + int(min(125, height * 0.11))

            pyautogui.moveTo(call_x, call_y, duration=0.25)
            pyautogui.click(call_x, call_y)
            time.sleep(0.3)
            # Second click in case focus was on page background
            pyautogui.click(call_x, call_y)
            log(f"Initiated {call_type} call to +{phone_digits} on WhatsApp Web.")
            return

        # Messaging
        log(f"Focusing message field for +{phone_digits}...")
        # Click into bottom message box area
        msg_x = left + int(width * 0.60)
        msg_y = bottom - 55
        pyautogui.click(msg_x, msg_y)
        time.sleep(0.4)

        if auto_send:
            log(f"Sending message to +{phone_digits}...")
            pyautogui.press("enter")
            time.sleep(0.3)
            # If enter didn't send because pre-fill wasn't focused, paste and hit enter
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
        log(f"Launching WhatsApp Web in Google Chrome for '{contact_name}'...")
        open_url_in_chrome(WHATSAPP_WEB_URL)

        # Allow WhatsApp Web to load chats & sync (needs 7.0 seconds on fresh load)
        time.sleep(7.0)
        focus_and_maximize_chrome()
        time.sleep(0.5)

        hwnd = find_chrome_hwnd()
        left, top, right, bottom, width, height = get_chrome_rect(hwnd)

        # ----------------------------------------------------
        # 1. FOCUS SEARCH BAR (Coordinate click + Keyboard Shortcut)
        # ----------------------------------------------------
        log(f"Focusing WhatsApp Web search bar...")
        search_x = left + min(240, int(width * 0.15))
        search_y = top + int(height * 0.15)

        # Click the search bar directly
        pyautogui.click(search_x, search_y)
        time.sleep(0.3)

        # Also send New Chat / Search shortcut (Ctrl+Alt+N or Ctrl+Alt+/)
        pyautogui.hotkey("ctrl", "alt", "n")
        time.sleep(0.2)

        # Clear existing text
        pyautogui.hotkey("ctrl", "a")
        pyautogui.press("backspace")
        time.sleep(0.2)

        # ----------------------------------------------------
        # 2. TYPE CONTACT NAME VIA CLIPBOARD
        # ----------------------------------------------------
        log(f"Searching for contact: '{contact_name}'...")
        pyperclip.copy(contact_name.strip())
        pyautogui.hotkey("ctrl", "v")

        # Wait 2.2 seconds for live WhatsApp query to filter contacts
        time.sleep(2.2)

        # ----------------------------------------------------
        # 3. SELECT CONTACT & OPEN CHAT
        # ----------------------------------------------------
        log(f"Opening chat with '{contact_name}'...")
        # Coordinate click on first search result card directly below the search bar
        first_result_x = search_x
        first_result_y = top + int(height * 0.23)
        pyautogui.click(first_result_x, first_result_y)
        time.sleep(0.3)

        # Also press Down then Enter to guarantee selection
        pyautogui.press("down")
        time.sleep(0.2)
        pyautogui.press("enter")

        # Wait 1.8 seconds for the conversation pane on the right to open
        time.sleep(1.8)

        # ----------------------------------------------------
        # 4. EXECUTE CALL OR MESSAGE
        # ----------------------------------------------------
        if is_call:
            log(f"Chat open. Initiating {call_type} call to '{contact_name}'...")
            # Refresh coordinates
            hwnd = find_chrome_hwnd()
            left, top, right, bottom, width, height = get_chrome_rect(hwnd)

            if "vid" in call_type.lower():
                call_x = right - 175
                call_y = top + int(min(125, height * 0.11))
            else:
                call_x = right - 125
                call_y = top + int(min(125, height * 0.11))

            pyautogui.moveTo(call_x, call_y, duration=0.25)
            pyautogui.click(call_x, call_y)
            time.sleep(0.3)
            pyautogui.click(call_x, call_y)
            log(f"Initiated {call_type} call to '{contact_name}' on WhatsApp Web.")
            return

        if message:
            log(f"Typing message for '{contact_name}'...")
            # Click directly into bottom message box
            msg_x = left + int(width * 0.60)
            msg_y = bottom - 55
            pyautogui.click(msg_x, msg_y)
            time.sleep(0.3)

            pyperclip.copy(message.strip())
            pyautogui.hotkey("ctrl", "v")
            time.sleep(0.4)

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
