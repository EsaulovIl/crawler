from pydantic import BaseModel, HttpUrl, field_validator


class EventData(BaseModel):
    title: str
    organizer: str
    start_date: str
    end_date: str
    event_type: str
    event_format: str
    url: HttpUrl

    @field_validator('*', mode='before')
    @classmethod
    def strip_whitespace(cls, v: str):
        """
        Убираем внешние пробелы у всех строковых полей ещё перед валидацией.
        """
        return v.strip() if isinstance(v, str) else v
