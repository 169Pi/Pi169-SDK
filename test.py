from alpie import Alpie, ChatMessage

client = Alpie(api_key="pi-XQo91TO03f9IHnN3e1LfkVq4NOHVQiA7")

stream = client.chat.completions.create(
    model="alpie-32b",
    messages=[
        ChatMessage(role="user", content="Write a poem about coding")
    ],
    stream=True,
    max_tokens=50000
)

for chunk in stream:
    if chunk.delta_content:
        print(chunk.delta_content, end="", flush=True)