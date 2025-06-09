import os
import time
import logging
from collections import deque
import google.generativeai as genai
from google.api_core import exceptions as gex
from it_events_crawler.exceptions import LLMTimeoutError, LLMQuotaError

logger = logging.getLogger(__name__)
GEMINI_KEY = os.getenv("GEMINI_API_KEY")

_CALLS_LIMIT = 15
_TIME_WINDOW = 60.0

genai.configure(api_key=GEMINI_KEY)

_last_calls: deque[float] = deque(maxlen=_CALLS_LIMIT)


def _rate_limit_sleep() -> None:
    """
    Блокирует выполнение, если за последний интервал было ≥ лимита вызовов.
    """
    now = time.time()
    if len(_last_calls) < _CALLS_LIMIT:
        return

    earliest = _last_calls[0]
    delta = now - earliest
    if delta < _TIME_WINDOW:
        time_to_sleep = _TIME_WINDOW - delta + 0.1
        time.sleep(time_to_sleep)


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
    _rate_limit_sleep()
    model = genai.GenerativeModel("gemini-2.0-flash")
    cfg = genai.types.GenerationConfig(
        max_output_tokens=max_output_tokens,
        temperature=temperature
    )

    attempt = 0
    while True:
        try:
            response = model.generate_content(prompt, generation_config=cfg)
            _last_calls.append(time.time())  # успешно — отмечаем вызов
            return response.text
        except gex.ResourceExhausted as e:
            attempt += 1
            if attempt > retries:
                logger.error("Rate limit exceeded: %s", e)
                raise LLMQuotaError(str(e))
            time.sleep(backoff ** attempt)
        except gex.DeadlineExceeded as e:
            attempt += 1
            if attempt > retries:
                logger.error("Service unavailable: %s", e)
                raise LLMTimeoutError(str(e))
            time.sleep(backoff ** attempt)
        except Exception as e:
            logger.exception("Unexpected LLM error")
            raise
