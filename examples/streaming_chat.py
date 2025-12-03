"""
Interactive CLI example for streaming chat completions.
"""

from alpie import Alpie, ChatMessage
from alpie.exceptions import AlpieError
import os

def main():
    api_key = os.getenv("ALPIE_API_KEY")
    if not api_key:
        print("Please set ALPIE_API_KEY environment variable")
        print("Example (PowerShell):  $env:ALPIE_API_KEY='your-key'")
        return

    client = Alpie(api_key=api_key)

    print("\nAlpie SDK - Interactive Chat")
    print("=" * 50)

    # Optional system message
    system_prompt = ChatMessage(
        role="system", 
        content="You are a helpful assistant."
    )

    while True:
        user_input = input("\nYou: ")
        if user_input.lower() in ["exit", "quit"]:
            print("Goodbye!")
            break

        try:
            print("Assistant: ", end="", flush=True)

            stream = client.chat.completions.create(
                model="alpie-32b",
                messages=[
                    system_prompt,
                    ChatMessage(role="user", content=user_input)
                ],
                max_tokens=500,
                stream=True
            )

            # Stream tokens
            for chunk in stream:
                if chunk.delta_content:
                    print(chunk.delta_content, end="", flush=True)

            print()  # newline after response

        except AlpieError as e:
            print(f"\nError: {e.message}")

if __name__ == "__main__":
    main()
