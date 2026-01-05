"""
Simple example demonstrating non-streaming chat completions.
"""

from pi169 import Alpie, ChatMessage
from pi169.exceptions import AlpieError
import os

def main():
    api_key = "ALPIE_API_KEY"  # Replace with your actual API key or fetch from environment
    if not api_key:
        print("Please set ALPIE_API_KEY environment variable")
        print("Example: export ALPIE_API_KEY='your-api-key-here'")
        return
    
    client = Alpie(api_key=api_key)
    
    print("Alpie SDK - Simple Chat Example")
    print("=" * 50)
    
    try:
        response = client.chat.completions.create(
            model="alpie-32b",
            messages=[
                ChatMessage(role="system", content="You are a helpful assistant."),
                ChatMessage(role="user", content="What is Python? Give a brief answer.")
            ],
            max_tokens=200
        )
        
        print(f"\nModel: {response.model}")
        print(f"Response: {response.choices[0].message.content}")
        
        if response.usage:
            print(f"\nToken Usage:")
            print(f"  Prompt: {response.usage.prompt_tokens}")
            print(f"  Completion: {response.usage.completion_tokens}")
            print(f"  Total: {response.usage.total_tokens}")
    
    except AlpieError as e:
        print(f"Error: {e.message}")

if __name__ == "__main__":
    main()
