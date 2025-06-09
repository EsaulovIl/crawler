import logging
import requests
from crawler.it_events_crawler.search import google_search
from crawler.it_events_crawler.llm_parser import clean_html
from crawler.it_events_crawler.llm_parser import extract_event_info

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_page_html(url: str) -> str | None:
    try:
        r = requests.get(url, timeout=10)
        r.raise_for_status()
        return r.text
    except Exception as e:
        logger.warning("Не удалось скачать %s: %s", url, e)
        return None


def main():
    query = "ИТ мероприятия Нижний Новгород"
    urls = google_search(query, num_results=5)
    logger.info("Найдено URL’ов: %d", len(urls))

    for url in urls:
        html = get_page_html(url)
        if not html:
            continue

        text = clean_html(html)  # убираем скрипты и стили, оставляем текст
        data = extract_event_info(text, url)
        if data:
            # Тут будет сохранение — в БД, CSV, JSON, передача в Scrapy-пайплайн
            logger.info("Извлекли: %s", data)
        else:
            logger.warning("LLM не вернул данные для %s", url)


if __name__ == "__main__":
    main()
