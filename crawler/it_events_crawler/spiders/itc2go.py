import scrapy
import re
from w3lib.html import remove_tags
from urllib.parse import urljoin
import html
from it_events_crawler.items import EventItem


class Itc2Go(scrapy.Spider):
    name = "itc2go"
    start_urls = [
        "https://ict2go.ru/regions/Nizhny_Novgorod/"
    ]

    def get_title(self, info):
        return info.css("a.media-left.image-link").attrib["title"]

    def get_start_date(self, info):
        result = info.css("div.date-place::text").get()
        match = re.search(r'(\d{2}\.\d{2}\.\d{4})(?:\s*\|\s*(\S.*))?', result)
        if match:
            date = match.group(1)
            city = match.group(2).strip() if match.group(2) else None
        return date

    def get_end_date(self, info):
        return None

    def get_location(self, info):  # надо переходить по ссылке
        return ""

    def get_description(self, info):
        return ""

    def get_tags(self, info):
        tags = info.css("div.event-themes a::text").getall()
        return tags

    def parse(self, response):
        base = "https://ict2go.ru"
        for info in response.css("div.index-events-item.media"):
            rel_link = info.css("a.event-title").attrib["href"]
            if "/events" not in rel_link:
                continue

            item = EventItem(
                title=self.get_title(info),
                start_date=self.get_start_date(info),
                # url=response.url,
                organizer="Не указано",
                event_type="Не указано",
                event_format="Не указано",
                tags=self.get_tags(info)
            )

            href = info.css("a.event-title::attr(href)").get()
            if href and "/events/" in href:
                abs_url = urljoin(response.url, href)
                yield response.follow(
                    abs_url,
                    callback=self.parse_event,
                    meta={"item": item},
                    dont_filter=True
                )
                item["url"] = abs_url
            else:
                item["description"] = "Не указано"
                yield item

    def clear_description(self, raw_html):
        text = remove_tags(raw_html)
        text = html.unescape(text)
        text = text.replace('\r', '').replace('\t', '')
        lines = [re.sub(r' {2,}', ' ', line).strip() for line in text.split('\n')]
        lines = [line for line in lines if line]

        return '\n'.join(lines)

    def parse_event(self, response):
        item = response.meta["item"]

        date_info_html = response.css("p.date-info").get()
        if date_info_html:
            date_info_text = self.clear_description(date_info_html)

            date_range = re.search(r'(\d{2}\.\d{2}\.\d{4})\s*-\s*(\d{2}\.\d{2}\.\d{4})', date_info_text)
            single_date = re.search(r'(\d{2}\.\d{2}\.\d{4})', date_info_text)

            if date_range:
                item["end_date"] = date_range.group(2)
            elif single_date:
                item["end_date"] = single_date.group(1)
            else:
                item["end_date"] = "Не указано"
        else:
            item["end_date"] = "Не указано"

        raw = response.css("div.tab-item.description-info").get()
        item["description"] = self.clear_description(raw) if raw else "Не указано"

        location = response.css("p.place-info").get()
        item["location"] = self.clear_description(location)[len("Место проведения: "):].replace("\n",
                                                                                                "") if location else "Не указано"

        yield item
