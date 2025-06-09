import os

from dotenv import load_dotenv

load_dotenv()

BOT_NAME = 'it_events_crawler'
SPIDER_MODULES = ['it_events_crawler.spiders']
NEWSPIDER_MODULE = 'it_events_crawler.spiders'

# отключаем robots.txt, если нужно
ROBOTSTXT_OBEY = False

# пайплайн сохраняет сырые HTML
ITEM_PIPELINES = {
    # 'it_events_crawler.pipelines.RawHtmlPipeline': 300,
    "it_events_crawler.pipelines.LLMEventPipeline": 300,
}

# Google Custom Search API
GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
CUSTOM_SEARCH_ENGINE_ID = os.getenv('CUSTOM_SEARCH_ENGINE_ID')
QUERY = "ИТ мероприятия Нижний Новгород"

FEEDS = {
    "data/events_structured.json": {
        "format": "json",
        "encoding": "utf8",
        "indent": 2,
        "item_classes": ["it_events_crawler.items.EventItem"],
        "fields": [
            "title", "organizer", "start_date", "end_date",
            "event_type", "event_format",
            "url"
        ],
    },
    # DEBUG файл: приходят очищенные html
    "data/events_raw.json": {
        "format": "json",
        "encoding": "utf8",
        "indent": 2,
        "item_classes": ["it_events_crawler.items.PageContentItem"],
        "fields": ["url", "content"],
    },
}

# Отключить излишний вывод в консоль
LOG_LEVEL = 'WARNING'
