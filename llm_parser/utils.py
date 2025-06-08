import re
from bs4 import BeautifulSoup

try:
    from readability import Document

    USE_READABILITY = True
except ImportError:
    USE_READABILITY = False


def clean_html(html: str) -> str:
    """
    Убираем скрипты/стили, возвращаем чистый текст.
    """
    soup = BeautifulSoup(html, 'html.parser')
    for tag in soup(['script', 'style', 'header', 'footer', 'nav', 'aside']):
        tag.decompose()
    text = soup.get_text(separator='\n')
    lines = [line.strip() for line in text.splitlines()]
    # отсеиваем короткие или «мусорные» строки
    filtered = [
        line for line in lines
        if len(line) >= 30
           and not re.match(r'^\W*$', line)
    ]
    return '\n\n'.join(filtered)


def extract_main_content(html: str) -> str:
    """
    С помощью readability-lxml вытягиваем основной текст.
    Falls back to clean_html.
    """
    if USE_READABILITY:
        doc = Document(html)
        content_html = doc.summary()
        return clean_html(content_html)
    else:
        return clean_html(html)


def extract_metadata(html: str) -> dict:
    """
    Достаём <title> и <meta name="description">.
    """
    soup = BeautifulSoup(html, 'html.parser')
    title = soup.title.string.strip() if soup.title else ''
    desc = ''
    m = soup.find('meta', attrs={'name': 'description'})
    if m and m.get('content'):
        desc = m['content'].strip()
    return {'title': title, 'description': desc}


def select_relevant_paragraphs(text: str, keywords: list[str],
                               max_paras: int = 20) -> list[str]:
    """
    Из списка абзацев выбираем:
      1) Первые 3 абзаца
      2) До 5 абзацев, где встречается одно из ключевых слов
      3) Затем следующие подряд до достижения max_paras
    """
    paras = [p for p in text.split('\n\n') if p]
    selected = []
    # 1) первые 3
    selected.extend(paras[:3])
    # 2) «ключевые» абзацы
    key_paras = [p for p in paras if any(kw in p.lower() for kw in keywords)]
    for p in key_paras:
        if p not in selected:
            selected.append(p)
            if len(selected) >= max_paras:
                break
    # 3) если ещё мало — добавляем подряд со следующей позиции
    idx = len(selected)
    while len(selected) < max_paras and idx < len(paras):
        if paras[idx] not in selected:
            selected.append(paras[idx])
        idx += 1
    return selected


def chunk_paragraphs(paragraphs: list[str],
                     max_length: int = 13000) -> str:
    """
    Склеиваем абзацы, пока не превысим max_length.
    """
    out = []
    total = 0
    for p in paragraphs:
        if total + len(p) + 2 > max_length:
            break
        out.append(p)
        total += len(p) + 2  # плюс два перевода строки
    return "\n\n".join(out)
