import os
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv('GOOGLE_API_KEY')
CX = os.getenv('CUSTOM_SEARCH_ENGINE_ID')


def google_search(query: str, num_results: int = 10) -> list[str]:
    """
    Возвращает список URL’ов по запросу через Custom Search JSON API.
    """
    search_url = "https://www.googleapis.com/customsearch/v1"
    params = {'q': query, 'key': API_KEY, 'cx': CX, 'num': num_results}
    resp = requests.get(search_url, params=params, timeout=10)
    resp.raise_for_status()
    items = resp.json().get('items', [])
    return [item['link'] for item in items if 'link' in item]
