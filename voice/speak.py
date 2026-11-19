"""Voice output wrapper delegating to JarvisTTS prefetch engine."""

from core.tts import JarvisTTS, clean_text_for_speech

__all__ = ["JarvisTTS", "clean_text_for_speech"]

