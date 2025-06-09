import scrapy


class PageContentItem(scrapy.Item):
    """Пред-LLM: url и очищенный русский текст страницы."""
    url = scrapy.Field()
    content = scrapy.Field()


class EventItem(scrapy.Item):
    """Пост-LLM: итоговая запись мероприятия."""
    url = scrapy.Field()
    title = scrapy.Field()
    organizer = scrapy.Field()
    start_date = scrapy.Field()
    end_date = scrapy.Field()
    # location = scrapy.Field()
    event_type = scrapy.Field()
    event_format = scrapy.Field()
    # tags = scrapy.Field()
