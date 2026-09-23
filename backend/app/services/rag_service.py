from sqlalchemy.orm import Session

from app.models import DocumentChunk
from app.services.llm_service import generate_answer
from app.services.query_router import classify_query
from app.services.search_service import semantic_search


def answer_question(
    db: Session,
    file_id: int,
    question: str,
):
    query_type = classify_query(question)

    sources = []

    if query_type == "SPECIFIC":
        results = semantic_search(
            db=db,
            file_id=file_id,
            query=question,
            limit=5,
        )

        if not results:
            return {
                "answer": "I could not find the answer in this document.",
                "sources": [],
            }

        context_parts = []

        for chunk, distance in results:
            context_parts.append(
                f"[Page {chunk.page_number}]\n{chunk.text}"
            )

            sources.append(
                {
                    "chunk_index": chunk.chunk_index,
                    "page_number": chunk.page_number,
                    "distance": round(float(distance), 4),
                }
            )

        context = "\n\n".join(context_parts)

        prompt = f"""You are a document question-answering assistant.

Answer the user's question using ONLY the provided document context.

If the answer cannot be found in the context, say:
"I could not find the answer in this document."

Do not invent facts or use outside knowledge.

Document context:
{context}

User question:
{question}

Answer clearly and concisely.
"""

        answer = generate_answer(
            prompt,
            max_tokens=700,
        )

    elif query_type == "DOCUMENT_WIDE":
        chunks = (
            db.query(DocumentChunk)
            .filter(DocumentChunk.file_id == file_id)
            .order_by(DocumentChunk.chunk_index.asc())
            .all()
        )

        if not chunks:
            return {
                "answer": "I could not find any content in this document.",
                "sources": [],
            }

        context_parts = []

        for chunk in chunks:
            context_parts.append(
                f"[Page {chunk.page_number}]\n{chunk.text}"
            )

            sources.append(
                {
                    "chunk_index": chunk.chunk_index,
                    "page_number": chunk.page_number,
                }
            )

        context = "\n\n".join(context_parts)

        prompt = f"""You are an expert document analysis assistant.

You must answer the user's request using ONLY the document context provided below.

This is a DOCUMENT-WIDE question. You must consider the entire supplied document context rather than focusing on only one chunk.

For summaries:
- Cover the major topics and sections present in the document.
- Preserve the terminology and concepts used in the document.
- Connect related ideas across pages.
- Do not invent information that is not present in the document.

For lists, counts, comparisons, or other document-wide requests:
- Examine all supplied document content before answering.
- Include information from different pages when relevant.

If the requested information genuinely cannot be found in the supplied document context, say:
"I could not find the answer in this document."

Document context:
{context}

User question:
{question}

Provide a complete answer based only on the document.
"""

        answer = generate_answer(
            prompt,
            max_tokens=2000,
        )

    else:
        raise RuntimeError(
            f"Unsupported query type: {query_type}"
        )

    return {
        "answer": answer,
        "sources": sources,
    }
