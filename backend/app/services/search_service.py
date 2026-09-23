from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import DocumentChunk
from app.services.embedding_service import generate_embedding


def semantic_search(
    db: Session,
    file_id: int,
    query: str,
    limit: int = 5,
) -> list[tuple[DocumentChunk, float]]:
    query_embedding = generate_embedding(query)

    distance = DocumentChunk.embedding.cosine_distance(
        query_embedding
    )

    statement = (
        select(DocumentChunk, distance.label("distance"))
        .where(DocumentChunk.file_id == file_id)
        .where(DocumentChunk.embedding.is_not(None))
        .order_by(distance)
        .limit(limit)
    )

    return list(db.execute(statement).all())