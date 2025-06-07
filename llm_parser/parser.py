import re
from .schema import EventData
from .exceptions import LLMParseError

# соответствие заголовков в ответе полям EventData
FIELD_MAP = {
    'Название ИТ-мероприятия': 'title',
    'Организатор': 'organizer',
    'Даты проведения': 'dates',
    'Тип мероприятия': 'event_type',
    'Формат проведения': 'event_format',
}


def parse_llm_response(raw: str, url: str) -> dict:
    """
    Извлекает поля из ответа LLM (строки вида 'Поле: "значение"').
    Возвращает валидированный словарь или кидает LLMParseError.
    """
    # инициализируем словарь с «Не указано»
    data = {v: "Не указано" for v in FIELD_MAP.values()}
    # для каждого поля ищем регуляркой
    for line in raw.splitlines():
        for label, key in FIELD_MAP.items():
            m = re.match(rf'^{re.escape(label)}\s*:\s*"(.+)"\s*$', line)
            if m:
                data[key] = m.group(1).strip()

    # добавляем URL в данные
    data['url'] = url

    # валидация через Pydantic
    try:
        event = EventData(**data)
    except Exception as e:
        raise LLMParseError(f"Failed to validate LLM response: {e}")

    return event.model_dump()
