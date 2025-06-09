import requests


def google_search(query: str, api_key, cx, num_results: int = 2) -> list[str]:
    """
    Возвращает список URL’ов по запросу через Custom Search JSON API.
    """
    search_url = "https://www.googleapis.com/customsearch/v1"
    params = {'q': query, 'key': api_key, 'cx': cx, 'num': num_results}
    resp = requests.get(search_url, params=params, timeout=3)
    resp.raise_for_status()
    items = resp.json().get('items', [])
    return [item['link'] for item in items if 'link' in item]
