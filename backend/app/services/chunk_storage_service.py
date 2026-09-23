from sqlalchemy.orm import Session

from app.models import DocumentChunk
from langchain_core.documents import Document


def store_chunks(
    db: Session,
    file_id: int,
    chunks: list[Document],
) -> list[DocumentChunk]:
    stored_chunks = []

    for chunk_index, chunk in enumerate(chunks):
        document_chunk = DocumentChunk(
            file_id=file_id,
            chunk_index=chunk_index,
            text=chunk.page_content,
            page_number=chunk.metadata.get("page_number"),
        )

        db.add(document_chunk)
        stored_chunks.append(document_chunk)

    db.commit()

    return stored_chunks
