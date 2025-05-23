from openai import OpenAI
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def call_openai(prompt: str):
    """Call OpenAI API for LLM-based remediation using gpt-3.5-turbo model."""
    client = OpenAI()
    chat_completion = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
    )
    return chat_completion.choices[0].message.content