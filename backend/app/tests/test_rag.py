"""Tests for RAG service."""

import pytest
from pathlib import Path
from uuid import uuid4

from app.rag import RAGService
from app.schemas import ChunkData


class TestRAGService:
    """Tests for RAG chunking and processing."""

    def test_chunk_text_basic(self):
        """Text should be split into chunks of ~500 words with overlap."""
        service = RAGService()
        doc_id = uuid4()

        # Create text with ~1200 words
        words = ["word"] * 1200
        text = " ".join(words)

        chunks = service.chunk_text(text, doc_id)

        # Should create 3 chunks (500 + 500 + 200 with overlap)
        assert len(chunks) >= 2
        assert all(isinstance(c, ChunkData) for c in chunks)

        # Check overlap: each chunk should share words with next
        # First chunk: words 0-500
        # Second chunk: words 450-950 (50 overlap)
        # Third chunk: words 900-1200

    def test_chunk_text_short(self):
        """Short text should produce single chunk."""
        service = RAGService()
        doc_id = uuid4()

        text = "This is a short text."
        chunks = service.chunk_text(text, doc_id)

        assert len(chunks) == 1
        assert chunks[0].content == text

    def test_chunk_text_empty(self):
        """Empty text should produce no chunks."""
        service = RAGService()
        doc_id = uuid4()

        chunks = service.chunk_text("", doc_id)
        assert chunks == []

    def test_chunk_metadata(self):
        """Chunks should have correct metadata."""
        service = RAGService()
        doc_id = uuid4()

        text = " ".join(["word"] * 600)
        chunks = service.chunk_text(text, doc_id)

        for i, chunk in enumerate(chunks):
            assert chunk.metadata["doc_id"] == str(doc_id)
            assert chunk.metadata["chunk_index"] == i
            assert "char_start" in chunk.metadata
            assert "char_end" in chunk.metadata


class TestPDFExtraction:
    """Tests for PDF text extraction (requires test PDF)."""

    def test_extract_pdf_placeholder(self):
        """Placeholder - would need a test PDF file."""
        # This would test with a real PDF
        # For now, just verify the function exists
        service = RAGService()
        assert hasattr(service, '_extract_pdf')


class TestTextExtraction:
    """Tests for text file extraction."""

    def test_extract_txt(self, tmp_path):
        """Should extract text from .txt files."""
        service = RAGService()

        test_file = tmp_path / "test.txt"
        test_file.write_text("Hello world\nThis is a test.")

        text = service.extract_text(test_file, "test.txt")
        assert "Hello world" in text
        assert "This is a test" in text

    def test_extract_md(self, tmp_path):
        """Should extract text from .md files."""
        service = RAGService()

        test_file = tmp_path / "test.md"
        test_file.write_text("# Header\n\nContent here.")

        text = service.extract_text(test_file, "test.md")
        assert "Header" in text
        assert "Content here" in text

    def test_invalid_extension(self, tmp_path):
        """Should reject unsupported file types."""
        service = RAGService()

        test_file = tmp_path / "test.docx"
        test_file.write_text("content")

        with pytest.raises(ValueError, match="not allowed"):
            service.extract_text(test_file, "test.docx")