"""Voice input interface module (extensible hook for optional microphone STT backends)."""


def is_voice_input_available() -> bool:
    """Return True if an optional speech_recognition backend is installed."""
    try:
        import speech_recognition  # noqa: F401
        return True
    except ImportError:
        return False


def listen_once(timeout: int = 5) -> str:
    """Capture a single spoken utterance when optional SpeechRecognition + PyAudio are installed."""
    try:
        import speech_recognition as sr
    except ImportError as exc:
        raise RuntimeError(
            "Voice input requires optional packages 'SpeechRecognition' and 'PyAudio'."
        ) from exc

    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        audio = recognizer.listen(source, timeout=timeout)
    return recognizer.recognize_google(audio)

