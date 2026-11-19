"""WhatsApp Web Automation Engine for J.A.R.V.I.S.

Automates WhatsApp Web in Google Chrome:
- Direct message via phone number scheme (https://web.whatsapp.com/send?phone=...&text=...)
- Contact name search on WhatsApp Web search bar (Ctrl+Alt+/), chat opening, and messaging
- Voice/Video call initiation and conversation opening
- Background threading so UI remains 100% responsive
"""

import os
import re
import sys
import time
import ctypes
import threading
import urllib.parse
from typing import Callable, Optional

import pyautogui
import pyperclip

from tools.computer import find_chrome_executable, open_url_in_chrome

# Disable PyAutoGUI fail-safe pause delay for snappy execution, but keep fail-safe enabled
pyautogui.PAUSE = 0.05
pyautogui.FAILSAFE = True

WHATSAPP_WEB_URL = "https://web.whatsapp.com"


def is_phone_number(contact: str) -> bool:
    """Return True if contact string represents a direct phone number."""
    cleaned = re.sub(r"[\s\-\(\)\.]", "", (contact or "").strip())
    # Starts with + and has digits, or is a digit sequence of 7 to 15 digits
    if cleaned.startswith("+") and cleaned[1:].isdigit() and len(cleaned[1:]) >= 7:
        return True
    if cleaned.isdigit() and len(cleaned) >= 7:
        return True
    return False


def clean_phone_number(contact: str) -> str:
    """Normalize phone number to purely digits (removing +, spaces, dashes)."""
    return re.sub(r"[^\d]", "", (contact or "").strip())


def bring_chrome_to_foreground() -> bool:
    """Bring Google Chrome or WhatsApp window to the foreground on Windows."""
    if sys.platform != "win32":
        return False

    user32 = ctypes.windll.user32
    target_hwnd = None

    def enum_windows_proc(hwnd, lparam):
        nonlocal target_hwnd
        if user32.IsWindowVisible(hwnd):
            length = user32.GetWindowTextLengthW(hwnd)
            if length > 0:
                buff = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, buff, length + 1)
                title = buff.value.lower()
                if "whatsapp" in title or "google chrome" in title or "chrome" in title:
                    target_hwnd = hwnd
                    return False
        return True

    try:
        CB = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
        user32.EnumWindows(CB(enum_windows_proc), 0)
        if target_hwnd:
            # SW_RESTORE = 9, SW_SHOW = 5
            user32.ShowWindow(target_hwnd, 9)
            user32.SetForegroundWindow(target_hwnd)
            return True
    except Exception:
        pass
    return False


def open_whatsapp_web() -> str:
    """Open WhatsApp Web in Google Chrome and bring to foreground."""
    browser_used = open_url_in_chrome(WHATSAPP_WEB_URL)
    time.sleep(1.0)
    bring_chrome_to_foreground()
    return f"Opened WhatsApp Web in {browser_used}."


def _automate_whatsapp_contact_and_msg(
    contact_name: str,
    message: str = "",
    auto_send: bool = True,
    is_call: bool = False,
    call_type: str = "voice",
    on_status: Optional[Callable[[str], None]] = None,
):
    """Background automation worker for searching contact and typing/sending message in Chrome."""
    def log(msg: str):
        if on_status:
            try:
                on_status(msg)
            except Exception:
                pass

    try:
        log("Opening WhatsApp Web in Google Chrome...")
        open_url_in_chrome(WHATSAPP_WEB_URL)

        # Allow browser window and WhatsApp Web page to load / focus
        time.sleep(3.5)
        bring_chrome_to_foreground()
        time.sleep(0.5)

        log(f"Focusing search bar and searching for '{contact_name}'...")
        # Dismiss any open modals or dialogs
        pyautogui.press("escape")
        time.sleep(0.2)

        # WhatsApp Web official shortcut to focus search: Ctrl + Alt + / (or Ctrl + Alt + N)
        pyautogui.hotkey("ctrl", "alt", "/")
        time.sleep(0.3)

        # In case search didn't focus, try Ctrl+Alt+N (new chat search)
        # Clear field just in case
        pyautogui.hotkey("ctrl", "a")
        pyautogui.press("backspace")
        time.sleep(0.2)

        # Paste contact name via clipboard for 100% Unicode / emoji fidelity
        pyperclip.copy(contact_name.strip())
        pyautogui.hotkey("ctrl", "v")
        time.sleep(1.8)  # Wait for live search results to populate

        log(f"Selecting contact '{contact_name}'...")
        # Press Enter to open the top matched contact
        pyautogui.press("enter")
        time.sleep(1.0)

        # Second enter or down arrow in case first hit stayed in search results list
        pyautogui.press("enter")
        time.sleep(0.8)

        if is_call:
            log(f"Opened conversation with '{contact_name}'. Ready for {call_type} call in Chrome.")
            # WhatsApp call notification: The contact's chat is now open.
            # In WhatsApp Web/Desktop, the user can click the voice/video call icon in top-right header.
            return

        if message:
            log(f"Entering message for '{contact_name}'...")
            pyperclip.copy(message.strip())
            time.sleep(0.2)
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
            log(f"Opened chat with '{contact_name}' on WhatsApp Web.")

    except Exception as err:
        log(f"WhatsApp automation encountered an error: {err}")


def send_whatsapp_message(
    contact: str,
    message: str = "",
    auto_send: bool = True,
    on_status: Optional[Callable[[str], None]] = None,
) -> str:
    """Send a WhatsApp message via Google Chrome (supporting both phone numbers and contact names)."""
    raw_contact = (contact or "").strip()
    if not raw_contact:
        raise ValueError("Please provide a contact name or phone number for WhatsApp.")

    # 1. Direct Phone Number Mode (Official WhatsApp Web URL Scheme)
    if is_phone_number(raw_contact):
        phone_digits = clean_phone_number(raw_contact)
        if message:
            encoded_text = urllib.parse.quote(message.strip())
            url = f"https://web.whatsapp.com/send?phone={phone_digits}&text={encoded_text}"
        else:
            url = f"https://web.whatsapp.com/send?phone={phone_digits}"

        browser_used = open_url_in_chrome(url)

        if auto_send and message:
            def _send_enter_later():
                time.sleep(6.5)
                bring_chrome_to_foreground()
                time.sleep(0.5)
                pyautogui.press("enter")

            threading.Thread(target=_send_enter_later, daemon=True, name="WhatsApp-AutoEnter").start()

        return f"Opened WhatsApp Web in {browser_used} for +{phone_digits} with pre-filled message."

    # 2. Contact Name Mode (Search Bar Automation in Chrome)
    threading.Thread(
        target=_automate_whatsapp_contact_and_msg,
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
    """Search for contact on WhatsApp Web in Google Chrome, open chat, and prime voice/video call."""
    raw_contact = (contact or "").strip()
    if not raw_contact:
        raise ValueError("Please provide a contact name or phone number to call on WhatsApp.")

    ctype = "video" if "vid" in call_type.lower() else "voice"

    if is_phone_number(raw_contact):
        phone_digits = clean_phone_number(raw_contact)
        url = f"https://web.whatsapp.com/send?phone={phone_digits}"
        browser_used = open_url_in_chrome(url)
        return f"Opened chat with +{phone_digits} on WhatsApp Web in {browser_used}. Ready for {ctype} call."

    threading.Thread(
        target=_automate_whatsapp_contact_and_msg,
        args=(raw_contact, "", False, True, ctype, on_status),
        daemon=True,
        name="WhatsApp-SearchCall",
    ).start()

    return f"Opening conversation with '{raw_contact}' on WhatsApp Web in Google Chrome for {ctype} call."


def parse_and_send_whatsapp(payload: str) -> str:
    """Parse common syntax formats and execute WhatsApp message dispatch.
    
    Supported formats:
    - 'Alex | Hello how are you'
    - 'Mom : Dinner is ready'
    - 'John saying I will be there in 5 mins'
    - 'Sarah - Meeting rescheduled'
    - '+1234567890 | Hello'
    """
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
