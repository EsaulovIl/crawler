class LLMError(Exception):
    """Базовый класс ошибок LLM"""

class LLMTimeoutError(LLMError):
    """Сервис недоступен или таймаут"""

class LLMQuotaError(LLMError):
    """Превышен rate-limit / квота"""

class LLMParseError(LLMError):
    """Не удалось распарсить ответ модели"""
