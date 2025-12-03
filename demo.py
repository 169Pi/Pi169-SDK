"""
Demo script showcasing the Alpie SDK features.

This demo shows:
1. SDK initialization
2. Non-streaming chat completion
3. Streaming chat completion
4. Error handling

To run with your API key:
  export ALPIE_API_KEY='your-api-key-here'
  python demo.py
"""

from alpie import Alpie, ChatMessage
from alpie.exceptions import AlpieError, ValidationError
import os
import sys

def demo_initialization():
    """Demo: Client initialization"""
    print("\n" + "=" * 60)
    print("1. CLIENT INITIALIZATION")
    print("=" * 60)
    
    api_key = os.getenv("ALPIE_API_KEY", "demo-key-for-testing")
    
    client = Alpie(
        api_key=api_key,
        timeout=60.0
    )
    
    print(f"✓ Client initialized successfully")
    print(f"  Base URL: {client.base_url}")
    print(f"  Timeout: {client.timeout}s")
    
    return client

def demo_non_streaming(client):
    """Demo: Non-streaming chat completion"""
    print("\n" + "=" * 60)
    print("2. NON-STREAMING CHAT COMPLETION")
    print("=" * 60)
    
    print("\nSending request to API...")
    print("Note: This demo requires a valid API key set in ALPIE_API_KEY")
    print("If you see an authentication error, that's expected without a real key.")
    
    try:
        response = client.chat.completions.create(
            model="alpie-32b",
            messages=[
                ChatMessage(role="system", content="You are a helpful assistant."),
                ChatMessage(role="user", content="Say hello in one sentence.")
            ],
            max_tokens=100
        )
        
        print(f"\n✓ Response received!")
        print(f"  Model: {response.model}")
        print(f"  Content: {response.choices[0].message.content}")
        
        if response.usage:
            print(f"  Tokens used: {response.usage.total_tokens}")
    
    except AlpieError as e:
        print(f"\n✗ Expected error (demo mode): {e.message}")
        print(f"  Status code: {e.status_code}")

def demo_streaming(client):
    """Demo: Streaming chat completion"""
    print("\n" + "=" * 60)
    print("3. STREAMING CHAT COMPLETION")
    print("=" * 60)
    
    print("\nSending streaming request...")
    print("Note: This demo requires a valid API key set in ALPIE_API_KEY")
    
    try:
        stream = client.chat.completions.create(
            model="alpie-32b",
            messages=[
                ChatMessage(role="user", content="Count from 1 to 5.")
            ],
            max_tokens=100,
            stream=True
        )
        
        print("\nStreaming response:")
        for chunk in stream:
            if chunk.delta_content:
                print(chunk.delta_content, end="", flush=True)
        
        print("\n\n✓ Streaming completed!")
    
    except AlpieError as e:
        print(f"\n✗ Expected error (demo mode): {e.message}")

def demo_error_handling():
    """Demo: Error handling"""
    print("\n" + "=" * 60)
    print("4. ERROR HANDLING")
    print("=" * 60)
    
    print("\nTesting validation error (empty API key)...")
    try:
        Alpie(api_key="")
    except ValidationError as e:
        print(f"✓ Caught ValidationError: {e.message}")
    
    print("\nTesting invalid message format...")
    try:
        client = Alpie(api_key="test-key")
        client.chat.completions.create(
            model="alpie-32b",
            messages=["invalid"]
        )
    except ValidationError as e:
        print(f"✓ Caught ValidationError: {e.message}")

def main():
    print("\n" + "=" * 60)
    print("ALPIE SDK DEMO")
    print("=" * 60)
    print("\nThis demo showcases the Alpie SDK's main features.")
    print("Set ALPIE_API_KEY environment variable to test with real API.")
    
    client = demo_initialization()
    
    demo_non_streaming(client)
    
    demo_streaming(client)
    
    demo_error_handling()
    
    print("\n" + "=" * 60)
    print("DEMO COMPLETED")
    print("=" * 60)
    print("\nNext steps:")
    print("1. Set your API key: export ALPIE_API_KEY='your-key-here'")
    print("2. Run examples:")
    print("   - python examples/simple_chat.py")
    print("   - python examples/streaming_chat.py")
    print("   - python examples/chat_cli.py")
    print("3. Read the documentation in README.md")
    print("4. Run tests: pytest tests/")
    print()

if __name__ == "__main__":
    main()
