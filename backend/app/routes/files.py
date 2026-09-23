import logging
import uuid
from pathlib import Path
from tempfile import NamedTemporaryFile

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import DocumentChunk
from app.models import File as FileModel
from app.models import User
from app.services.document_processing_service import process_file
from app.services.rag_service import answer_question
from app.services.s3_service import (
    delete_file,
    generate_download_url,
    upload_file,
)
from app.services.search_service import semantic_search


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/files", tags=["Files"])


MAX_FILE_SIZE = 10 * 1024 * 1024
ALLOWED_CONTENT_TYPE = "application/pdf"
PDF_SIGNATURE = b"%PDF-"


@router.post("/upload")
def upload_file_endpoint(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if file.content_type != ALLOWED_CONTENT_TYPE:
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are allowed",
        )

    original_filename = Path(file.filename or "").name

    if not original_filename:
        raise HTTPException(
            status_code=400,
            detail="Filename is required",
        )

    if not original_filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are allowed",
        )

    suffix = ".pdf"

    with NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
        temp_path = temp_file.name
        total_size = 0

        while chunk := file.file.read(1024 * 1024):
            total_size += len(chunk)

            if total_size > MAX_FILE_SIZE:
                Path(temp_path).unlink(missing_ok=True)

                raise HTTPException(
                    status_code=413,
                    detail="File size exceeds the 10 MB limit",
                )

            temp_file.write(chunk)

    with open(temp_path, "rb") as temp_file:
        signature = temp_file.read(len(PDF_SIGNATURE))

    if signature != PDF_SIGNATURE:
        Path(temp_path).unlink(missing_ok=True)

        raise HTTPException(
            status_code=400,
            detail="Invalid PDF file",
        )

    object_key = f"uploads/{uuid.uuid4()}{suffix}"

    file_record = None

    try:
        upload_file(
            temp_path,
            object_key,
            file.content_type,
        )

        file_record = FileModel(
            original_filename=original_filename,
            object_key=object_key,
            content_type=file.content_type,
            file_size=total_size,
            user_id=current_user.id,
        )

        db.add(file_record)
        db.commit()
        db.refresh(file_record)

        processing_result = process_file(
            db=db,
            file=file_record,
        )

        return {
            "id": file_record.id,
            "filename": file_record.original_filename,
            "content_type": file_record.content_type,
            "file_size": file_record.file_size,
            "user_id": file_record.user_id,
            "processing": processing_result,
        }

    except HTTPException:
        logger.exception(
            "Document processing failed with HTTPException: "
            "filename=%s user_id=%s",
            original_filename,
            current_user.id,
        )

        db.rollback()

        if file_record is not None:
            db.query(DocumentChunk).filter(
                DocumentChunk.file_id == file_record.id
            ).delete(
                synchronize_session=False
            )

            db.delete(file_record)
            db.commit()

        try:
            delete_file(object_key)
        except Exception:
            logger.exception(
                "Failed to clean up S3 object after upload failure: "
                "object_key=%s",
                object_key,
            )

        raise

    except Exception:
        logger.exception(
            "Document processing failed: filename=%s user_id=%s",
            original_filename,
            current_user.id,
        )

        db.rollback()

        if file_record is not None:
            db.query(DocumentChunk).filter(
                DocumentChunk.file_id == file_record.id
            ).delete(
                synchronize_session=False
            )

            db.delete(file_record)
            db.commit()

        try:
            delete_file(object_key)
        except Exception:
            logger.exception(
                "Failed to clean up S3 object after processing failure: "
                "object_key=%s",
                object_key,
            )

        raise HTTPException(
            status_code=500,
            detail="File upload succeeded but document processing failed",
        )

    finally:
        Path(temp_path).unlink(missing_ok=True)


@router.get("/")
def get_files(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    files = (
        db.query(FileModel)
        .filter(FileModel.user_id == current_user.id)
        .order_by(FileModel.created_at.desc())
        .all()
    )

    return [
        {
            "id": file.id,
            "filename": file.original_filename,
            "content_type": file.content_type,
            "file_size": file.file_size,
            "created_at": file.created_at,
            "user_id": file.user_id,
        }
        for file in files
    ]


@router.get("/{file_id}/search")
def search_file_endpoint(
    file_id: int,
    q: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    file_record = (
        db.query(FileModel)
        .filter(
            FileModel.id == file_id,
            FileModel.user_id == current_user.id,
        )
        .first()
    )

    if file_record is None:
        raise HTTPException(
            status_code=404,
            detail="File not found",
        )

    if not q.strip():
        raise HTTPException(
            status_code=400,
            detail="Search query is required",
        )

    results = semantic_search(
        db=db,
        file_id=file_id,
        query=q,
        limit=5,
    )

    return {
        "file_id": file_id,
        "query": q,
        "results": [
            {
                "chunk_index": chunk.chunk_index,
                "page_number": chunk.page_number,
                "text": chunk.text,
                "distance": distance,
            }
            for chunk, distance in results
        ],
    }


@router.get("/{file_id}/chat")
def chat_with_file_endpoint(
    file_id: int,
    q: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    file_record = (
        db.query(FileModel)
        .filter(
            FileModel.id == file_id,
            FileModel.user_id == current_user.id,
        )
        .first()
    )

    if file_record is None:
        raise HTTPException(
            status_code=404,
            detail="File not found",
        )

    if not q.strip():
        raise HTTPException(
            status_code=400,
            detail="Question is required",
        )

    result = answer_question(
        db=db,
        file_id=file_id,
        question=q,
    )

    return {
        "file_id": file_id,
        "question": q,
        "answer": result["answer"],
        "sources": result["sources"],
    }


@router.get("/{file_id}/download")
def download_file_endpoint(
    file_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    file_record = (
        db.query(FileModel)
        .filter(
            FileModel.id == file_id,
            FileModel.user_id == current_user.id,
        )
        .first()
    )

    if file_record is None:
        raise HTTPException(
            status_code=404,
            detail="File not found",
        )

    download_url = generate_download_url(file_record.object_key)

    return {
        "id": file_record.id,
        "filename": file_record.original_filename,
        "download_url": download_url,
        "expires_in": 300,
    }


@router.delete("/{file_id}")
def delete_file_endpoint(
    file_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    file_record = (
        db.query(FileModel)
        .filter(
            FileModel.id == file_id,
            FileModel.user_id == current_user.id,
        )
        .first()
    )

    if file_record is None:
        raise HTTPException(
            status_code=404,
            detail="File not found",
        )

    delete_file(file_record.object_key)

    db.delete(file_record)
    db.commit()

    return {
        "message": "File deleted successfully",
        "id": file_id,
    }