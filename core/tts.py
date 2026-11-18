
import asyncio
import edge_tts
import pygame
import os
import tempfile
import threading
import queue


class JarvisTTS:

    def __init__(self):

        self.voice = "en-US-GuyNeural"

        self.speech_queue = queue.Queue()
        self.running = True

        self.generation = 0
        self.lock = threading.Lock()
        self.audio_available = False
        self._is_speaking = False

        try:
            pygame.mixer.init()
            self.audio_available = True
        except Exception as error:
            print(f"[TTS WARNING] Audio output unavailable: {error}")

        self.thread = threading.Thread(
            target=self._speech_loop,
            daemon=True
        )

        self.thread.start()

    @property
    def is_speaking(self):
        return self._is_speaking

    def speak(self, text):

        if not self.audio_available or not text or not text.strip():
            return

        with self.lock:

            if not self.running:
                return

            current_generation = self.generation

        self.speech_queue.put(
            (text.strip(), current_generation)
        )

    def clear(self):

        with self.lock:
            self.generation += 1

            # Stop audio currently playing.
            if self.audio_available:
                try:
                    pygame.mixer.music.stop()
                except Exception:
                    pass

        # Remove sentences that have not started playing.
        while True:
            try:
                self.speech_queue.get_nowait()
                self.speech_queue.task_done()

            except queue.Empty:
                break

    def _speech_loop(self):

        while True:

            item = self.speech_queue.get()

            try:

                if item is None:
                    break

                text, generation = item

                with self.lock:
                    if not self.running:
                        break

                    if generation != self.generation:
                        continue

                asyncio.run(
                    self._generate_and_play(text, generation)
                )

            except Exception as error:
                print("[TTS ERROR]", error)

            finally:
                self.speech_queue.task_done()

    async def _generate_and_play(self, text, generation):

        if not self.audio_available:
            return

        audio_path = None
        loaded = False

        try:

            with tempfile.NamedTemporaryFile(
                suffix=".mp3",
                delete=False
            ) as temp_file:

                audio_path = temp_file.name

            communicate = edge_tts.Communicate(
                text,
                self.voice
            )

            await communicate.save(audio_path)

            with self.lock:

                if not self.running:
                    return

                if generation != self.generation:
                    return

                pygame.mixer.music.load(audio_path)
                loaded = True
                self._is_speaking = True
                pygame.mixer.music.play()

            while pygame.mixer.music.get_busy():

                with self.lock:

                    if not self.running:
                        pygame.mixer.music.stop()
                        break

                    if generation != self.generation:
                        pygame.mixer.music.stop()
                        break

                await asyncio.sleep(0.1)

        finally:

            self._is_speaking = False

            if loaded and self.audio_available:
                try:
                    pygame.mixer.music.stop()
                    pygame.mixer.music.unload()
                except Exception:
                    pass

            if audio_path and os.path.exists(audio_path):
                try:
                    os.remove(audio_path)
                except OSError:
                    pass

    def stop(self):

        with self.lock:
            if not self.running:
                return

            self.running = False
            self.generation += 1

            if self.audio_available:
                try:
                    pygame.mixer.music.stop()
                except Exception:
                    pass

        self.speech_queue.put(None)

    def shutdown(self):

        self.stop()

        self.thread.join(timeout=10)

        if self.audio_available and not self.thread.is_alive():
            try:
                pygame.mixer.quit()
            except Exception:
                pass
