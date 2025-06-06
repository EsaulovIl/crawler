import os
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import google.generativeai as genai
import logging

# Настройка логирования: вывод в консоль с уровнем INFO и выше
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# Загрузка переменных из .env
load_dotenv()

API_KEY = os.getenv('GOOGLE_API_KEY')
CX = os.getenv('CUSTOM_SEARCH_ENGINE_ID')
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY or not CX or not GEMINI_API_KEY:
    logger.error("Не заданы необходимые переменные окружения. Проверьте .env файл.")
    exit(1)

genai.configure(api_key=GEMINI_API_KEY)

def google_search(query, api_key, cx, num_results=10):
    """
    Поиск в Google с использованием Custom Search JSON API.

    :param query: строка запроса
    :param api_key: ваш API ключ
    :param cx: идентификатор поисковой системы
    :param num_results: число результатов (максимум 10 за один запрос)
    :return: список найденных URL
    """
    search_url = "https://www.googleapis.com/customsearch/v1"
    params = {
        'q': query,
        'key': api_key,
        'cx': cx,
        'num': num_results
    }

    try:
        response = requests.get(search_url, params=params, timeout=10)
        response.raise_for_status()
        results = response.json()
    except requests.RequestException as e:
        logger.error("Ошибка при поиске в Google API: %s", e)
        return []

    urls = []
    for item in results.get('items', []):
        link = item.get('link')
        if link:
            urls.append(link)
    logger.info("Найдено %d результатов", len(urls))
    return urls


def extract_event_info_from_text(text, url):
    """
    Использует Gemini API для извлечения информации об ИТ-мероприятии из текста.
    Возвращает ответ, полученный от модели.
    """
    #client = genai.Client(api_key = GEMINI_API_KEY)

    model = genai.GenerativeModel("gemini-2.0-flash")

    prompt = """
    Ты — эксперт по извлечению структурированной информации из текста. 
    Твоя задача — проанализировать предоставленный текст страницы, на которой описывается ИТ-мероприятие, и выделить из него следующие сведения:

    Название ИТ-мероприятия
    Организатор
    Даты проведения мероприятия
    Тип мероприятия (например, конференция, хакатон, семинар и т.д.)
    Адрес проведения

    Если какая-либо информация отсутствует или не может быть уверенно определена, укажи вместо неё значение «Не указано».

    Придерживайся следующего формата ответа (каждое поле — с новой строки):
    Название ИТ-мероприятия: "..."
    Организатор: "..."
    Даты проведения: "..."
    Тип мероприятия: "..."
    Формат проведения: "..."
    
    Инструкции:
    Прочитай весь предоставленный текст.
    Идентифицируй и выдели ключевые фрагменты, содержащие название мероприятия, данные об организаторе, дата или период проведения, тип и формат мероприятия.
    Если информация разбросана по тексту или представлена в виде описания, собери её и представь в требуемой форме.
    Убедись, что итоговый ответ структурирован и соответствует заданному формату.
    
    Пример:

    Входной текст:
    "В ближайшую субботу, 12 июля 2025 года, в конференц-центре 'TechHub' пройдет ежегодная IT-конференция 'Innovate 2025'. Мероприятие организовано компанией 'TechEvents'. На конференции запланировано выступление ведущих специалистов в области технологий."

    Вывод модели:
    Название ИТ-мероприятия: "Innovate 2025"
    Организатор: "TechEvents"
    Даты проведения: "12 июля 2025"
    Тип мероприятия: "Конференция"
    Формат проведения: "Очно"
    
    Вот текст страницы:
    {text}
    """

    full_prompt = prompt.format(text = text, url = url)

    generation_config = genai.types.GenerationConfig(
        max_output_tokens=1000,
        temperature=0.2
    )

    try:
        response = model.generate_content(
            full_prompt,
            generation_config=generation_config
        )
        logger.info("Ответ от Gemini API получен для %s", url)
    except Exception as e:
        logger.error("Ошибка при вызове Gemini API для URL %s: %s", url, e)
        return None

    return response.text



def get_page_text(url):
    """
        Загрузка и очистка текста со страницы.
        Возвращает очищенный текст или None при ошибке.
    """
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'html.parser')

        # Удаляем скрипты и стили
        for script_or_style in soup(['script', 'style']):
            script_or_style.decompose()

        text = soup.get_text(separator='\n')
        cleaned_text = '\n'.join(line.strip() for line in text.splitlines() if line.strip())
        logger.info("Страница %s успешно загружена", url)
        return cleaned_text
    except Exception as e:
        logger.error("Ошибка при получении содержимого страницы %s: %s", url, e)
        return None

def main():
    # Пример запроса
    query = "ИТ мероприятия Нижний Новгород"
    logger.info("Запускаем поиск: %s", query)

    urls = google_search(query, API_KEY, CX, num_results=5)

    if not urls:
        logger.warning("Ничего не найдено по запросу: %s", query)
        return

    # Обработка найденных URL
    for url in urls:
        logger.info("Начало обработки URL: %s", url)
        page_text = get_page_text(url)
        if not page_text:
            logger.warning("Не удалось получить текст со страницы: %s", url)
            continue

        result = extract_event_info_from_text(page_text[:14000], url)  # ограничение по токенам
        if result:
            print(result)
        else:
            logger.error("Не удалось извлечь информацию для %s", url)


if __name__ == '__main__':
    main()