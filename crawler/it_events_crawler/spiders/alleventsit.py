import scrapy
import re
from w3lib.html import remove_tags
import html
from it_events_crawler.items import EventItem


class AllEventsIT(scrapy.Spider):
    name = "alleventsit"
    start_urls = [
        "https://all-events.ru/events/calendar/city-is-nizhniy_novgorod/"
    ]

    def get_title(self, info):
        return info.css("div.event_flex_content").css("div.event_order_1").css("a.event_name_new::text").get()

    def get_start_date(self, info):
        result = info.xpath('.//div[@class="event-date"]/div[not(@class)]/text()').get()
        return result[0:10]

    def get_end_date(self, info):
        result = info.xpath('.//div[@class="event-date"]/div[not(@class)]/text()').get()
        result = result.replace('\xa0', ' ').strip()
        m = re.search(r'(\d{2}\.\d{2}\.\d{4})(?:\s*-\s*(\d{2}\.\d{2}\.\d{4}))?', result)
        return m.group(2) or m.group(1) if m else None

    def get_location(self, info):
        sel = info.css(
            "div.event_flex_content div.event_width.order_3 div.event_info_new "
            "a.event_info_new_text.svg_hybrid span:nth-of-type(2)::text, "
            "div.event_flex_content div.event_width.order_3 div.event_info_new "
            "a.event_info_new_text.svg_ span:nth-of-type(2)::text, "
            "div.event_flex_content div.event_width.order_3 div.event_info_new "
            "a.event_info_new_text.svg_offline span:nth-of-type(2)::text"
        )
        return ', '.join(sel.getall()).strip()

    def get_tags(self, info):
        return info.css("div.teg_content a::text").getall()

    def parse(self, response):
        base = "https://all-events.ru"
        for info in response.css("div.event_flex_item"):
            item = EventItem(
                title=self.get_title(info),
                start_date=self.get_start_date(info),
                end_date=self.get_end_date(info),
                location=self.get_location(info),
                url=response.url,
                organizer="Не указано",
                event_type="Не указано",
                event_format="Не указано"
            )
            rel_link = info.css("div.btn_events a::attr(href)").get()
            if rel_link:
                yield response.follow(
                    base + rel_link,
                    callback=self.parse_event,
                    meta={"item": item},
                    dont_filter=True
                )
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
        raw = response.css("div.events-content").get()
        item["description"] = self.clear_description(raw) if raw else "Не указано"
        yield item
