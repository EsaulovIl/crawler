import scrapy
import re
from it_events_crawler.items import EventItem


class It52Spider(scrapy.Spider):
    name = "it52"
    start_urls = [
        "https://it52.info/events?kind=all&status=future",
        "https://it52.info/events?kind=all&status=past"
    ]

    def get_title(self, info):
        return info.css("h2.event-header").css("a::text").get()

    def get_date(self, info):
        pattern = r'\b\d{4}-\d{2}-\d{2}\b'
        href_info = info.css("a.event-date-inversed").attrib["href"]
        dates = re.findall(pattern, href_info)
        return dates[0]

    def get_location(self, info):
        address = info.css('span[itemprop="address"]::text').get()
        building = info.css('span[itemprop="name"]::text').get()
        return f"{address}, {building}" if address and building else address or building or ""

    def get_description(self, info):
        description = info.css("div.event-description").get()
        description = re.sub(r'</?(br|p)[^>]*>', '\n', description)
        description = re.sub(r'<[^>]+>', '', description)
        description = re.sub(r'\n+', '\n', description).strip()

        return description

    def get_tags(self, info):
        div = info.css("div.event-tags").get()
        cleaned_tags = []
        if div:
            tags = re.findall(r'>(#\w+)<', div)
            cleaned_tags = [tag[1:] for tag in tags]

        return cleaned_tags

    def parse(self, response):
        for info in response.css("div.event.panel.panel-default"):
            yield EventItem(
                title=self.get_title(info),
                start_date=self.get_date(info),
                end_date=self.get_date(info),
                location=self.get_location(info),
                description=self.get_description(info),
                url=response.url,
                organizer="Не указано",
                event_type="Не указано",
                event_format="Не указано"
            )
