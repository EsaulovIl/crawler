import re, html
from bs4 import BeautifulSoup, NavigableString, Tag, Comment

try:
    from readability import Document

    USE_READABILITY = True
except ImportError:
    USE_READABILITY = False

NON_CONTENT = re.compile(
    r"(nav|menu|footer|header|banner|cookie|share|social|sidebar|ads?)",
    re.I
)

RE_GARBAGE_LINE = re.compile(
    r"^(?:share|поделиться|cookies?|facebook|vk\.com|twitter|instagram"
    r"|\d{1,2}\s?[–-]\s?\d{1,2}(?!\s*(январ|феврал|март|апрел|мая|июн|июл|"
    r"август|сентябр|октябр|ноябр|декабр)))\b",
    re.I
)


def _sanitize_soup(soup: BeautifulSoup) -> BeautifulSoup:
    """
    Удаляем тех-теги, комментарии, <header>/<footer> и пр.
    """
    for sel in ["header", "footer", '[role="banner"]', '[role="contentinfo"]']:
        for node in soup.select(sel):
            node.decompose()

    for t in soup(["script", "style", "iframe", "svg", "canvas", "noscript"]):
        t.decompose()

    for c in soup(text=lambda t: isinstance(t, Comment)):
        c.extract()

    return soup


def _container(soup: BeautifulSoup) -> Tag:
    for sel in ["article", "main", '[role="main"]', "section", "body"]:
        tag = soup.select_one(sel)
        if tag and len(tag.get_text(strip=True)) > 100:
            return tag
    return soup


def _text_from_node(node: Tag) -> str:
    buf = []
    for el in node.descendants:
        if isinstance(el, NavigableString):
            buf.append(str(el))
        elif el.name == "br":
            buf.append("\n")
        elif el.name == "li":
            buf.append("\n• ")
        elif el.name in ("p", "div"):
            buf.append("\n\n")
        elif el.name in ("td", "th"):
            buf.append("  ")
    txt = "".join(buf)
    return html.unescape(txt)


def extract_visible_text(html_raw: str) -> str:
    soup = _sanitize_soup(BeautifulSoup(html_raw, "lxml"))
    cont = _container(soup)
    text = _text_from_node(cont)

    # нормализуем пробелы
    lines = [re.sub(r"\s+", " ", ln).strip() for ln in text.splitlines()]
    clean = []
    for ln in lines:
        if not ln or RE_GARBAGE_LINE.match(ln):
            continue
        # строка-мусор если ≤3 символа каждое слово
        if all(len(w) <= 3 for w in ln.split()):
            continue
        clean.append(ln)

    result = "\n".join(clean).strip()
    if len(result) >= 150:
        return result

    # Fallback: грубый html -> text + сокращение до 1k симв.
    rough = soup.get_text(separator="\n")
    rough = re.sub(r"[ \t]{2,}", " ", rough)
    rough = re.sub(r"\n{3,}", "\n\n", rough).strip()
    return rough[:1000]


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
    # первые 3
    selected.extend(paras[:3])
    # «ключевые» абзацы
    key_paras = [p for p in paras if any(kw in p.lower() for kw in keywords)]
    for p in key_paras:
        if p not in selected:
            selected.append(p)
            if len(selected) >= max_paras:
                break
    # если ещё мало — добавляем подряд со следующей позиции
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
        total += len(p) + 2
    return "\n\n".join(out)
