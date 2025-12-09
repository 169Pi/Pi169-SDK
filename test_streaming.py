import os
from dotenv import load_dotenv
from alpie import Alpie

load_dotenv()
api_key = os.getenv("ALPIE_API_KEY")

if not api_key:
    raise ValueError("api key missing")

client = Alpie(api_key=api_key)

stream = client.chat.create(
    model="alpie-32b",
    messages=[{"role": "user", "content": "what is the capital of france?"}],
    stream=True,
)

for chunk in stream:
    # chunk is StreamChunk, but chunk.choices is list of dicts
    if not chunk.choices:
        continue

    delta = chunk.choices[0].get("delta")
    if not delta:
        continue

    content = delta.get("content")
    if content:
        print(content, end="", flush=True)
