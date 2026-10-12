"""LLM wrapper for Ollama with structured JSON output and retry logic."""

import json
import logging
from typing import Type, TypeVar

import ollama
from pydantic import BaseModel, ValidationError

from app.config import settings

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class LLMError(Exception):
    """Base exception for LLM errors."""
    pass


class LLMValidationError(LLMError):
    """Raised when LLM output fails validation after retries."""
    pass


class LLMTimeoutError(LLMError):
    """Raised when LLM request times out."""
    pass


async def generate_json(
    prompt: str,
    schema: Type[T],
    model: str | None = None,
    temperature: float | None = None,
    retries: int = 2,
    system_prompt: str | None = None,
) -> T:
    """
    Generate structured JSON output from Ollama LLM.

    Args:
        prompt: User prompt to send to the LLM
        schema: Pydantic model class to validate output against
        model: Override default model (from settings)
        temperature: Override default temperature (from settings)
        retries: Number of retry attempts on validation failure
        system_prompt: Optional system prompt to prepend

    Returns:
        Validated Pydantic model instance

    Raises:
        LLMValidationError: If validation fails after all retries
        LLMTimeoutError: If request times out
    """
    model = model or settings.llm_model
    temperature = temperature if temperature is not None else settings.llm_temperature

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    # Build JSON schema for Ollama's format parameter
    json_schema = schema.model_json_schema()

    last_error: Exception | None = None

    for attempt in range(retries + 1):
        try:
            logger.debug(f"LLM call attempt {attempt + 1}/{retries + 1} with model {model}")

            response = await ollama.AsyncClient(host=settings.ollama_base_url).chat(
                model=model,
                messages=messages,
                format=json_schema,
                options={
                    "temperature": temperature,
                    "num_ctx": settings.llm_num_ctx,
                },
            )

            content = response["message"]["content"]
            logger.debug(f"Raw LLM response: {content[:200]}...")

            # Parse and validate
            data = json.loads(content)
            return schema.model_validate(data)

        except ValidationError as e:
            last_error = e
            error_msg = f"Validation error: {e}"
            logger.warning(f"Attempt {attempt + 1} failed: {error_msg}")

            if attempt < retries:
                # Append validation error to prompt for retry
                messages.append({"role": "assistant", "content": content})
                messages.append({
                    "role": "user",
                    "content": (
                        f"The previous response failed validation. "
                        f"Error: {error_msg}. "
                        f"Please respond with valid JSON matching the schema exactly."
                    ),
                })
            continue

        except json.JSONDecodeError as e:
            last_error = e
            logger.warning(f"Attempt {attempt + 1} failed: JSON decode error: {e}")
            if attempt < retries:
                messages.append({"role": "assistant", "content": content})
                messages.append({
                    "role": "user",
                    "content": f"Invalid JSON. Error: {e}. Please respond with valid JSON only."
                })
            continue

        except ollama.ResponseError as e:
            last_error = e
            logger.error(f"Ollama error: {e}")
            if "timeout" in str(e).lower():
                raise LLMTimeoutError(f"LLM request timed out: {e}") from e
            raise LLMError(f"Ollama error: {e}") from e

        except Exception as e:
            last_error = e
            logger.error(f"Unexpected error: {e}")
            raise LLMError(f"Unexpected error: {e}") from e

    # All retries exhausted
    raise LLMValidationError(
        f"Failed to generate valid JSON after {retries + 1} attempts. "
        f"Last error: {last_error}"
    ) from last_error


async def generate_text(
    prompt: str,
    model: str | None = None,
    temperature: float | None = None,
    system_prompt: str | None = None,
) -> str:
    """
    Generate plain text output from Ollama LLM.

    Args:
        prompt: User prompt
        model: Override default model
        temperature: Override default temperature
        system_prompt: Optional system prompt

    Returns:
        Raw text response
    """
    model = model or settings.llm_model
    temperature = temperature if temperature is not None else settings.llm_temperature

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    response = await ollama.AsyncClient(host=settings.ollama_base_url).chat(
        model=model,
        messages=messages,
        options={
            "temperature": temperature,
            "num_ctx": settings.llm_num_ctx,
        },
    )

    return response["message"]["content"]