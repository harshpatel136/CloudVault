from pathlib import Path
from tempfile import NamedTemporaryFile

import pymupdf
from langchain_core.documents import Document

from app.models import File
from app.services.s3_service import download_file


def extract_pdf_documents(file: File) -> list[Document]:
    with NamedTemporaryFile(suffix=".pdf", delete=False) as temp_file:
        temp_path = Path(temp_file.name)

    try:
        download_file(
            file.object_key,
            str(temp_path),
        )

        pdf = pymupdf.open(temp_path)

        try:
            documents = []

            for page_number, page in enumerate(pdf, start=1):
                text = page.get_text().strip()

                if not text:
                    continue

                documents.append(
                    Document(
                        page_content=text,
                        metadata={
                            "file_id": file.id,
                            "filename": file.original_filename,
                            "page_number": page_number,
                        },
                    )
                )

            return documents

        finally:
            pdf.close()

    finally:
        temp_path.unlink(missing_ok=True)
