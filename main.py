
from core.brain import ask_jarvis


def main():

    print("=" * 45)
    print("       J.A.R.V.I.S. AI SYSTEM")
    print("=" * 45)

    print("\nJARVIS: Systems online. How may I assist you?")

    while True:

        user_input = input("\nYOU: ").strip()

        if user_input.lower() == "exit":
            print("JARVIS: Shutting down. Goodbye!")
            break

        if not user_input:
            continue

        response = ask_jarvis(user_input)

        print(f"\nJARVIS: {response}")


if __name__ == "__main__":
    main()