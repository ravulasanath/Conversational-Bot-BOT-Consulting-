# app/llm_client.py
import os
from typing import List, Literal

import requests
from dotenv import load_dotenv

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# type alias
Role = Literal["system", "user", "assistant"]


def call_llm(messages: List[dict]) -> str:
    """
    Call an LLM (Groq Llama3 here) with a list of messages:
    messages = [{ "role": "user"|"assistant"|"system", "content": "..." }, ...]
    Returns assistant text.
    """

    # Fallback fake response if no API key (useful for local testing)
    if not GROQ_API_KEY:
        return "This is a dummy LLM response. Configure GROQ_API_KEY to get real answers."

    url = "https://api.groq.com/openai/v1/chat/completions"

    payload = {
    "model": "llama-3.1-8b-instant",
    "messages": messages,
    "temperature": 0.7,
}


    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }

    response = requests.post(url, json=payload, headers=headers, timeout=30)

    if response.status_code != 200:
        # simple error handling
        raise RuntimeError(f"LLM API error: {response.status_code} - {response.text}")

    data = response.json()
    return data["choices"][0]["message"]["content"]
