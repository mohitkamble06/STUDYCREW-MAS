"""Researcher agent: produces condensed notes for a topic using RAG."""

import logging
from uuid import UUID

from app.agents.base import BaseAgent
from app.prompts.researcher import RESEARCHER_SYSTEM_PROMPT
from app.schemas import ResearcherInput, TopicNotes, TopicRead, SourceRef
from app.rag import rag_service

logger = logging.getLogger(__name__)


class ResearcherAgent(BaseAgent[ResearcherInput, TopicNotes]):
    name = "researcher"
    system_prompt = RESEARCHER_SYSTEM_PROMPT
    output_schema = TopicNotes

    async def _execute(self, input_data: ResearcherInput) -> TopicNotes:
        topic = input_data.topic
        retrieved_chunks = input_data.retrieved_chunks

        # Format retrieved chunks for prompt
        chunks_text = self._format_chunks(retrieved_chunks)

        prompt = f"""Create condensed study notes for: {topic.name}

RETRIEVED CONTEXT FROM UPLOADED DOCUMENTS:
{chunks_text}

Use the retrieved context as primary source. Supplement with your knowledge where needed.
Cite sources properly: use "uploaded" for retrieved chunks with doc_id/chunk_id, "model_knowledge" for your own knowledge.

Output ONLY valid JSON matching TopicNotes schema."""

        result = await self._call_llm(prompt, TopicNotes)

        # Ensure topic name matches
        result.topic = topic.name

        # Convert source refs to proper format
        result.sources = [SourceRef.model_validate(s) if isinstance(s, dict) else s for s in result.sources]

        return result

    def _format_chunks(self, chunks: list[dict]) -> str:
        if not chunks:
            return "No relevant uploaded documents found. Use your own knowledge."

        lines = []
        for i, chunk in enumerate(chunks):
            metadata = chunk.get("metadata", {})
            doc_id = metadata.get("doc_id", "unknown")
            chunk_id = chunk.get("id", "unknown")
            content = chunk.get("content", "")[:500]
            lines.append(f"[Chunk {i+1}] doc_id={doc_id}, chunk_id={chunk_id}: {content}")

        return "\n\n".join(lines)