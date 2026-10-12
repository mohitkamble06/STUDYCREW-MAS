"""File upload API routes."""

import logging
import shutil
import uuid
from pathlib import Path
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import async_session_maker, UploadedDoc, Course
from app.rag import rag_service
from app.schemas import UploadedDocRead
from app.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)

# Temp upload directory
UPLOAD_DIR = Path(settings.chroma_path) / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_EXTENSIONS = {".pdf", ".txt", ".md"}


async def get_db():
    async with async_session_maker() as session:
        yield session


def validate_file(filename: str) -> str:
    """Validate file extension and return suffix."""
    suffix = Path(filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"File type {suffix} not allowed. Allowed: {', '.join(ALLOWED_EXTENSIONS)}",
        )
    return suffix


@router.post("/{course_id}/upload", response_model=UploadedDocRead)
async def upload_document(
    course_id: UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Upload and process a document for RAG."""
    # Verify course exists
    course = await db.get(Course, course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    # Validate file
    suffix = validate_file(file.filename)

    # Save file temporarily
    file_id = uuid.uuid4()
    temp_path = UPLOAD_DIR / f"{file_id}{suffix}"

    try:
        with open(temp_path, "wb") as f:
            shutil.copyfileobj(file.file, f)

        # Extract text
        text = rag_service.extract_text(temp_path, file.filename)
        if not text.strip():
            raise HTTPException(status_code=400, detail="No text content extracted from file")

        # Chunk text
        chunks = rag_service.chunk_text(text, file_id)
        if not chunks:
            raise HTTPException(status_code=400, detail="No chunks generated from file")

        # Add course_id to chunk metadata
        for chunk in chunks:
            chunk.metadata["course_id"] = str(course_id)

        # Embed and store in ChromaDB
        await rag_service.add_chunks(chunks)

        # Save document record
        doc = UploadedDoc(
            course_id=course_id,
            filename=file.filename,
            chunk_count=len(chunks),
        )
        db.add(doc)
        await db.commit()
        await db.refresh(doc)

        logger.info(f"Uploaded {file.filename} for course {course_id}: {len(chunks)} chunks")

        return UploadedDocRead(
            id=doc.id,
            course_id=doc.course_id,
            filename=doc.filename,
            chunk_count=doc.chunk_count,
            uploaded_at=doc.uploaded_at,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Upload failed")
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

    finally:
        # Clean up temp file
        if temp_path.exists():
            temp_path.unlink()


@router.get("/{course_id}/uploads", response_model=list[UploadedDocRead])
async def list_uploads(course_id: UUID, db: AsyncSession = Depends(get_db)):
    """List uploaded documents for a course."""
    course = await db.get(Course, course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    result = await db.execute(
        select(UploadedDoc).where(UploadedDoc.course_id == course_id).order_by(UploadedDoc.uploaded_at.desc())
    )
    docs = result.scalars().all()

    return [UploadedDocRead.model_validate(d) for d in docs]


@router.delete("/{course_id}/uploads/{doc_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_upload(course_id: UUID, doc_id: UUID, db: AsyncSession = Depends(get_db)):
    """Delete an uploaded document and its chunks."""
    doc = await db.get(UploadedDoc, doc_id)
    if not doc or doc.course_id != course_id:
        raise HTTPException(status_code=404, detail="Document not found")

    # Delete from ChromaDB
    await rag_service.delete_doc_chunks(doc_id)

    # Delete from database
    await db.delete(doc)
    await db.commit()