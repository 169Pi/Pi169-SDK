import asyncio
from alpie.async_client import AsyncAlpie

async def main():
    # 1. Initialize the client
    client = AsyncAlpie(api_key="ALPIE_API_KEY") # Replace with your actual API key

    print("Sending request...")

    # 2. Await the response
    response = await client.chat.completions.create(
        model="alpie-32b",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "What is the capital of France?"}
        ]
    )

    # 3. Access the data just like the sync version
    print(f"Response: {response.choices[0].message.content}")
    print(f"Tokens used: {response.usage.total_tokens}")

if __name__ == "__main__":
    asyncio.run(main())