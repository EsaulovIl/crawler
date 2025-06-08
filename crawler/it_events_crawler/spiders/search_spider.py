import scrapy
from it_events_crawler.search import google_search
from it_events_crawler.items import EventItem


class SearchSpider(scrapy.Spider):
    name = "search"
    custom_settings = {
        'DOWNLOAD_DELAY': 1.0,
        'LOG_LEVEL': 'WARNING',  # убираем лишний лог
        # экспортим в JSON без доп. пайплайнов
        'FEEDS': {
            'data/events.json': {
                'format': 'json',
                'encoding': 'utf8',
                'indent': 2,
                'fields': ['url', 'html'],
            }
        }
    }

    def start_requests(self):
        # берём query, ключ и CX из настроек Scrapy
        query = self.settings.get('QUERY')
        api_key = self.settings.get('GOOGLE_API_KEY')
        cx = self.settings.get('CUSTOM_SEARCH_ENGINE_ID')

        # получаем seed-URL'ы
        urls = google_search(query, api_key, cx, num_results=5)
        for url in urls:
            yield scrapy.Request(url, callback=self.parse_event)

    def parse_event(self, response):
        # отдаём URL + весь HTML дальше в пайплайны
        yield {
            'url': response.url,
            'html': response.text
        }
