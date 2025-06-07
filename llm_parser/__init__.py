from .client import llm_generate
from .prompt import build_event_prompt
from .parser import parse_llm_response
from .exceptions import LLMError


def extract_event_info(text: str, url: str) -> dict | None:
    """
    Высокоуровневая функция: из текста страницы и её URL
    возвращает словарь с полями EventData или None при ошибке.
    """
    prompt = build_event_prompt(text, url)
    try:
        raw = llm_generate(prompt)
        return parse_llm_response(raw, url)
    except LLMError as e:
        return None
