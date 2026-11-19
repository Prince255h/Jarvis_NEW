"""Quick standalone Edge-TTS test script."""

import asyncio
import edge_tts


async def main():
    text = "Hello! I am JARVIS. Your personal AI assistant. How can I help you today?"
    voice = "en-GB-RyanNeural"
    communicate = edge_tts.Communicate(text, voice, rate="+18%")
    await communicate.save("jarvis_test.mp3")
    print("Speech generated successfully!")


if __name__ == "__main__":
    asyncio.run(main())
