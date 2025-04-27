import os

from openai import OpenAI
from dotenv import load_dotenv
load_dotenv()

client = OpenAI()

chat_completion = client.chat.completions.create(
    messages=[
        {
            "role": "user",
            "content": "Explain the importance of fast language models",
        }
    ],
    model="gpt-3.5-turbo",
)

print(chat_completion.choices[0].message.content)