"""Procedural Stark HUD Sound Effects Engine using numpy + pygame.mixer (Zero external audio files)."""

import numpy as np
import pygame

from core.memory import get_setting, set_setting


class HUDSoundFX:
    """Generates subtle, cinema-grade Stark HUD chimes and tactile micro-clicks."""

    def __init__(self):
        self.enabled = (get_setting("sfx_enabled", "true") or "true").lower() == "true"
        self.sample_rate = 24000
        self._sounds = {}
        self._ready = False
        self._init_sounds()

    def _init_sounds(self):
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=self.sample_rate, size=-16, channels=2, buffer=512)
            self._sounds["boot"] = self._make_chord([440.0, 554.37, 659.25, 880.0], duration=0.45, volume=0.14)
            self._sounds["click"] = self._make_tone(920.0, duration=0.035, volume=0.07, sweep_to=1240.0)
            self._sounds["pulse"] = self._make_tone(260.0, duration=0.22, volume=0.12, sweep_to=520.0)
            self._sounds["alert"] = self._make_chord([587.33, 880.0], duration=0.28, volume=0.15)
            self._ready = True
        except Exception as err:
            print(f"[SFX WARNING] HUD sound effects unavailable: {err}")
            self._ready = False

    def _to_sound(self, mono_wave: np.ndarray):
        clipped = np.clip(mono_wave, -1.0, 1.0)
        pcm = (clipped * 32767).astype(np.int16)
        stereo = np.column_stack((pcm, pcm))
        return pygame.sndarray.make_sound(stereo)

    def _make_tone(self, freq: float, duration: float, volume: float = 0.1, sweep_to: float = None):
        n = max(1, int(self.sample_rate * duration))
        t = np.linspace(0.0, duration, n, endpoint=False)
        if sweep_to is not None:
            freqs = np.linspace(freq, sweep_to, n)
            phase = 2.0 * np.pi * np.cumsum(freqs) / self.sample_rate
        else:
            phase = 2.0 * np.pi * freq * t
        env = np.sin(np.pi * np.linspace(0.0, 1.0, n)) ** 1.3
        wave = np.sin(phase) * env * volume
        return self._to_sound(wave)

    def _make_chord(self, freqs: list[float], duration: float, volume: float = 0.12):
        n = max(1, int(self.sample_rate * duration))
        t = np.linspace(0.0, duration, n, endpoint=False)
        wave = np.zeros(n, dtype=np.float64)
        for idx, f in enumerate(freqs):
            delay = idx * 0.04
            mask = t >= delay
            local_t = np.where(mask, t - delay, 0.0)
            env = np.where(mask, np.exp(-local_t * 6.5) * np.minimum(1.0, local_t / 0.015), 0.0)
            wave += np.sin(2.0 * np.pi * f * local_t) * env
        wave = (wave / max(1, len(freqs))) * volume
        return self._to_sound(wave)

    def set_enabled(self, enabled: bool):
        self.enabled = bool(enabled)
        set_setting("sfx_enabled", "true" if self.enabled else "false")

    def play(self, name: str):
        if not self.enabled or not self._ready:
            return
        snd = self._sounds.get(name)
        if snd is not None:
            try:
                snd.play()
            except Exception:
                pass

    def shutdown(self):
        self._ready = False
        self._sounds.clear()


hud_sfx = HUDSoundFX()

