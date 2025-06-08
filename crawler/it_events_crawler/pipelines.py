import os
import hashlib

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