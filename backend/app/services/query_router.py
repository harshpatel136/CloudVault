from app.services.llm_service import client, MODEL_NAME


CLASSIFICATION_PROMPT = """Classify this question into exactly one category.

SPECIFIC:
The answer can be found from a small number of relevant document chunks.

DOCUMENT_WIDE:
The answer requires examining the document broadly, including:
- summarizing
- counting across the document
- listing multiple items
- aggregating information
- comparing information across sections

Examples:
Who is the corresponding author? -> SPECIFIC
What methodology does the paper use? -> SPECIFIC
How many papers are mentioned in the references? -> DOCUMENT_WIDE
How many references does the paper contain? -> DOCUMENT_WIDE
List all limitations discussed in the paper. -> DOCUMENT_WIDE
Summarize the entire document. -> DOCUMENT_WIDE

Return ONLY one word:
SPECIFIC
or
DOCUMENT_WIDE

Question:
"""


def classify_query(question: str) -> str:
    response = client.chat_completion(
        model=MODEL_NAME,
        messages=[
            {
                "role": "user",
                "content": CLASSIFICATION_PROMPT + question.strip(),
            }
        ],
        max_tokens=10,
        temperature=0.0,
    )

    result = (
        response.choices[0].message.content or ""
    ).strip().upper()

    if result == "DOCUMENT_WIDE":
        return "DOCUMENT_WIDE"

    if result == "SPECIFIC":
        return "SPECIFIC"

    raise RuntimeError(
        f"Invalid query classification returned by Hugging Face: {result!r}"
    )
