import scrapy


class EventItem(scrapy.Item):
    url = scrapy.Field()
    raw_html = scrapy.Field()
