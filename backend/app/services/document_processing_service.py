from sqlalchemy.orm import Session

from app.models import DocumentChunk, File
from app.services.chunk_service import chunk_documents
from app.services.document_service import extract_pdf_documents
from app.services.embedding_service import generate_embedding


def process_file(
    db: Session,
    file: File,
) -> dict:
    documents = extract_pdf_documents(file)

    if not documents:
        raise ValueError("No text could be extracted from the PDF")

    chunks = chunk_documents(documents)

    if not chunks:
        raise ValueError("No chunks were created from the PDF")

    document_chunks = []

    for chunk_index, chunk in enumerate(chunks):
        document_chunk = DocumentChunk(
            file_id=file.id,
            chunk_index=chunk_index,
            text=chunk.page_content,
            page_number=chunk.metadata.get("page_number"),
            embedding=generate_embedding(chunk.page_content),
        )

        document_chunks.append(document_chunk)

    db.add_all(document_chunks)
    db.commit()

    return {
        "pages": len(documents),
        "chunks": len(document_chunks),
        "embeddings": len(document_chunks),
    }
