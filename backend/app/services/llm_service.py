import os

from dotenv import load_dotenv
from huggingface_hub import InferenceClient

load_dotenv("/app/.env")
load_dotenv("/Users/harsh/Desktop/CloudProject/backend/.env")

HF_TOKEN = os.getenv("HF_TOKEN")

if not HF_TOKEN:
    raise RuntimeError("HF_TOKEN is not configured")

MODEL_NAME = "Qwen/Qwen3-235B-A22B-Instruct-2507"

client = InferenceClient(
    token=HF_TOKEN,
)


def generate_answer(
    prompt: str,
    max_tokens: int = 500,
) -> str:
    response = client.chat_completion(
        model=MODEL_NAME,
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
        max_tokens=max_tokens,
        temperature=0.2,
    )

    content = response.choices[0].message.content

    if not content:
        raise RuntimeError("Hugging Face returned an empty response")

    return content
