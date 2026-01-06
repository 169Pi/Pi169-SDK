import asyncio
import os
from dotenv import load_dotenv
from pi169.async_client import AsyncPi169Client

load_dotenv()

async def main():
    api_key = os.getenv("ALPIE_API_KEY")
    if not api_key:
        raise ValueError("API key missing")

    client = AsyncPi169Client(api_key=api_key)

    # Create multiple tasks
    tasks = [
        client.chat.completions.create(
            model="alpie-32b",
            messages=[{"role": "user", "content": f"What is {n} + {n}?"}]
        )
        for n in range(1, 6)
    ]

    # Execute concurrently
    responses = await asyncio.gather(*tasks)

    for i, response in enumerate(responses, 1):
        print(f"Response {i}: {response.choices[0].message.content}")

if __name__ == "__main__":
    asyncio.run(main())