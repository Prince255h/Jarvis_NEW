"""Low-latency Prefetch TTS Engine for JARVIS & ULTRON (Zero-Pause Pipeline)."""

import asyncio
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


def clean_text_for_speech(text: str) -> str:
    """Strip markdown, URLs, and code fences so TTS speaks smoothly without awkward pauses."""
    if not text:
        return ""
    s = str(text)
    # Remove fenced code blocks completely
    s = re.sub(r"```[\s\S]*?```", " ", s)
    # Remove URLs
    s = re.sub(r"https?://\S+", "", s)
    # Unwrap markdown links [label](url) -> label
    s = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", s)
    # Remove markdown formatting characters
    s = re.sub(r"[`*_#~>|]", " ", s)
    # Replace bullet/dash prefixes cleanly
    s = re.sub(r"^\s*[-▸•]+\s*", "", s, flags=re.MULTILINE)
    # Collapse whitespace
    s = re.sub(r"\s+", " ", s).strip()
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
