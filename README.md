Alpie Python SDK

The Alpie SDK provides a clean, type-safe, and robust interface for interacting with the Alpie 32B reasoning model.
Designed for production workloads with streaming support, retries, timeouts, typed exceptions, and intuitive APIs.

Installation
pip  install  alpie-chat-sdk
Python 3.10+ required

Authentication
Alpie uses Bearer Token authentication.

from  alpie  import  Alpie
client  =  Alpie(api_key="YOUR_API_KEY")
Every request automatically sends:(add the url to Create API key)

Authorization:  Bearer  <API_KEY>
Base URL & Client Configuration
client  =  Alpie(

api_key="YOUR_API_KEY",

base_url="https://api.169pi.com/v1",

timeout=60.0,

max_retries=2,

)
base_url → API root

timeout → max wait time

max_retries → safe retry logic for network issues

Features
Streaming & Non-Streaming Chat Completions

Clean, type-safe Python Interface (dataclasses, type hints)

Robust Error Handling with typed exceptions

Production-Ready Networking (retries, timeouts, httpx)

Fully Tested with pytest

Optimized for Reasoning Models

Quickstart Examples
Non-Streaming Chat Completion
from  alpie  import  Alpie,  ChatMessage
client  =  Alpie(api_key="YOUR_API_KEY")
response  =  client.chat.completions.create(

model="alpie-22b",

messages=[

ChatMessage(role="system",  content="You are a helpful assistant."),

ChatMessage(role="user",  content="What is Python?")

],

max_tokens=10000,

)

  

print(response.choices[0].message.content)
Streaming Chat Completion
from  alpie  import  Alpie,  ChatMessage
client  =  Alpie(api_key="YOUR_API_KEY")
stream  =  client.chat.completions.create(
model="alpie-32b",
messages=[
ChatMessage(role="user",  content="tell me a poem about coding")
],
stream=True,
max_tokens=5000,
)
for  chunk  in  stream:
if  chunk.delta_content:
print(chunk.delta_content,  end="",  flush=True)
Streaming responses yield partial tokens in real time — ideal for chatbots, UIs, and live applications.
