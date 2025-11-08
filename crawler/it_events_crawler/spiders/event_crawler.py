from urllib.parse import urlparse
from scrapy.linkextractors import LinkExtractor
from scrapy.spiders import CrawlSpider, Rule
from it_events_crawler.search import google_search
from it_events_crawler.items import PageContentItem
from it_events_crawler.utils import extract_visible_text

DENY_PATTERNS = [r'/login', r'/signin', r'/register', r'/auth', r'/logout',
                 r'/cart', r'/checkout', r'/wp-admin', r'/wp-login',
                 r'/privacy', r'/terms', r'/cookies', r'/contacts?', r'/about',
                 r'/search', r'/feed', r'/rss', r'\.pdf$', r'\.docx?$', r'\.xlsx?$', r'\.pptx?$']
DENY_EXTENSIONS = ['jpg', 'jpeg', 'png', 'gif', 'svg', 'webp', 'ico', 'css', 'js', 'woff', 'woff2',
                   'ttf', 'eot', 'zip', 'rar', '7z', 'mp4', 'mp3', 'avi', 'mkv']
SOCIAL_DOMAINS = ['facebook.com', 'twitter.com', 'vk.com', 'instagram.com',
                  'youtube.com', 'youtu.be', 't.me', 'telegram.me', 'linkedin.com']

LANGS = "en|de|fr|es|it|pt|nl|pl|uk|tr|zh|ja|ko|ar|sv|fi|cs|sk|hu|cn"

# языковой» паттерн
DENY_LANG_PATTERN = (
    rf"https?://(?:{LANGS})\."  # en.example.com
    rf"|/(?:(?:{LANGS}))(?:/|$)"  # /en/...
    rf"|[?&](?:lang|locale|hl|l)="  # ?lang=en
    rf"(?:(?:{LANGS})(?:[_-][A-Z]{{2}})?)\b"
    rf"|[-_/](?:{LANGS})(?:[-_/]|$)"
)


class EventCrawlSpider(CrawlSpider):
    name = "events"
    custom_settings = {
        "DOWNLOAD_DELAY": 2.0,
        "DEPTH_LIMIT": 2,
        "CLOSESPIDER_PAGECOUNT": 1200,
        "LOG_LEVEL": "INFO"
    }

    @classmethod
    def from_crawler(cls, crawler, *args, **kwargs):
        spider = super().from_crawler(crawler, *args, **kwargs)

        # читаем настройки и переменные окружения
        s = crawler.settings
        spider.query = s.get('QUERY', 'ИТ мероприятия')  # fallback
        spider.google_key = s.get('GOOGLE_API_KEY')
        spider.cse_id = s.get('CUSTOM_SEARCH_ENGINE_ID')

        # формируем стартовые URL-ы
        spider.start_urls = google_search(
            spider.query, spider.google_key, spider.cse_id, num_results=4
        )

        print(spider.start_urls)

        # allowed_domains - все домены из start_urls
        spider.allowed_domains = [
            urlparse(u).netloc.replace('www.', '') for u in spider.start_urls
        ]

        # собираем правила обхода
        le = LinkExtractor(
            allow_domains=spider.allowed_domains,
            deny_domains=SOCIAL_DOMAINS,
            deny=DENY_PATTERNS + [DENY_LANG_PATTERN],
            deny_extensions=DENY_EXTENSIONS,
            unique=True,
        )
        spider.rules = [Rule(le, callback='parse_event', follow=True)]
        # обновляем внутренние структуры CrawlSpider
        spider._compile_rules()

        return spider

    def parse_event(self, response):
        clean = extract_visible_text(response.text)
        print(response.url)
        print(clean)
        yield PageContentItem(
            url=response.url,
            content=clean
        )
