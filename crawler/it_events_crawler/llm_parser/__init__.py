"""
Подпакет с логикой работы LLM:
    build_event_prompt – сбор промпта
    llm_generate – вызов Gemini
    parse_llm_response – разбор ответа
Ровно те же функции, что были раньше, но теперь живут в одном месте.
"""

from .prompt import build_event_prompt  # noqa: F401
from .client import llm_generate  # noqa: F401
from .parser import parse_llm_response  # noqa: F401

__all__ = [
    "build_event_prompt",
    "llm_generate",
    "parse_llm_response",
]
