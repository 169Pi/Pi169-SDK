import argparse
import os
from pi169 import Pi169Client

def main():
    parser = argparse.ArgumentParser(description="Pi169 CLI")
    parser.add_argument("prompt", help="Prompt to send to the model")
    parser.add_argument("--model", default="alpie-32b")
    parser.add_argument("--stream", action="store_true")

    args = parser.parse_args()

    api_key = os.getenv("ALPIE_API_KEY")
    if not api_key:
        raise RuntimeError("ALPIE_API_KEY not set")

    client = Pi169Client(api_key=api_key)

    if args.stream:
        stream = client.chat.completions.create(
            model=args.model,
            messages=[{"role": "user", "content": args.prompt}],
            stream=True,
        )
        for chunk in stream:
            if chunk.choices:
                delta = chunk.choices[0].get("delta", {})
                if delta.get("content"):
                    print(delta["content"], end="", flush=True)
        print()
    else:
        response = client.chat.completions.create(
            model=args.model,
            messages=[{"role": "user", "content": args.prompt}],
        )
        print(response.choices[0].message.content)
