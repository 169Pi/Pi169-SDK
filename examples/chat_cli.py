"""
Interactive command-line chat interface using the Alpie SDK.
"""

from pi169 import Alpie, ChatMessage
from pi169.exceptions import AlpieError
import os
import sys
from dotenv import load_dotenv
load_dotenv()

def main():
    api_key = os.getenv("ALPIE_API_KEY")
    if not api_key:
        print("Please set ALPIE_API_KEY environment variable")
        print("Example: export ALPIE_API_KEY='your-api-key-here'")
        return
    
    client = Alpie(api_key=api_key)
    
    print("=" * 60)
    print("Alpie SDK - Interactive Chat CLI")
    print("=" * 60)
    print("Type 'exit' or 'quit' to end the conversation")
    print("Type 'stream' to toggle streaming mode (default: off)")
    print("=" * 60)
    print()
    
    messages = [
        ChatMessage(role="system", content="You are a helpful assistant.")
    ]
    
    use_streaming = False
    
    while True:
        try:
            user_input = input("You: ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() in ["exit", "quit"]:
                print("\nGoodbye!")
                break
            
            if user_input.lower() == "stream":
                use_streaming = not use_streaming
                mode = "ON" if use_streaming else "OFF"
                print(f"\n[Streaming mode: {mode}]\n")
                continue
            
            messages.append(ChatMessage(role="user", content=user_input))
            
            print("\nAssistant: ", end="", flush=True)
            
            if use_streaming:
                full_response = ""
                stream = client.chat.completions.create(
                    model="alpie-32b",
                    messages=messages,
                    max_tokens=2000,
                    stream=True
                )
                
                for chunk in stream:
                    if chunk.delta_content:
                        print(chunk.delta_content, end="", flush=True)
                        full_response += chunk.delta_content
                
                print("\n")
                messages.append(ChatMessage(role="assistant", content=full_response))
            
            else:
                response = client.chat.completions.create(
                    model="alpie-32b",
                    messages=messages,
                    max_tokens=2000
                )
                
                assistant_message = response.choices[0].message.content
                print(f"{assistant_message}\n")
                messages.append(ChatMessage(role="assistant", content=assistant_message))
        
        except KeyboardInterrupt:
            print("\n\nGoodbye!")
            break
        except AlpieError as e:
            print(f"\nError: {e.message}\n")
        except Exception as e:
            print(f"\nUnexpected error: {e}\n")

if __name__ == "__main__":
    main()
