"""Low-latency Prefetch TTS Engine for JARVIS & ULTRON (Zero-Pause Pipeline)."""

import asyncio
import html
import os
import queue
import re
import tempfile
import threading
import edge_tts
import pygame

from core.memory import get_setting, set_setting


VOICE_PRESETS = {
    "JARVIS (British - Ryan)": {"voice": "en-GB-RyanNeural", "pitch": "+0Hz"},
    "JARVIS (British - Thomas)": {"voice": "en-GB-ThomasNeural", "pitch": "+0Hz"},
    "ULTRON (Deep - Christopher)": {"voice": "en-US-ChristopherNeural", "pitch": "-6Hz"},
    "Classic (US - Guy)": {"voice": "en-US-GuyNeural", "pitch": "+0Hz"},
    "FRIDAY (Irish - Emily)": {"voice": "en-IE-EmilyNeural", "pitch": "+0Hz"},
}

SPEED_PRESETS = {
    "Normal (+0%)": "+0%",
    "Crisp (+12%)": "+12%",
    "Fast / Natural (+18%)": "+18%",
    "Rapid (+26%)": "+26%",
    "Turbo (+35%)": "+35%",
}

EMOJI_PATTERN = re.compile(
    "["
    "\U0001F600-\U0001F64F"  # emoticons
    "\U0001F300-\U0001F5FF"  # misc symbols and pictographs
    "\U0001F680-\U0001F6FF"  # transport and map
    "\U0001F700-\U0001F77F"  # alchemical symbols
    "\U0001F780-\U0001F7FF"  # Geometric Shapes Extended
    "\U0001F800-\U0001F8FF"  # Supplemental Arrows-C
    "\U0001F900-\U0001F9FF"  # Supplemental Symbols and Pictographs
    "\U0001FA00-\U0001FA6F"  # Chess Symbols
    "\U0001FA70-\U0001FAFF"  # Symbols and Pictographs Extended-A
    "\U00002700-\U000027BF"  # Dingbats
    "\U00002600-\U000026FF"  # Misc symbols (sun, umbrella, warning, etc.)
    "\U00002300-\U000023FF"  # Misc technical
    "\U00002B50-\U00002B55"  # Stars, etc.
    "\U0000200D"              # Zero-width joiner
    "\U0000FE0E-\U0000FE0F"  # Variation selectors
    "]+",
    flags=re.UNICODE,
)


def clean_text_for_speech(text: str) -> str:
    """Strip markdown, URLs, emojis, brackets, and code fences so TTS speaks smoothly and naturally."""
    if not text:
        return ""
    s = str(text)
    s = html.unescape(s)

    # 1. Remove fenced code blocks completely
    s = re.sub(r"```[\s\S]*?```", " ", s)

    # 2. Inline code - strip backticks, keep readable text
    s = re.sub(r"`+([^`\n]+)`+", r" \1 ", s)
    s = s.replace("`", " ")

    # 3. Action tags & system directives [ACTION: ...], [WHATSAPP: ...], etc.
    s = re.sub(r"\[\s*[A-Z_]{2,}\b[^\]]*\]", " ", s)
    s = re.sub(r"\[\s*[A-Za-z0-9_-]+\s*[:|][^\]]*\]", " ", s)

    # 4. Strip citations and references in brackets: [1], [2, 3], [1-4], [^1], [citation needed], [source], [ref]
    s = re.sub(
        r"\[\s*(?:\^?\d+(?:\s*[,-]\s*\d+)*|citation\s+needed|source|ref|reference)\s*\]",
        " ",
        s,
        flags=re.IGNORECASE,
    )

    # 5. Markdown images ![alt](url) -> remove completely
    s = re.sub(r"!\[[^\]]*\]\([^\)]*\)", " ", s)

    # 6. Markdown links [text](url) -> keep only clean anchor text
    s = re.sub(r"\[([^\]]+)\]\([^\)]*\)", r" \1 ", s)

    # 7. Remove parenthetical URLs / citations entirely:
    # e.g., "(see https://...)", "(https://...)", "(source: www.google.com)", "(web.whatsapp.com)"
    s = re.sub(
        r"\([^)]*(?:https?://|www\.|(?:\b[a-zA-Z0-9-]+\.)+(?:com|org|net|io|ai|co|in|edu|gov|ly|dev|app)\b)[^)]*\)",
        " ",
        s,
        flags=re.IGNORECASE,
    )

    # 8. Autolink angle brackets <https://...> or <email@domain.com>
    s = re.sub(r"<\s*https?://[^>]+>", " ", s)
    s = re.sub(r"<\s*[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+\s*>", " ", s)

    # 9. Email addresses (must run before bare domain matching so address isn't partially truncated)
    s = re.sub(r"\b[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+\b", " ", s)
    s = s.replace("@", " ")

    # 10. Protocol URLs (http, https, ftp, file)
    s = re.sub(r"\b(?:https?|ftp|file)://[^\s)\]}>,;\"']+", " ", s)

    # 11. Bare www URLs
    s = re.sub(r"\bwww\.[a-zA-Z0-9-]+\.[a-zA-Z0-9-.\/?%&=_#+~@!$,;:]*", " ", s)

    # 12. Standalone domain-like URLs (e.g. google.com/search, web.whatsapp.com, github.com/user/repo, bit.ly/abc)
    s = re.sub(
        r"\b(?:[a-zA-Z0-9-]+\.)+(?:com|org|net|edu|gov|io|ai|co|in|dev|app|me|info|ly)\b(?:/[^\s)\]}>,;\"']*)?",
        " ",
        s,
        flags=re.IGNORECASE,
    )

    # 13. Markdown table divider lines |---|---|
    s = re.sub(r"\|(?:\s*[-:]+[-| :]*)\|", " ", s)

    # 14. Markdown horizontal rules ---, ***, ___
    s = re.sub(r"^[ \t]*[-*_]{3,}[ \t]*$", " ", s, flags=re.MULTILINE)

    # 15. Markdown headers # Title -> Title
    s = re.sub(r"^\s*#{1,6}\s+", "", s, flags=re.MULTILINE)

    # 16. HTML tags (<br>, <span>, etc.)
    s = re.sub(r"<br\s*/?>", "\n", s, flags=re.IGNORECASE)
    s = re.sub(r"<[^>]+>", " ", s)

    # 17. Emojis and unicode pictographs
    s = EMOJI_PATTERN.sub(" ", s)

    # 18. Bullets, list markers, arrows, and decorative symbols
    s = re.sub(r"^\s*[-*+•▸→➤]+\s+", "", s, flags=re.MULTILINE)
    s = re.sub(r"[→←↑↓⇒▶▲▼■□●○★☆✓✔✕✖]", " ", s)

    # 19. Markdown bold / italics / strikethrough markers (*, ~, and isolated _)
    s = re.sub(r"[*~]+", "", s)
    # Underscores: replace lone underscores in snake_case with spaces so "run_jarvis" -> "run jarvis"
    s = s.replace("_", " ")

    # 20. Backslashes in paths -> replace with space so TTS does not say "backslash"
    s = s.replace("\\", " ")

    # 21. Replace table column pipes with natural comma pause
    s = s.replace("|", ", ")

    # 22. Brackets, parentheses, braces, chevrons:
    # Parentheses become natural comma pause
    s = re.sub(r"\s*\(\s*", ", ", s)
    s = re.sub(r"\s*\)\s*", ", ", s)
    # Remaining square brackets, curly braces, and angle brackets become spaces
    s = re.sub(r"[\[\]{}<>]", " ", s)

    # 23. Punctuation cleanup and normalization:
    # Remove comma if preceded by another punctuation mark (e.g., "!," -> "!")
    s = re.sub(r"([.!?])\s*,\s*", r"\1 ", s)
    # Remove multiple commas
    s = re.sub(r",\s*,+", ", ", s)
    # Remove comma directly before sentence-ending punctuation (e.g., ",." -> ".")
    s = re.sub(r",\s*([.!?])", r"\1", s)
    # Normalize long ellipsis
    s = re.sub(r"\.{4,}", "...", s)
    # Remove space before punctuation marks
    s = re.sub(r"\s+([,.!?;:])", r"\1", s)
    # Collapse multiple spaces
    s = re.sub(r"[ \t]+", " ", s)
    # Strip leading/trailing punctuation and spaces
    s = s.strip(" \t\n,;:-")
    return s


class JarvisTTS:
    """Two-stage async prefetch + immediate playback TTS engine (eliminates inter-sentence gaps)."""

    def __init__(self):
        saved_voice = get_setting("tts_voice", "en-GB-RyanNeural") or "en-GB-RyanNeural"
        saved_rate = get_setting("tts_rate", "+18%") or "+18%"
        saved_pitch = get_setting("tts_pitch", "+0Hz") or "+0Hz"

        self.voice = saved_voice
        self.rate = saved_rate
        self.pitch = saved_pitch

        self.text_queue = queue.Queue()
        self.audio_queue = queue.Queue(maxsize=4)

        self.running = True
        self.generation = 0
        self.lock = threading.Lock()
        self.audio_available = False
        self._is_speaking = False

        try:
            pygame.mixer.init(frequency=24000, buffer=1024)
            self.audio_available = True
        except Exception as error:
            print(f"[TTS WARNING] Audio output unavailable: {error}")

        # Stage 1: Prefetch synthesizer thread (runs ahead of playback)
        self.synth_thread = threading.Thread(
            target=self._synth_loop,
            daemon=True,
            name="JarvisTTS-Synth",
        )
        # Stage 2: Playback thread (plays prefetched audio back-to-back with zero gap)
        self.play_thread = threading.Thread(
            target=self._play_loop,
            daemon=True,
            name="JarvisTTS-Play",
        )

        self.synth_thread.start()
        self.play_thread.start()

    @property
    def is_speaking(self):
        return self._is_speaking

    def set_voice_profile(self, voice: str, pitch: str = "+0Hz"):
        with self.lock:
            self.voice = voice
            self.pitch = pitch
        set_setting("tts_voice", voice)
        set_setting("tts_pitch", pitch)

    def set_rate(self, rate: str):
        with self.lock:
            self.rate = rate
        set_setting("tts_rate", rate)

    def speak(self, text):
        if not self.audio_available:
            return

        cleaned = clean_text_for_speech(text)
        if not cleaned or len(cleaned) < 2:
            return

        with self.lock:
            if not self.running:
                return
            current_gen = self.generation

        self.text_queue.put((cleaned, current_gen))

    def clear(self):
        with self.lock:
            self.generation += 1
            self._is_speaking = False
            if self.audio_available:
                try:
                    pygame.mixer.music.stop()
                except Exception:
                    pass

        # Drain pending texts
        while True:
            try:
                self.text_queue.get_nowait()
                self.text_queue.task_done()
            except queue.Empty:
                break

        # Drain and delete any prefetched audio files
        while True:
            try:
                item = self.audio_queue.get_nowait()
                self.audio_queue.task_done()
                if item is not None:
                    audio_path, _ = item
                    self._safe_remove(audio_path)
            except queue.Empty:
                break

    @staticmethod
    def _safe_remove(path):
        if path and os.path.exists(path):
            try:
                os.remove(path)
            except OSError:
                pass

    def _synth_loop(self):
        """Persistent asyncio loop that synthesizes upcoming sentences while current one plays."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            while True:
                item = self.text_queue.get()
                try:
                    if item is None:
                        break

                    text, gen = item

                    with self.lock:
                        if not self.running:
                            break
                        if gen != self.generation:
                            continue
                        voice = self.voice
                        rate = self.rate
                        pitch = self.pitch

                    audio_path = loop.run_until_complete(
                        self._synthesize_to_file(text, voice, rate, pitch)
                    )

                    if not audio_path:
                        continue

                    with self.lock:
                        stale = (not self.running) or (gen != self.generation)

                    if stale:
                        self._safe_remove(audio_path)
                        continue

                    self.audio_queue.put((audio_path, gen))

                except Exception as error:
                    print(f"[TTS SYNTH ERROR] {error}")
                finally:
                    self.text_queue.task_done()
        finally:
            try:
                loop.close()
            except Exception:
                pass

    async def _synthesize_to_file(self, text: str, voice: str, rate: str, pitch: str):
        audio_path = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tf:
                audio_path = tf.name

            communicate = edge_tts.Communicate(
                text=text,
                voice=voice,
                rate=rate,
                pitch=pitch,
            )
            await communicate.save(audio_path)

            if os.path.getsize(audio_path) == 0:
                self._safe_remove(audio_path)
                return None

            return audio_path
        except Exception:
            self._safe_remove(audio_path)
            raise

    def _play_loop(self):
        """Plays prefetched audio files continuously with ~20ms transition latency."""
        while True:
            item = self.audio_queue.get()
            audio_path = None
            loaded = False
            try:
                if item is None:
                    break

                audio_path, gen = item

                with self.lock:
                    if not self.running:
                        break
                    if gen != self.generation or not self.audio_available:
                        continue
                    pygame.mixer.music.load(audio_path)
                    loaded = True
                    self._is_speaking = True
                    pygame.mixer.music.play()

                # Tight 20ms poll for seamless back-to-back sentence flow
                while pygame.mixer.music.get_busy():
                    with self.lock:
                        if not self.running or gen != self.generation:
                            pygame.mixer.music.stop()
                            break
                    threading.Event().wait(0.02)

            except Exception as error:
                print(f"[TTS PLAY ERROR] {error}")
            finally:
                with self.lock:
                    if self.audio_queue.empty():
                        self._is_speaking = False
                    if loaded and self.audio_available:
                        try:
                            pygame.mixer.music.stop()
                            pygame.mixer.music.unload()
                        except Exception:
                            pass
                self._safe_remove(audio_path)
                self.audio_queue.task_done()

    def stop(self):
        with self.lock:
            if not self.running:
                return
            self.running = False
            self.generation += 1
            self._is_speaking = False
            if self.audio_available:
                try:
                    pygame.mixer.music.stop()
                except Exception:
                    pass

        self.text_queue.put(None)
        try:
            self.audio_queue.put_nowait(None)
        except queue.Full:
            self.clear()
            self.audio_queue.put(None)

    def shutdown(self):
        self.stop()
        self.synth_thread.join(timeout=4)
        self.play_thread.join(timeout=4)
        if self.audio_available and not self.play_thread.is_alive():
            try:
                pygame.mixer.quit()
            except Exception:
                pass
