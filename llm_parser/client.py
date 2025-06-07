import os
import time
import logging
import google.generativeai as genai
from .exceptions import LLMTimeoutError, LLMQuotaError

logger = logging.getLogger(__name__)
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

genai.configure(api_key=GEMINI_KEY)


def llm_generate(prompt: str,
        max_output_tokens: int = 1000,
        temperature: float = 0.2,
        retries: int = 3,
        backoff: float = 2.0
) -> str:
    """
    Генерирует ответ из Gemini-2.0-flash по промпту.
    Делает retry при таймаутах и rate-limit’ах.
    """
    model = genai.GenerativeModel("gemini-2.0-flash")
    cfg = genai.types.GenerationConfig(
        max_output_tokens=max_output_tokens,
        temperature=temperature
    )

    attempt = 0
    while True:
        try:
            response = model.generate_content(
                prompt,
                generation_config=cfg
            )
            return response.text
        except genai.error.RateLimitError as e:
            attempt += 1
            if attempt > retries:
                logger.error("Rate limit exceeded: %s", e)
                raise LLMQuotaError(str(e))
            time.sleep(backoff ** attempt)
        except genai.error.ServiceUnavailableError as e:
            attempt += 1
            if attempt > retries:
                logger.error("Service unavailable: %s", e)
                raise LLMTimeoutError(str(e))
            time.sleep(backoff ** attempt)
        except Exception as e:
            logger.exception("Unexpected LLM error")
            raise
