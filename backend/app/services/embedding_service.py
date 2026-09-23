from sentence_transformers import SentenceTransformer
from sqlalchemy.orm import Session

from app.models import DocumentChunk


MODEL_NAME = "BAAI/bge-small-en-v1.5"

model = SentenceTransformer(MODEL_NAME)


def generate_embedding(text: str) -> list[float]:
    vector = model.encode(
        text,
        normalize_embeddings=True,
    )

    return vector.tolist()


def embed_file_chunks(
    db: Session,
    file_id: int,
) -> int:
    chunks = (
        db.query(DocumentChunk)
        .filter(DocumentChunk.file_id == file_id)
        .order_by(DocumentChunk.chunk_index)
        .all()
    )

    for chunk in chunks:
        chunk.embedding = generate_embedding(chunk.text)

    db.commit()

    return len(chunks)