"""RAG module for document ingestion, chunking, embedding, and retrieval."""

import hashlib
import logging
import uuid
from pathlib import Path
from typing import Any

import chromadb
from chromadb.config import Settings as ChromaSettings
from sentence_transformers import SentenceTransformer

from app.config import settings
from app.schemas import ChunkData, UploadedDocRead

logger = logging.getLogger(__name__)


class RAGService:
    """Handles document processing, embedding, and retrieval using ChromaDB."""

    def __init__(self):
        self._client: chromadb.AsyncClient | None = None
        self._collection: chromadb.AsyncCollection | None = None
        self._embedder: SentenceTransformer | None = None

    async def initialize(self) -> None:
        """Initialize ChromaDB client and embedding model."""
        # Initialize ChromaDB - support both local and remote
        if settings.chroma_host:
            # Remote ChromaDB (Chroma Cloud or self-hosted)
            logger.info(f"Connecting to remote ChromaDB at {settings.chroma_host}:{settings.chroma_port}")
            self._client = await chromadb.AsyncHttpClient(
                host=settings.chroma_host,
                port=settings.chroma_port,
                ssl=settings.chroma_ssl,
                settings=ChromaSettings(anonymized_telemetry=False),
            )
        else:
            # Local ChromaDB with file persistence
            logger.info(f"Initializing local ChromaDB at {settings.chroma_path_resolved}")
            self._client = await chromadb.AsyncClient(
                ChromaSettings(
                    persist_directory=settings.chroma_path_resolved,
                    anonymized_telemetry=False,
                )
            )

        self._collection = await self._client.get_or_create_collection(
            name="studycrew_chunks",
            metadata={"hnsw:space": "cosine"},
        )

        # Initialize embedder
        self._embedder = SentenceTransformer(settings.embedding_model)
        logger.info(f"RAG service initialized with embedder: {settings.embedding_model}")

    async def close(self) -> None:
        """Close connections."""
        if self._client:
            await self._client.close()

    @property
    def collection(self) -> chromadb.AsyncCollection:
        if not self._collection:
            raise RuntimeError("RAG service not initialized. Call initialize() first.")
        return self._collection

    @property
    def embedder(self) -> SentenceTransformer:
        if not self._embedder:
            raise RuntimeError("RAG service not initialized. Call initialize() first.")
        return self._embedder

    # -------------------------------------------------------------------------
    # Document Processing
    # -------------------------------------------------------------------------

    def extract_text(self, file_path: Path, filename: str) -> str:
        """Extract text from uploaded file based on extension."""
        suffix = filename.lower().split(".")[-1]

        if suffix == "pdf":
            return self._extract_pdf(file_path)
        elif suffix in ("txt", "md"):
            return file_path.read_text(encoding="utf-8")
        else:
            raise ValueError(f"Unsupported file type: {suffix}")

    def _extract_pdf(self, file_path: Path) -> str:
        """Extract text from PDF using pypdf."""
        try:
            from pypdf import PdfReader
            reader = PdfReader(file_path)
            texts = []
            for page in reader.pages:
                text = page.extract_text()
                if text:
                    texts.append(text)
            return "\n\n".join(texts)
        except Exception as e:
            logger.error(f"PDF extraction failed: {e}")
            raise ValueError(f"Failed to extract text from PDF: {e}")

    def chunk_text(self, text: str, doc_id: uuid.UUID) -> list[ChunkData]:
        """Split text into overlapping chunks."""
        chunks = []
        chunk_size = settings.chunk_size
        overlap = settings.chunk_overlap

        # Simple word-based chunking
        words = text.split()
        if not words:
            return chunks

        start = 0
        chunk_index = 0

        while start < len(words):
            end = min(start + chunk_size, len(words))
            chunk_words = words[start:end]
            chunk_text = " ".join(chunk_words)

            chunk_id = uuid.uuid4()
            chunks.append(ChunkData(
                id=chunk_id,
                content=chunk_text,
                metadata={
                    "doc_id": str(doc_id),
                    "chunk_index": chunk_index,
                    "char_start": start,
                    "char_end": end,
                }
            ))

            chunk_index += 1
            if end >= len(words):
                break
            start = end - overlap

        return chunks

    # -------------------------------------------------------------------------
    # Embedding & Storage
    # -------------------------------------------------------------------------

    def _generate_embeddings(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for a list of texts."""
        embeddings = self._embedder.encode(texts, convert_to_tensor=False, normalize_embeddings=True)
        return embeddings.tolist()

    async def add_chunks(self, chunks: list[ChunkData]) -> None:
        """Add chunks to ChromaDB with embeddings."""
        if not chunks:
            return

        texts = [c.content for c in chunks]
        embeddings = self._generate_embeddings(texts)

        ids = [str(c.id) for c in chunks]
        metadatas = [c.metadata for c in chunks]

        await self.collection.add(
            ids=ids,
            documents=texts,
            embeddings=embeddings,
            metadatas=metadatas,
        )
        logger.info(f"Added {len(chunks)} chunks to ChromaDB")

    async def delete_doc_chunks(self, doc_id: uuid.UUID) -> None:
        """Delete all chunks for a document."""
        # ChromaDB doesn't support delete by metadata directly in async yet
        # We'll query first then delete by IDs
        results = await self.collection.get(
            where={"doc_id": str(doc_id)},
            include=["metadatas"],
        )
        if results["ids"]:
            await self.collection.delete(ids=results["ids"])
            logger.info(f"Deleted {len(results['ids'])} chunks for doc {doc_id}")

    # -------------------------------------------------------------------------
    # Retrieval
    # -------------------------------------------------------------------------

    async def retrieve(
        self,
        query: str,
        course_id: uuid.UUID,
        top_k: int = 5,
        topic_filter: str | None = None,
    ) -> list[dict[str, Any]]:
        """
        Retrieve relevant chunks for a query.

        Args:
            query: Search query
            course_id: Filter by course (via doc metadata)
            top_k: Number of results to return
            topic_filter: Optional topic name to bias retrieval

        Returns:
            List of dicts with chunk data and metadata
        """
        query_embedding = self._generate_embeddings([query])[0]

        # Build where clause for course filtering
        where_clause = {"course_id": str(course_id)}
        if topic_filter:
            where_clause["topic"] = topic_filter

        results = await self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where_clause,
            include=["documents", "metadatas", "distances"],
        )

        chunks = []
        for i in range(len(results["ids"][0])):
            chunks.append({
                "id": uuid.UUID(results["ids"][0][i]),
                "content": results["documents"][0][i],
                "metadata": results["metadatas"][0][i],
                "distance": results["distances"][0][i],
            })

        return chunks


# Global RAG service instance
rag_service = RAGService()