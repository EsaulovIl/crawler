import re
from .schema import EventData
from it_events_crawler.exceptions import LLMParseError

# соответствие заголовков в ответе полям EventData
FIELD_MAP = {
    'Название ИТ-мероприятия': 'title',
    'Организатор': 'organizer',
    'Дата начала': 'start_date',
    'Дата окончания': 'end_date',
    'Тип мероприятия': 'event_type',
    'Формат проведения': 'event_format',
    'Адрес мероприятия': 'location',
    'Описание мероприятия': 'description',
}


def parse_llm_response(raw: str, url: str) -> dict:
    """
    Извлекает поля из ответа LLM (строки вида Поле: "значение").
    Возвращает валидированный словарь или ошибку LLMParseError.
    """
    # инициализируем словарь с «Не указано»
    data = {v: "Не указано" for v in FIELD_MAP.values()}
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

    return event.model_dump(mode = "json")
