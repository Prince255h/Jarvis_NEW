
import time
from core.tts import JarvisTTS

tts = JarvisTTS()

tts.speak(
    "Hello! I am JARVIS. "
    "My speech engine is now integrated."
)

print("Speech queued successfully.")

time.sleep(12)

tts.shutdown()

print("TTS test completed.")
