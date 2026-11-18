
import asyncio
import edge_tts


async def main():
    text = "Hello! I am JARVIS. Your personal AI assistant. How can I help you today?"

    voice = "en-US-GuyNeural"

    communicate = edge_tts.Communicate(text, voice)

    await communicate.save("jarvis_test.mp3")

    print("Speech generated successfully!")


asyncio.run(main())
