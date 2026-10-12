"""Base agent class with common functionality."""

import logging
from abc import ABC, abstractmethod
from typing import Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel

from app.llm import generate_json, LLMValidationError
from app.schemas import AgentEvent, AgentStatus

logger = logging.getLogger(__name__)

InputT = TypeVar("InputT", bound=BaseModel)
OutputT = TypeVar("OutputT", bound=BaseModel)


class BaseAgent(ABC, Generic[InputT, OutputT]):
    """Base class for all agents."""

    name: str = "base"
    system_prompt: str = ""
    output_schema: type[OutputT]

    def __init__(self, run_id: UUID, emit_event_callback=None):
        self.run_id = run_id
        self.emit_event = emit_event_callback

    async def _emit(self, status: AgentStatus, message: str, topic_id: UUID | None = None, data: dict | None = None) -> None:
        """Emit progress event for SSE streaming."""
        if self.emit_event:
            event = AgentEvent(
                run_id=self.run_id,
                agent=self.name,
                status=status,
                message=message,
                topic_id=topic_id,
                data=data or {},
            )
            await self.emit_event(event)

    @abstractmethod
    async def _execute(self, input_data: InputT) -> OutputT:
        """Execute the agent's core logic."""
        pass

    async def run(self, input_data: InputT, topic_id: UUID | None = None) -> OutputT:
        """Run the agent with event emission and error handling."""
        await self._emit(AgentStatus.STARTED, f"Starting {self.name}", topic_id)

        try:
            result = await self._execute(input_data)
            await self._emit(AgentStatus.DONE, f"{self.name} completed", topic_id, data=result.model_dump() if hasattr(result, 'model_dump') else {})
            return result

        except LLMValidationError as e:
            await self._emit(AgentStatus.ERROR, f"{self.name} validation failed: {e}", topic_id)
            raise

        except Exception as e:
            logger.exception(f"Agent {self.name} failed")
            await self._emit(AgentStatus.ERROR, f"{self.name} failed: {e}", topic_id)
            raise

    async def _call_llm(self, prompt: str, schema: type[OutputT], system_prompt: str | None = None, retries: int = 2) -> OutputT:
        """Call LLM with the agent's system prompt."""
        return await generate_json(
            prompt=prompt,
            schema=schema,
            system_prompt=system_prompt or self.system_prompt,
            retries=retries,
        )