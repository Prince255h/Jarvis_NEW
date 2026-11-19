"""Standalone test harness for JarvisTTS prefetch playback engine."""

import time
from core.tts import JarvisTTS


def main():
    tts = JarvisTTS()
    tts.speak(
        "Hello! I am JARVIS. "
        "My low-latency prefetch speech engine is now integrated."
    )
    print("Speech queued successfully.")
    time.sleep(8)
    tts.shutdown()
    print("TTS test completed.")


if __name__ == "__main__":
    main()
