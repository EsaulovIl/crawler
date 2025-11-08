import os
import hashlib
import logging
from .items import EventItem, PageContentItem
from .llm_parser import (build_event_prompt,
                         llm_generate,
                         parse_llm_response)
from .exceptions import LLMError
from scrapy.exceptions import DropItem

logger = logging.getLogger(__name__)

"""
class RawHtmlPipeline:
    def open_spider(self, spider):
        os.makedirs('data/raw', exist_ok=True)

    def process_item(self, item, spider):
        # 1) берём URL
        url = item.get('url', '')
        # 2) генерируем короткий и гарантированно безопасный хеш
        url_hash = hashlib.sha1(url.encode('utf-8')).hexdigest()
        # 3) составляем имя файла из хеша
        filename = os.path.join('data', 'raw', f'{url_hash}.html')

        # 4) сохраняем HTML
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(item.get('html', ''))  # или item['raw_html'], если вы так именуете

        return item
"""


class LLMEventPipeline:
    """
    1)Принимает PageContentItem
    2)Вызывает Gemini
    3)Возвращает EventItem.
    """

    def process_item(self, item, spider):
        if not isinstance(item, PageContentItem):
            return item

        url = item["url"]
        text = item["content"]
        if not text:
            logger.info("Empty content for %s – skip LLM", url)
            return item  # или drop

        prompt = build_event_prompt(text, url)

        try:
            answer = llm_generate(prompt)
        except LLMError as e:
            logger.warning("LLM error for %s: %s", url, e)
            return item

        try:
            data = parse_llm_response(answer, url)
        except Exception as e:
            logger.warning("Parse error for %s: %s", url, e)
            return item

        data.setdefault("url", url)
        data.setdefault("tags", "Не указано")
        return EventItem(**data)


class DropIncompletePipeline:
    """
    Отбрасывает EventItem, у которых одно из критически важных полей
    осталось «Не указано». Допускаем пропуски только для:
      • event_type
      • event_format
      • organizer
    """
    # поля, которые **обязательно** должны быть заполнены
    _required = ("title", "start_date", "end_date", "location", "description")

    def process_item(self, item, spider):
        # пропускаем всё, что не EventItem
        if not isinstance(item, EventItem):
            return item

        # если хотя бы одно обязательное поле == "Не указано", то дропаем
        if any(item.get(f) == "Не указано" for f in self._required):
            raise DropItem(
                f"[DropIncompletePipeline] Incomplete item, url={item.get('url')}"
            )

        return item
