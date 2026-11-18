"""Smart AI Brain for JARVIS: Gemini, Groq, Ollama, smart task routing, fallback, vision, memory, and summarization."""

import os
import re
import json
import mimetypes
import requests
from pathlib import Path

from dotenv import load_dotenv
from google import genai
from google.genai import types

from core.personality import (
    JARVIS_PERSONALITY,
    PERSONALITIES,
    RESPONSE_STYLES,
    LANGUAGES,
    build_system_prompt,
)
from core.memory import (
    save_message,
    get_recent_messages,
    get_long_term_memories,
    add_long_term_memory,
    get_session_summary,
    save_session_summary,
    get_setting,
    set_setting,
)


# ==========================================
# CONFIGURATION
# ==========================================

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3.5:4b")

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")

_gemini_quota_exhausted = False

PROVIDER_MODE = get_setting("provider_mode", "auto") or "auto"
LAST_USED_PROVIDER = None
LAST_TASK_TYPE = "general"

CURRENT_PERSONALITY = get_setting("personality", "JARVIS") or "JARVIS"
CURRENT_RESPONSE_STYLE = get_setting("response_style", "Balanced") or "Balanced"
CURRENT_LANGUAGE = get_setting("language", "Auto-Detect") or "Auto-Detect"


# ==========================================
# PROVIDER & BRAIN SETTINGS CONTROL
# ==========================================

def set_provider_mode(provider):
    global PROVIDER_MODE
    allowed = ["auto", "gemini", "groq", "ollama"]
    provider = provider.lower().strip()
    if provider not in allowed:
        raise ValueError("Invalid AI provider.")
    PROVIDER_MODE = provider
    set_setting("provider_mode", provider)


def get_provider_mode():
    return PROVIDER_MODE


def get_last_provider():
    return LAST_USED_PROVIDER


def get_last_task_type():
    return LAST_TASK_TYPE


def set_personality(name):
    global CURRENT_PERSONALITY
    if name not in PERSONALITIES:
        raise ValueError(f"Unknown personality: {name}")
    CURRENT_PERSONALITY = name
    set_setting("personality", name)


def get_personality():
    return CURRENT_PERSONALITY


def set_response_style(style):
    global CURRENT_RESPONSE_STYLE
    if style not in RESPONSE_STYLES:
        raise ValueError(f"Unknown response style: {style}")
    CURRENT_RESPONSE_STYLE = style
    set_setting("response_style", style)


def get_response_style():
    return CURRENT_RESPONSE_STYLE


def set_language(language):
    global CURRENT_LANGUAGE
    if language not in LANGUAGES:
        raise ValueError(f"Unknown language: {language}")
    CURRENT_LANGUAGE = language
    set_setting("language", language)


def get_language():
    return CURRENT_LANGUAGE


# ==========================================
# GEMINI CLIENT
# ==========================================

gemini_client = None

if GEMINI_API_KEY:
    gemini_client = genai.Client(
        api_key=GEMINI_API_KEY,
        http_options=types.HttpOptions(api_version="v1beta"),
    )


# ==========================================
# SMART TASK CLASSIFICATION & MODEL ROUTING (1.3)
# ==========================================

_CODE_KEYWORDS = (
    "code", "python", "javascript", "typescript", "java", "c++", "rust", "sql",
    "debug", "traceback", "exception", "syntaxerror", "git ", "github", "regex",
    "refactor", "function", "class ", "docker", "linux", "bash", "powershell",
    "html", "css", "api", "algorithm", "bug", "compile",
)

_CYBER_KEYWORDS = (
    "owasp", "xss", "sqli", "sql injection", "csrf", "ssrf", "cve-", "cwe-",
    "vulnerability", "pentest", "bug bounty", "firewall", "siem", "log analysis",
    "http header", "csp", "hsts", "jwt", "nmap", "burp", "cybersecurity",
    "hardening", "malware", "phishing", "threat", "security audit",
)


def classify_task(message, image_path=None, document_context=None, web_context=None):
    """Classify the user's request to pick optimal provider order, temperature, and prompt focus."""
    if image_path:
        return "vision"
    if document_context:
        return "document"
    if web_context:
        return "web"

    lower = (message or "").lower()
    if any(k in lower for k in _CYBER_KEYWORDS):
        return "cybersecurity"
    if any(k in lower for k in _CODE_KEYWORDS) or "```" in lower:
        return "coding"
    if len(lower.split()) <= 10 and not any(w in lower for w in ("explain", "analyze", "compare", "write", "detailed", "summarize")):
        return "quick"
    return "general"


def get_task_temperature(task_type):
    if task_type in ("coding", "cybersecurity", "document"):
        return 0.25
    if task_type == "web":
        return 0.35
    if task_type == "vision":
        return 0.4
    return 0.7


def get_smart_provider_order(task_type, mode=None):
    """Return ordered list of provider keys based on mode and task type."""
    active_mode = (mode or PROVIDER_MODE).lower().strip()
    if active_mode != "auto":
        return [active_mode]

    # Vision requires multimodal support (Gemini first)
    if task_type == "vision":
        return ["gemini", "ollama", "groq"]

    # Quick short queries prioritize ultra-fast Groq if configured
    if task_type == "quick" and GROQ_API_KEY:
        return ["groq", "gemini", "ollama"]

    # Coding / Cybersecurity / Documents / General: Gemini -> Groq -> Ollama
    return ["gemini", "groq", "ollama"]


# ==========================================
# AUTO LONG-TERM MEMORY EXTRACTION (1.7)
# ==========================================

_MEMORY_PATTERNS = [
    (re.compile(r"\bmy name is ([A-Za-z][A-Za-z0-9 _-]{1,40})", re.IGNORECASE), "profile", "User's name is {0}"),
    (re.compile(r"\bcall me ([A-Za-z][A-Za-z0-9 _-]{1,30})", re.IGNORECASE), "profile", "User prefers to be called {0}"),
    (re.compile(r"\bi am a[n]? ([A-Za-z0-9 ,/_-]{3,60})", re.IGNORECASE), "profile", "User is a {0}"),
    (re.compile(r"\bi prefer ([^.!?\n]{4,100})", re.IGNORECASE), "preference", "User prefers {0}"),
    (re.compile(r"\bremember that ([^.!?\n]{4,160})", re.IGNORECASE), "note", "{0}"),
]


def extract_and_store_memories(message):
    """Automatically save explicit user preferences/facts into long-term memory."""
    text = (message or "").strip()
    if not text or len(text) > 400:
        return []
    saved = []
    for pattern, category, template in _MEMORY_PATTERNS:
        match = pattern.search(text)
        if match:
            captured = match.group(1).strip(" .,!?")
            if captured:
                fact = template.format(captured)
                add_long_term_memory(fact, category=category)
                saved.append(fact)
    return saved


def build_active_system_prompt(task_type="general", personality_override=None, style_override=None):
    memories = [(row[1], row[2]) for row in get_long_term_memories()[:25]]
    summary = get_session_summary()
    return build_system_prompt(
        personality=personality_override or CURRENT_PERSONALITY,
        response_style=style_override or CURRENT_RESPONSE_STYLE,
        language=CURRENT_LANGUAGE,
        task_type=task_type,
        long_term_memories=memories,
        conversation_summary=summary,
    )


# ==========================================
# CONVERSATION HISTORY
# ==========================================

def load_chat_history():
    saved_messages = get_recent_messages(limit=40)
    history = []

    for message_id, role, message, timestamp in saved_messages:
        if role not in ("user", "assistant"):
            continue
        history.append({"role": role, "content": message})

    return history


def get_gemini_history():
    saved_messages = load_chat_history()
    merged = []

    for item in saved_messages:
        gemini_role = "model" if item["role"] == "assistant" else "user"

        if not merged and gemini_role == "model":
            continue

        if merged and merged[-1]["role"] == gemini_role:
            merged[-1]["content"] += "\n" + item["content"]
        else:
            merged.append({"role": gemini_role, "content": item["content"]})

    return [
        types.Content(
            role=item["role"],
            parts=[types.Part.from_text(text=item["content"])]
        )
        for item in merged
    ]


def _build_image_part(image_path):
    path = Path(image_path)
    if not path.is_file():
        raise FileNotFoundError(f"Image file not found: {image_path}")
    mime_type, _ = mimetypes.guess_type(str(path))
    if not mime_type or not mime_type.startswith("image/"):
        mime_type = "image/png"
    data = path.read_bytes()
    return types.Part.from_bytes(data=data, mime_type=mime_type)


# ==========================================
# GEMINI AI
# ==========================================

def ask_gemini(message, system_prompt=None, temperature=0.7, image_path=None, include_history=True):
    global _gemini_quota_exhausted

    if not GEMINI_API_KEY or not gemini_client:
        raise RuntimeError("Gemini API key is not configured.")

    if _gemini_quota_exhausted and PROVIDER_MODE == "auto":
        raise RuntimeError("Gemini quota already exhausted in this session.")

    contents = get_gemini_history() if include_history else []
    user_parts = [types.Part.from_text(text=message)]
    if image_path:
        user_parts.append(_build_image_part(image_path))

    if contents and contents[-1].role == "user":
        contents[-1].parts.extend(user_parts)
    else:
        contents.append(types.Content(role="user", parts=user_parts))

    try:
        response = gemini_client.models.generate_content(
            model=GEMINI_MODEL,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt or build_active_system_prompt(),
                temperature=temperature,
            ),
        )

        answer = response.text
        if not answer:
            raise RuntimeError("Gemini returned an empty response.")

        _gemini_quota_exhausted = False
        return answer

    except Exception as error:
        error_text = str(error).lower()
        if "429" in error_text or "resource_exhausted" in error_text or "quota exceeded" in error_text:
            _gemini_quota_exhausted = True
        raise


# ==========================================
# GROQ AI
# ==========================================

def ask_groq(message, system_prompt=None, temperature=0.7, image_path=None, include_history=True):
    if not GROQ_API_KEY:
        raise RuntimeError("Groq API key is not configured.")

    if image_path:
        raise RuntimeError("Image understanding requires Gemini (multimodal vision).")

    from groq import Groq

    client = Groq(api_key=GROQ_API_KEY, timeout=45.0)

    messages = [{"role": "system", "content": system_prompt or build_active_system_prompt()}]
    if include_history:
        messages.extend(load_chat_history())
    messages.append({"role": "user", "content": message})

    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=messages,
        temperature=temperature,
        max_completion_tokens=2048,
    )

    answer = response.choices[0].message.content
    if not answer:
        raise RuntimeError("Groq returned an empty response.")
    return answer


# ==========================================
# OLLAMA LOCAL AI
# ==========================================

def ask_ollama(message, system_prompt=None, temperature=0.7, image_path=None, include_history=True):
    messages = [{"role": "system", "content": system_prompt or build_active_system_prompt()}]
    if include_history:
        messages.extend(load_chat_history())

    user_msg = {"role": "user", "content": message}
    if image_path:
        import base64
        user_msg["images"] = [base64.b64encode(Path(image_path).read_bytes()).decode("ascii")]
    messages.append(user_msg)

    response = requests.post(
        f"{OLLAMA_URL.rstrip('/')}/api/chat",
        json={
            "model": OLLAMA_MODEL,
            "messages": messages,
            "stream": False,
            "options": {"temperature": temperature},
        },
        timeout=180,
    )
    response.raise_for_status()

    data = response.json()
    answer = data.get("message", {}).get("content", "")
    if not answer:
        raise RuntimeError("Ollama returned an empty response.")
    return answer


# ==========================================
# STREAMING AI PROVIDERS
# ==========================================

def stream_gemini(message, system_prompt=None, temperature=0.7, image_path=None, include_history=True):
    global _gemini_quota_exhausted

    if not GEMINI_API_KEY or not gemini_client:
        raise RuntimeError("Gemini API key is not configured.")

    if _gemini_quota_exhausted and PROVIDER_MODE == "auto":
        raise RuntimeError("Gemini quota already exhausted.")

    contents = get_gemini_history() if include_history else []
    user_parts = [types.Part.from_text(text=message)]
    if image_path:
        user_parts.append(_build_image_part(image_path))

    if contents and contents[-1].role == "user":
        contents[-1].parts.extend(user_parts)
    else:
        contents.append(types.Content(role="user", parts=user_parts))

    try:
        response_stream = gemini_client.models.generate_content_stream(
            model=GEMINI_MODEL,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt or build_active_system_prompt(),
                temperature=temperature,
            ),
        )

        yielded_any = False
        for chunk in response_stream:
            try:
                text = chunk.text
            except ValueError:
                text = None
            if text:
                yielded_any = True
                yield text

        if yielded_any:
            _gemini_quota_exhausted = False

    except Exception as error:
        error_text = str(error).lower()
        if "429" in error_text or "resource_exhausted" in error_text or "quota exceeded" in error_text:
            _gemini_quota_exhausted = True
        raise


def stream_groq(message, system_prompt=None, temperature=0.7, image_path=None, include_history=True):
    if not GROQ_API_KEY:
        raise RuntimeError("Groq API key is not configured.")

    if image_path:
        raise RuntimeError("Image understanding requires Gemini (multimodal vision).")

    from groq import Groq

    client = Groq(api_key=GROQ_API_KEY, timeout=45.0)

    messages = [{"role": "system", "content": system_prompt or build_active_system_prompt()}]
    if include_history:
        messages.extend(load_chat_history())
    messages.append({"role": "user", "content": message})

    response_stream = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=messages,
        temperature=temperature,
        max_completion_tokens=2048,
        stream=True,
    )

    for chunk in response_stream:
        if not chunk.choices:
            continue
        text = chunk.choices[0].delta.content
        if text:
            yield text


def stream_ollama(message, system_prompt=None, temperature=0.7, image_path=None, include_history=True):
    messages = [{"role": "system", "content": system_prompt or build_active_system_prompt()}]
    if include_history:
        messages.extend(load_chat_history())

    user_msg = {"role": "user", "content": message}
    if image_path:
        import base64
        user_msg["images"] = [base64.b64encode(Path(image_path).read_bytes()).decode("ascii")]
    messages.append(user_msg)

    with requests.post(
        f"{OLLAMA_URL.rstrip('/')}/api/chat",
        json={
            "model": OLLAMA_MODEL,
            "messages": messages,
            "stream": True,
            "options": {"temperature": temperature},
        },
        stream=True,
        timeout=(10, 180),
    ) as response:
        response.raise_for_status()

        for line in response.iter_lines():
            if not line:
                continue
            if isinstance(line, bytes):
                line = line.decode("utf-8")
            data = json.loads(line)
            if data.get("error"):
                raise RuntimeError(data["error"])
            text = data.get("message", {}).get("content", "")
            if text:
                yield text


# ==========================================
# SAVE CONVERSATION
# ==========================================

def save_conversation(user_message, assistant_message):
    try:
        save_message("user", user_message)
        save_message("assistant", assistant_message)
    except Exception as error:
        print(f"[MEMORY ERROR] {error}")


# ==========================================
# MAIN AI PROVIDER MANAGER
# ==========================================

def ask_jarvis(
    message: str,
    image_path=None,
    document_context=None,
    web_context=None,
    personality_override=None,
    style_override=None,
    include_history=True,
    save_to_memory=True,
) -> str:
    global LAST_USED_PROVIDER, LAST_TASK_TYPE

    if not message or not message.strip():
        return "Please enter a message."

    task_type = classify_task(message, image_path=image_path, document_context=document_context, web_context=web_context)
    LAST_TASK_TYPE = task_type
    temperature = get_task_temperature(task_type)
    system_prompt = build_active_system_prompt(
        task_type=task_type,
        personality_override=personality_override,
        style_override=style_override,
    )

    prompt_text = message
    if document_context:
        prompt_text = f"{message}\n\n--- ATTACHED DOCUMENT CONTENT ---\n{document_context}"
    if web_context:
        prompt_text = f"{prompt_text}\n\n--- WEB SEARCH / EXTERNAL CONTEXT ---\n{web_context}"

    if save_to_memory:
        extract_and_store_memories(message)

    all_providers = {
        "gemini": ("Gemini", ask_gemini),
        "groq": ("Groq", ask_groq),
        "ollama": ("Ollama", ask_ollama),
    }

    mode = PROVIDER_MODE
    provider_keys = get_smart_provider_order(task_type, mode=mode)
    failures = []

    for key in provider_keys:
        provider_name, provider_function = all_providers[key]
        try:
            print(f"[JARVIS] Trying {provider_name} (task={task_type})...")
            answer = provider_function(
                prompt_text,
                system_prompt=system_prompt,
                temperature=temperature,
                image_path=image_path,
                include_history=include_history,
            )

            if not answer or not answer.strip():
                raise RuntimeError("Empty AI response.")

            if save_to_memory:
                save_conversation(message, answer)

            LAST_USED_PROVIDER = provider_name
            print(f"[JARVIS] Response generated by {provider_name}.")
            return f"[{provider_name} | {task_type}]\n\n{answer}"

        except Exception as error:
            print(f"[{provider_name} ERROR] {error}")
            failures.append(f"{provider_name}: {str(error)[:250]}")
            if mode != "auto":
                break

    failure_details = "\n".join(failures)
    return (
        "I'm unable to connect to the selected AI provider(s).\n\n"
        f"Provider errors:\n{failure_details}\n\n"
        "Please check your API keys, internet connection, and Ollama service."
    )


# ==========================================
# MAIN STREAMING MANAGER
# ==========================================

def stream_jarvis(
    message,
    on_chunk,
    on_reset,
    image_path=None,
    document_context=None,
    web_context=None,
    personality_override=None,
    style_override=None,
    include_history=True,
    save_to_memory=True,
):
    global LAST_USED_PROVIDER, LAST_TASK_TYPE

    if not message or not message.strip():
        raise ValueError("Please enter a message.")

    task_type = classify_task(message, image_path=image_path, document_context=document_context, web_context=web_context)
    LAST_TASK_TYPE = task_type
    temperature = get_task_temperature(task_type)
    system_prompt = build_active_system_prompt(
        task_type=task_type,
        personality_override=personality_override,
        style_override=style_override,
    )

    prompt_text = message
    if document_context:
        prompt_text = f"{message}\n\n--- ATTACHED DOCUMENT CONTENT ---\n{document_context}"
    if web_context:
        prompt_text = f"{prompt_text}\n\n--- WEB SEARCH / EXTERNAL CONTEXT ---\n{web_context}"

    if save_to_memory:
        extract_and_store_memories(message)

    all_providers = {
        "gemini": ("Gemini", stream_gemini),
        "groq": ("Groq", stream_groq),
        "ollama": ("Ollama", stream_ollama),
    }

    mode = PROVIDER_MODE
    provider_keys = get_smart_provider_order(task_type, mode=mode)
    failures = []

    for key in provider_keys:
        provider_name, provider_function = all_providers[key]
        full_response = ""
        received_chunks = False

        try:
            print(f"[JARVIS] Streaming with {provider_name} (task={task_type})...")

            for chunk in provider_function(
                prompt_text,
                system_prompt=system_prompt,
                temperature=temperature,
                image_path=image_path,
                include_history=include_history,
            ):
                if not chunk:
                    continue
                received_chunks = True
                full_response += chunk
                on_chunk(chunk)

            if not full_response.strip():
                raise RuntimeError("Provider returned an empty response.")

            if save_to_memory:
                save_conversation(message, full_response)

            LAST_USED_PROVIDER = provider_name
            print(f"[JARVIS] Stream completed by {provider_name}.")
            return f"{provider_name} ({task_type})", full_response

        except Exception as error:
            print(f"[{provider_name} STREAM ERROR] {error}")
            failures.append(f"{provider_name}: {str(error)[:250]}")

            if received_chunks:
                on_reset()

            if mode != "auto":
                break

            print("[JARVIS] Switching to next provider...")

    failure_details = "\n".join(failures)
    raise RuntimeError(
        "All selected AI providers failed.\n\n"
        f"{failure_details}\n\n"
        "Check your API keys, internet connection, and Ollama service."
    )


# ==========================================
# CONVERSATION SUMMARIZATION (1.6)
# ==========================================

def summarize_conversation(session_id=None):
    """Summarize the current or given conversation session and persist it."""
    rows = get_recent_messages(limit=60, session_id=session_id)
    if not rows:
        return "No messages in this conversation to summarize yet."

    transcript = "\n".join(f"{role.upper()}: {msg}" for _, role, msg, _ in rows)
    prompt = (
        "Summarize the following conversation concisely into:\n"
        "1. Main Topic / Goal\n"
        "2. Key Decisions or Answers\n"
        "3. Open Follow-ups / Action Items\n\n"
        f"{transcript[:14000]}"
    )

    result = ask_jarvis(
        prompt,
        personality_override="EXECUTIVE",
        style_override="Bullet Points",
        include_history=False,
        save_to_memory=False,
    )
    # Strip provider tag header before storing summary
    clean = re.sub(r"^\[[^\]]+\]\s*", "", result).strip()
    save_session_summary(clean, session_id=session_id)
    return clean


# ==========================================
# NEW CONVERSATION SUPPORT
# ==========================================

def start_new_chat():
    return True


# ==========================================
# PROVIDER HEALTH CHECK
# ==========================================

def check_provider_health(provider):
    import urllib.request
    import urllib.error

    provider = (provider or "").lower().strip()

    def request_json(url, headers=None):
        request_headers = {
            "User-Agent": "JARVIS-AI-Assistant/2.0",
            "Accept": "application/json",
        }
        if headers:
            request_headers.update(headers)
        req = urllib.request.Request(url, headers=request_headers, method="GET")
        with urllib.request.urlopen(req, timeout=10) as response:
            return json.loads(response.read().decode("utf-8"))

    try:
        if provider == "gemini":
            if not GEMINI_API_KEY:
                return "GEMINI", False, "API key is missing."
            url = "https://generativelanguage.googleapis.com/v1beta/models"
            data = request_json(url, {"x-goog-api-key": GEMINI_API_KEY})
            available_models = [
                model.get("name", "").replace("models/", "")
                for model in data.get("models", [])
            ]
            if GEMINI_MODEL in available_models:
                return "GEMINI", True, f"{GEMINI_MODEL} is available."
            return "GEMINI", False, f"{GEMINI_MODEL} was not found."

        elif provider == "groq":
            if not GROQ_API_KEY:
                return "GROQ", False, "API key is missing."
            url = "https://api.groq.com/openai/v1/models"
            data = request_json(url, {"Authorization": f"Bearer {GROQ_API_KEY}"})
            available_models = [model.get("id", "") for model in data.get("data", [])]
            if GROQ_MODEL in available_models:
                return "GROQ", True, f"{GROQ_MODEL} is available."
            return "GROQ", False, f"{GROQ_MODEL} was not found."

        elif provider == "ollama":
            url = f"{OLLAMA_URL.rstrip('/')}/api/tags"
            data = request_json(url)
            available_models = [model.get("name", "") for model in data.get("models", [])]
            if OLLAMA_MODEL in available_models or f"{OLLAMA_MODEL}:latest" in available_models:
                return "OLLAMA", True, f"{OLLAMA_MODEL} is installed."
            return "OLLAMA", False, f"{OLLAMA_MODEL} is not installed."

        else:
            return "UNKNOWN", False, "Invalid provider name."

    except urllib.error.HTTPError as error:
        details = error.read().decode("utf-8", errors="replace")
        return provider.upper(), False, f"HTTP {error.code}: {details[:500]}"

    except urllib.error.URLError:
        return provider.upper(), False, "Could not connect to the provider."

    except Exception as error:
        return provider.upper(), False, f"Check failed: {type(error).__name__}: {error}"
