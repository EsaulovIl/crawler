from bs4 import BeautifulSoup


def chunk_text(text: str, max_length: int) -> str:
    """
    Обрезаем текст на последний перенос строки до max_length.
    """
    if len(text) <= max_length:
        return text
    idx = text.rfind('\n', 0, max_length)
    return text[:idx] if idx > 0 else text[:max_length]


def clean_html(html: str) -> str:
    """
    Убираем <script>, <style> и возвращаем чистый текст.
    """
    soup = BeautifulSoup(html, 'html.parser')
    for tag in soup(['script', 'style']):
        tag.decompose()
    lines = (line.strip() for line in soup.get_text().splitlines())
    return '\n'.join(line for line in lines if line)
