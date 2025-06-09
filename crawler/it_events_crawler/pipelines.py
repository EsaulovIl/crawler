import os
import hashlib
import logging
from .items import EventItem, PageContentItem
from .llm_parser import (build_event_prompt,
                         llm_generate,
                         parse_llm_response)
from .exceptions import LLMError

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
        return EventItem(**data)
