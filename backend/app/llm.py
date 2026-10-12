"""LLM wrapper supporting Ollama (local) and Anthropic (cloud) with structured JSON output."""

import json
import logging
import os
from typing import Type, TypeVar

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
    Generate structured JSON output from LLM (Ollama or Anthropic).

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
    provider = getattr(settings, "llm_provider", "ollama")

    if provider == "anthropic":
        return await _generate_json_anthropic(
            prompt, schema, model, temperature, retries, system_prompt
        )
    else:
        return await _generate_json_ollama(
            prompt, schema, model, temperature, retries, system_prompt
        )


async def _generate_json_ollama(
    prompt: str,
    schema: Type[T],
    model: str | None = None,
    temperature: float | None = None,
    retries: int = 2,
    system_prompt: str | None = None,
) -> T:
    """Generate JSON using Ollama."""
    import ollama

    model = model or settings.llm_model
    temperature = temperature if temperature is not None else settings.llm_temperature

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    json_schema = schema.model_json_schema()

    last_error: Exception | None = None

    for attempt in range(retries + 1):
        try:
            logger.debug(f"Ollama call attempt {attempt + 1}/{retries + 1} with model {model}")

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
            logger.debug(f"Raw Ollama response: {content[:200]}...")

            data = json.loads(content)
            return schema.model_validate(data)

        except ValidationError as e:
            last_error = e
            error_msg = f"Validation error: {e}"
            logger.warning(f"Attempt {attempt + 1} failed: {error_msg}")

            if attempt < retries:
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

        except Exception as e:
            last_error = e
            logger.error(f"Ollama error: {e}")
            if "timeout" in str(e).lower():
                raise LLMTimeoutError(f"LLM request timed out: {e}") from e
            raise LLMError(f"Ollama error: {e}") from e

    raise LLMValidationError(
        f"Failed to generate valid JSON after {retries + 1} attempts. "
        f"Last error: {last_error}"
    ) from last_error


async def _generate_json_anthropic(
    prompt: str,
    schema: Type[T],
    model: str | None = None,
    temperature: float | None = None,
    retries: int = 2,
    system_prompt: str | None = None,
) -> T:
    """Generate JSON using Anthropic API."""
    import anthropic

    api_key = getattr(settings, "anthropic_api_key", None) or os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise LLMError("ANTHROPIC_API_KEY not configured")

    model = model or getattr(settings, "llm_model", "claude-3-haiku-20240307")
    temperature = temperature if temperature is not None else settings.llm_temperature

    client = anthropic.AsyncAnthropic(api_key=api_key)

    # Build system prompt with JSON schema instructions
    json_schema = schema.model_json_schema()
    schema_instructions = (
        f"You must respond with valid JSON matching this exact schema:\n"
        f"{json.dumps(json_schema, indent=2)}\n\n"
        f"Output ONLY the JSON object, no extra text."
    )

    full_system = (system_prompt or "") + "\n\n" + schema_instructions

    last_error: Exception | None = None

    for attempt in range(retries + 1):
        try:
            logger.debug(f"Anthropic call attempt {attempt + 1}/{retries + 1} with model {model}")

            response = await client.messages.create(
                model=model,
                max_tokens=4096,
                temperature=temperature,
                system=full_system,
                messages=[{"role": "user", "content": prompt}],
            )

            content = response.content[0].text
            logger.debug(f"Raw Anthropic response: {content[:200]}...")

            data = json.loads(content)
            return schema.model_validate(data)

        except ValidationError as e:
            last_error = e
            error_msg = f"Validation error: {e}"
            logger.warning(f"Attempt {attempt + 1} failed: {error_msg}")

            if attempt < retries:
                prompt = (
                    f"The previous response failed validation. "
                    f"Error: {error_msg}. "
                    f"Please respond with valid JSON matching the schema exactly."
                )
            continue

        except json.JSONDecodeError as e:
            last_error = e
            logger.warning(f"Attempt {attempt + 1} failed: JSON decode error: {e}")
            if attempt < retries:
                prompt = f"Invalid JSON. Error: {e}. Please respond with valid JSON only."
            continue

        except anthropic.APITimeoutError as e:
            raise LLMTimeoutError(f"Anthropic request timed out: {e}") from e

        except Exception as e:
            last_error = e
            logger.error(f"Anthropic error: {e}")
            raise LLMError(f"Anthropic error: {e}") from e

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
    Generate plain text output from LLM.

    Args:
        prompt: User prompt
        model: Override default model
        temperature: Override default temperature
        system_prompt: Optional system prompt

    Returns:
        Raw text response
    """
    provider = getattr(settings, "llm_provider", "ollama")

    if provider == "anthropic":
        import anthropic

        api_key = getattr(settings, "anthropic_api_key", None) or os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise LLMError("ANTHROPIC_API_KEY not configured")

        model = model or getattr(settings, "llm_model", "claude-3-haiku-20240307")
        temperature = temperature if temperature is not None else settings.llm_temperature

        client = anthropic.AsyncAnthropic(api_key=api_key)

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = await client.messages.create(
            model=model,
            max_tokens=4096,
            temperature=temperature,
            messages=[{"role": "user", "content": prompt}],
            system=system_prompt or "",
        )

        return response.content[0].text
    else:
        import ollama

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