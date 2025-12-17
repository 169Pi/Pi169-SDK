import asyncio
from alpie.async_client import AsyncAlpie

async def main():
    client = AsyncAlpie(api_key="ALPIE_API_KEY") # Replace with your actual API key

    # 1. Request with stream=True
    stream = await client.chat.completions.create(
        model="alpie-32b",
        messages=[{"role": "user", "content": "Write a long poem about coding."}],
        stream=True
    )

    print("Assistant: ", end="", flush=True)

    # 2. Iterate asynchronously over the chunks
    async for chunk in stream:
        content = chunk.delta_content
        if content:
            print(content, end="", flush=True)
    
    print("\n--- Stream finished ---")

if __name__ == "__main__":
    asyncio.run(main())