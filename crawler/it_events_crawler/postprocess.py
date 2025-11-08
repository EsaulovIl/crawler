import os
import json, html, sys, re, emoji, sqlite3
import networkx as nx
from pathlib import Path
from fuzzywuzzy import fuzz
from datetime import datetime, date
from gigachat import GigaChat
from bs4 import BeautifulSoup
from collections import defaultdict
from gigachat.models import Chat, Messages, MessagesRole
from dotenv import load_dotenv

load_dotenv()

GIGACHAT_API_KEY = os.getenv('GIGACHAT_API_KEY')
CA_BUNDLE = None
VERIFY_SSL = False

model_params = {
    "model": "GigaChat",
    "temperature": 0.3,
    "top_p": 0.95,
    "max_tokens": 1024,
    "repetition_penalty": 1.05,
    "stream": False,
    "update_interval": 0
}


def clean(json_path):
    def clean_text(text):
        if not isinstance(text, str):
            return text
        text = emoji.replace_emoji(text, replace='')
        text = BeautifulSoup(text, "html.parser").get_text()
        text = re.sub(r'[^\w\s.,:;!?/()\[\]\"\'–—\-]', '', text)
        text = re.sub(r'\s+', ' ', text)
        text = text.replace('\r', '').replace('\n', ' ')
        return text.strip()

    def convert_date(date_str):
        for fmt in ("%Y-%m-%d", "%d.%m.%Y", "%d/%m/%Y"):
            try:
                return datetime.strptime(date_str, fmt).strftime("%Y-%m-%d")
            except ValueError:
                continue
        return date_str

    with open(json_path, 'r', encoding='utf-8') as infile:
        data = json.load(infile)

    cleaned = []
    for obj in data:
        obj["title"] = clean_text(obj.get("title", ""))
        obj["location"] = clean_text(obj.get("location", ""))
        obj["description"] = clean_text(obj.get("description", ""))
        obj["start_date"] = convert_date(obj.get("start_date", ""))
        obj["end_date"] = convert_date(obj.get("end_date", ""))

        cleaned.append(obj)

    with open(json_path, 'w', encoding='utf-8') as outfile:
        json.dump(cleaned, outfile, ensure_ascii=False, indent=4)


def gigachat_1(json_path):
    prompt_system_1 = """
    На вход ты получишь 3 параметра:
    - location (место проведения мероприятия)
    - title (заголовок мероприятия)
    - description (описание мероприятия)

    Твоя задача: Определить релевантность мероприятия
    Мероприятие релевантно, если оно:
    - Проходит ТОЛЬКО в Нижнем Новгороде. Если в адресе, например, указан другой город(Например, г. Москва, г. Санкт-Петербург, г. Казань и другие города), то данное мероприятие не релевантно
    - Если мероприятие проходит онлайн, но не в Нижнем Новгороде, то оно считается не релевантным
    - Относится к сфере ИТ
    Если релевантно, помечай цифрой 1. Если нет — 0

    Формат вывода:
    Только одна цифра (1 или 0), ничего больше 
    """.strip()

    try:
        entries = json.loads(Path(json_path).read_text(encoding="utf-8"))
    except Exception as e:
        print(f"Не удалось открыть {json}: {e}", file=sys.stderr)
        return

    giga = GigaChat(
        credentials=GIGACHAT_API_KEY,
        ca_bundle_file=CA_BUNDLE,
        verify_ssl_certs=VERIFY_SSL,
    )

    results = []

    for obj in entries:
        title = html.unescape(obj.get("title", ""))
        description = html.unescape(obj.get("description", ""))
        location = html.unescape(obj.get("location", ""))
        start_date = html.unescape(obj.get("start_date", ""))
        end_date = html.unescape(obj.get("end_date", ""))
        tags = html.unescape(obj.get("tags", []))
        organizer = html.unescape(obj.get("organizer", []))
        event_type = html.unescape(obj.get("event_type", []))
        event_format = html.unescape(obj.get("event_format", []))
        url = html.unescape(obj.get("url", []))

        try:
            user_msg = f"location: {location}\ntitle: {title}\ndescription: {description}"

            print(user_msg)

            payload = Chat(
                messages=[
                    Messages(role=MessagesRole.SYSTEM, content=prompt_system_1),
                    Messages(role=MessagesRole.USER, content=user_msg),
                ],
                **model_params,
            )

            try:
                response = giga.chat(payload)
                chat_ans = response.choices[0].message.content.strip()
                print(chat_ans)
                print()

            except Exception as e:
                print(f"Ошибка запроса: {e}", file=sys.stderr)
                chat_ans = "0"
                print(chat_ans)
                print()
        except Exception as e:
            print(f"Ошибка разбора даты: {e}", file=sys.stderr)
            chat_ans = "0"

        results.append({
            "title": title,
            "organizer": organizer,
            "description": description,
            "location": location,
            "start_date": start_date,
            "end_date": end_date,
            "event_type": event_type,
            "event_format": event_format,
            "tags": tags,
            "url": url,
            "relevant": chat_ans,
        })

    for ev in results:
        for fld in ("start_date", "end_date"):
            if isinstance(ev[fld], date):
                ev[fld] = ev[fld].strftime("%Y-%m-%d")

    Path(json_path).write_text(
        json.dumps(results, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print(f"Обработано: {len(results)} шт.")
    print(f"Итог сохранён в {Path(json_path).resolve()}")


STOP = set("""
    of the a an for to              # англ. артикли / предлоги
    на в по                         # рус. предлоги
    2025 2024 2023 2022 2021 2020   # частые годы
""".split())

RX_NONALNUM = re.compile(r"[^\w]+", re.U)  # всё, кроме букв/цифр


def norm_str(s: str) -> str:
    """Нижний регистр, одиночные пробелы, без стоп-слов"""
    words = RX_NONALNUM.sub(" ", s.lower()).split()
    return " ".join(w for w in words if w not in STOP)


def extract_city(loc: str) -> str:
    """Наивно берём первое слово-город (г. Москва → москва)"""
    m = re.search(r"[А-ЯA-ZЁ][\w\-]+", loc)
    return m.group(0).lower() if m else ""


# Основная функция
def deduplicate(json_path: str, *, name_thr=85, loc_thr=85) -> None:
    p = Path(json_path)
    try:
        entries = json.loads(p.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"Не удалось открыть {p}: {e}", file=sys.stderr)
        return

    # строим ключ для быстрой группировки
    buckets = defaultdict(list)  # key -> [(idx, entry), ...]
    for idx, ev in enumerate(entries):
        if ev.get("relevant") == "0":  # уже помечено
            buckets[f"___irrelevant___"].append((idx, ev))
            continue

        core_title = norm_str(ev.get("title", ""))
        city = extract_city(ev.get("location", ""))
        ev_type = (ev.get("event_type") or "").lower()

        key = f"{core_title}|{ev_type}|{city}"
        buckets[key].append((idx, ev))

    # внутри ищем мягкие дубли
    fixed = []  # (orig_idx, entry)

    def is_dup(a, b) -> bool:
        # если форматы разные и оба известны → не дубликаты
        if a.get("event_type") and b.get("event_type") \
                and a["event_type"] != b["event_type"]:
            return False
        name_sim = fuzz.token_set_ratio(a["title"], b["title"])
        loc_sim = fuzz.token_set_ratio(a["location"], b["location"])
        return name_sim >= name_thr and loc_sim >= loc_thr

    print("\nПоиск дублей…")

    for key, group in buckets.items():
        if len(group) == 1:
            fixed.append(group[0])
            continue

        # строим граф «похожих» записей
        G = nx.Graph()
        G.add_nodes_from(range(len(group)))

        for i in range(len(group)):
            for j in range(i + 1, len(group)):
                if is_dup(group[i][1], group[j][1]):
                    G.add_edge(i, j)

        for comp in nx.connected_components(G):
            comp = list(comp)
            if len(comp) == 1:  # уникальная запись
                fixed.append(group[comp[0]])
                continue

            # выбираем «самую полную» как оригинал
            comp_sorted = sorted(
                comp,
                key=lambda k: len(group[k][1].get("description", "")),
                reverse=True
            )

            orig_idx, orig = group[comp_sorted[0]]
            fixed.append((orig_idx, orig))  # оставляем

            for dup_k in comp_sorted[1:]:
                dup_idx, dup = group[dup_k]
                dup["relevant"] = "0"  # помечаем
                fixed.append((dup_idx, dup))

                print(f"  • дубль → «{dup['title']}»")

    fixed_sorted = sorted(fixed, key=lambda x: x[0])
    result = [ev for _, ev in fixed_sorted]

    p.write_text(json.dumps(result, ensure_ascii=False, indent=2),
                 encoding="utf-8")
    print(f"\nДедупликация завершена. Итог: {len(result)} записей.")
    print(f" Файл сохранён: {p.resolve()}")


def gigachat_2(json_path):
    prompt_system_2 = """
    На вход ты получишь 3 параметра:
    - tags (тэг мероприятия)
    - title (заголовок мероприятия)
    - description (описание мероприятия)

    Твоя задача: Классифицировать тему
    Если в названии, описании или теге явно указано, к какому типу относится событие (например, «Хакатон», «Конференция», «Митап» и т. д.), используйте эту информацию для классификации — но только в том случае, если это действительно соответствует контексту.

    Выберите только одну тему из следующего списка:
    (1) Вебинары — это одноразовый онлайн-семинар или презентация в реальном времени, длительностью 1–2 часа. Обычно включает лекцию, обсуждение и ответы на вопросы.
    Для нескольких занятий см. (9). Если упор на практику, см. (2).

    (2) Воркшопы — практическое интерактивное занятие, направленное на освоение инструмента, подхода или навыка, длится от нескольких часов до 1–2 дней. Предполагает активное участие, работу в группах.
    Если это лекция без практики, см. (1). Для продолжительного обучения, см. (9).

    (3) Митапы — неформальная встреча небольшой группы (до 150 человек), посвящённая узкой теме. Проводится офлайн, с короткими выступлениями и обсуждением.
    Для масштабного события с секциями, см. (4). Если основной акцент на нетворкинг, см. (11).

    (4) Конференции — масштабная встреча (1–3 дня) с докладами, панелями, мастер-классами, выставками, ключевыми спикерами и параллельными сессиями.
    Если мероприятие стратегическое, высокого уровня, см. (5).

    (5) Форумы и саммиты — высокоуровневая встреча с обсуждением стратегических или отраслевых вопросов. Участвуют руководители, эксперты и представители госорганов.
    Для технических или образовательных форматов см. (4) или (9).

    (6) Хакатоны и чемпионаты — интенсивное соревнование команд (1–5 дней), включающее разработку прототипов и решений, менторство, жюри и призы.
    Если конкурс не связан с технологиями, см. (10).

    (7) Выставки и шоукейсы — демонстрация продуктов или решений в формате стендов и открытых демонстраций.
    Если акцент на сценических презентациях, см. (8).

    (8) Демо-дни и питч-сессии — публичные презентации проектов или стартапов перед инвесторами и экспертами. Обычно итог акселераторов или конкурсов.
    Для формата стендов без чёткого расписания см. (7).

    (9) Образовательные программы — структурированная учебная программа из серии занятий на несколько недель или месяцев, с сертификацией и развитием компетенций.
    Для однодневного формата см. (1) или (2).

    (10) Открытые конкурсы — открытый конкурс идей или решений без необходимости командной работы в реальном времени.
    Для интенсивной командной работы (например, хакатона) см. (6).

    (11) Нетворкинг-события и роадшоу — событие для развития профессиональных связей, включающее неформальное общение и форматы вроде speed networking.
    При наличии структурированных выступлений см. (3) или (4).

    (12) Клубы и сообщества — речь идёт о регулярном взаимодействии участников в долгосрочной перспективе, а не о разовом мероприятии.
    Для отдельного события от сообщества выбирайте его конкретный формат.

    Формат вывода:
    ТОЛЬКО ОДНА ЦИФРА (1-12) без каких-либо дополнительных слов или символов 
    """.strip()

    try:
        entries = json.loads(Path(json_path).read_text(encoding="utf-8"))
    except Exception as e:
        print(f"Не удалось открыть {json_path}: {e}", file=sys.stderr)
        return

    giga = GigaChat(
        credentials=GIGACHAT_API_KEY,
        ca_bundle_file=CA_BUNDLE,
        verify_ssl_certs=VERIFY_SSL,
    )

    results = []

    for obj in entries:
        title = html.unescape(obj.get("title", ""))
        description = html.unescape(obj.get("description", ""))
        location = html.unescape(obj.get("location", ""))
        start_date = html.unescape(obj.get("start_date", ""))
        end_date = html.unescape(obj.get("end_date", ""))
        tags = html.unescape(obj.get("tags", []))
        relevant = html.unescape(obj.get("relevant", ""))
        organizer = html.unescape(obj.get("organizer", []))
        event_type = html.unescape(obj.get("event_type", []))
        event_format = html.unescape(obj.get("event_format", []))
        url = html.unescape(obj.get("url", []))

        if event_type == "Не указано":
            if relevant != "1":
                results.append({
                    "title": title,
                    "organizer": organizer,
                    "description": description,
                    "location": location,
                    "start_date": start_date,
                    "end_date": end_date,
                    "tags": tags,
                    "relevant": relevant,
                    "event_format": event_format,
                    "url": url,
                    "event_type": "Не указано"
                })
                continue

            user_msg = f"tags: {tags}\ntitle: {title}\ndescription: {description}"

            print(user_msg)

            payload = Chat(
                messages=[
                    Messages(role=MessagesRole.SYSTEM, content=prompt_system_2),
                    Messages(role=MessagesRole.USER, content=user_msg),
                ],
                **model_params,
            )

            try:
                response = giga.chat(payload)
                chat_ans = response.choices[0].message.content.strip()
                print(chat_ans)
                print()

            except Exception as e:
                print(f"Ошибка запроса: {e}", file=sys.stderr)
                chat_ans = ""
                print(chat_ans)
                print()

            TOPIC_NAMES = {
                1: "Вебинар",
                2: "Воркшоп",
                3: "Митап",
                4: "Конференция",
                5: "Форум/Саммит",
                6: "Хакатон/Чемпионат",
                7: "Выставка/Шоукейс",
                8: "Демо-день/Питч-сессия",
                9: "Образовательная программа",
                10: "Открытый конкурс",
                11: "Нетворкинг-событие",
                12: "Клубное событие"
            }

            try:
                ev_type_name = TOPIC_NAMES.get(int(chat_ans), "")
            except ValueError:
                ev_type_name = ""

            results.append({
                "title": title,
                "organizer": organizer,
                "description": description,
                "location": location,
                "start_date": start_date,
                "end_date": end_date,
                "tags": tags,
                "relevant": relevant,
                "event_format": event_format,
                "url": url,
                "event_type": ev_type_name
            })
        else:
            results.append({
                "title": title,
                "organizer": organizer,
                "description": description,
                "location": location,
                "start_date": start_date,
                "end_date": end_date,
                "tags": tags,
                "relevant": relevant,
                "event_format": event_format,
                "url": url,
                "event_type": event_type
            })

    Path(json_path).write_text(
        json.dumps(results, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print(f"Обработано: {len(results)} шт.")
    print(f"Итог сохранён в {Path(json_path).resolve()}")


def gigachat_3(json_path):
    prompt_system_3 = """
    На вход ты получишь 5 параметров:
    - location (место проведения мероприятия)
    - event_type (тип мероприятия)
    - tags (тэг мероприятия)
    - title (заголовок мероприятия)
    - description (описание мероприятия)

    Формат — это способ, с помощью которого участники взаимодействуют с мероприятием: физически, удалённо или и так, и так.
    Выберите только одну тему из следующего списка:
    (1) Очно — участие предполагает физическое присутствие на площадке. В тексте могут быть указаны:
    конкретный адрес или место проведения (город, улица, конференц-зал, вуз и т.д.)
    слова вроде "офлайн", "вживую", "на месте", "в офисе", "очно", "приходите", "встречаемся"
    если указано "места ограничены" или "вход по спискам" без упоминания онлайн-доступа

    (2) Онлайн — мероприятие проводится полностью в интернете. Возможные признаки:
    указаны платформы: Zoom, Teams, YouTube, Webinar.ru и др.
    присутствуют фразы: "онлайн", "дистанционно", "трансляция", "вебинар", "ссылка будет выслана", "подключайтесь", "удалённо", "в прямом эфире"
    если указано, что все участники подключаются удалённо, даже если есть студия или офлайн-спикеры

    (3) Гибрид — участники могут выбрать между очным и онлайн-форматом. Это смешанный формат. Возможные признаки:
    ясно указано: "гибрид", "можно участвовать как очно, так и онлайн", "трансляция + очное участие"
    указано место и платформа одновременно, или описан выбор участия
    сочетание очных формулировок ("встречаемся в офисе") и онлайн-элементов ("ссылка на подключение", "трансляция", "участие через Zoom")

    Важно: 
    - Если location содержит адрес, но ничего не сказано про онлайн — это очный формат.
    - Если event_type или tags содержат «вебинар», «онлайн» и т.п. — учитывай как дополнительный сигнал.
    - Не путай гибрид с записью. Если указано, что будет запись, но участвовать можно только очно — это не гибрид.
    - Если есть противоречия, то опирайся на информацию из location и description

    Формат вывода:
    ТОЛЬКО ОДНА ЦИФРА (1-3) без каких-либо дополнительных слов или символов 
    """.strip()

    try:
        entries = json.loads(Path(json_path).read_text(encoding="utf-8"))
    except Exception as e:
        print(f"Не удалось открыть {json_path}: {e}", file=sys.stderr)
        return

    giga = GigaChat(
        credentials=GIGACHAT_API_KEY,
        ca_bundle_file=CA_BUNDLE,
        verify_ssl_certs=VERIFY_SSL,
    )

    results = []

    for obj in entries:
        title = html.unescape(obj.get("title", ""))
        description = html.unescape(obj.get("description", ""))
        location = html.unescape(obj.get("location", ""))
        start_date = html.unescape(obj.get("start_date", ""))
        end_date = html.unescape(obj.get("end_date", ""))
        tags = html.unescape(obj.get("tags", []))
        relevant = html.unescape(obj.get("relevant", ""))
        event_type = html.unescape(obj.get("event_type", ""))
        organizer = html.unescape(obj.get("organizer", []))
        event_format = html.unescape(obj.get("event_format", []))
        url = html.unescape(obj.get("url", []))

        if event_format == "Не указано":

            if relevant != "1":
                results.append({
                    "title": title,
                    "organizer": organizer,
                    "description": description,
                    "location": location,
                    "start_date": start_date,
                    "end_date": end_date,
                    "tags": tags,
                    "relevant": relevant,
                    "event_type": "Не указано",
                    "event_format": "Не указано",
                    "url": url,
                })
                continue

            user_msg = f"location: {location}\nev_type: {event_type}\ntags: {tags}\ntitle: {title}\ndescription: {description}"

            print(user_msg)

            payload = Chat(
                messages=[
                    Messages(role=MessagesRole.SYSTEM, content=prompt_system_3),
                    Messages(role=MessagesRole.USER, content=user_msg),
                ],
                **model_params,
            )

            try:
                response = giga.chat(payload)
                chat_ans = response.choices[0].message.content.strip()
                print(chat_ans)
                print()

            except Exception as e:
                print(f"Ошибка запроса: {e}", file=sys.stderr)
                chat_ans = ""
                print(chat_ans)
                print()

            FORMAT_NAMES = {
                1: "Очно",
                2: "Онлайн",
                3: "Гибрид"
            }

            try:
                ev_format_name = FORMAT_NAMES.get(int(chat_ans), "")
            except ValueError:
                ev_format_name = ""

            results.append({
                "title": title,
                "organizer": organizer,
                "description": description,
                "location": location,
                "start_date": start_date,
                "end_date": end_date,
                "tags": tags,
                "relevant": relevant,
                "event_type": event_type,
                "event_format": ev_format_name,
                "url": url,
            })
        else:
            results.append({
                "title": title,
                "organizer": organizer,
                "description": description,
                "location": location,
                "start_date": start_date,
                "end_date": end_date,
                "tags": tags,
                "relevant": relevant,
                "event_type": event_type,
                "event_format": event_format,
                "url": url,
            })

    Path(json_path).write_text(
        json.dumps(results, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print(f"Обработано: {len(results)} шт.")
    print(f"Итог сохранён в {Path(json_path).resolve()}")


def gigachat_4(json_path):
    prompt_system_4 = """
    На вход ты получишь 3 параметра:
    - location (место проведения мероприятия)
    - title (заголовок мероприятия)
    - description (описание мероприятия)

    Твоя задача: найти и вывести организатора мероприятия
    Как найти:
    - В тексте явно указано «Организатор мероприятия» или что-то похожее
    - Из описания понятно, кто именно организует мероприятие

    Не додумывай и не придумывай ничего нового, опирайся только на информацию, которая тебе отправляется
    Если организатор отсутствует, выводи цифру 0

    Формат вывода:
    Название организатора(без вводных слов и без «организатор...») или ТОЛЬКО ОДНУ цифру 0  
    """.strip()

    try:
        entries = json.loads(Path(json_path).read_text(encoding="utf-8"))
    except Exception as e:
        print(f"Не удалось открыть {json_path}: {e}", file=sys.stderr)
        return

    giga = GigaChat(
        credentials=GIGACHAT_API_KEY,
        ca_bundle_file=CA_BUNDLE,
        verify_ssl_certs=VERIFY_SSL,
    )

    results = []

    for obj in entries:
        title = html.unescape(obj.get("title", ""))
        description = html.unescape(obj.get("description", ""))
        location = html.unescape(obj.get("location", ""))
        start_date = html.unescape(obj.get("start_date", ""))
        end_date = html.unescape(obj.get("end_date", ""))
        tags = html.unescape(obj.get("tags", []))
        relevant = html.unescape(obj.get("relevant", ""))
        event_type = html.unescape(obj.get("event_type", ""))
        event_format = html.unescape(obj.get("event_format", ""))
        organizer = html.unescape(obj.get("organizer", []))
        url = html.unescape(obj.get("url", []))

        if organizer == "Не указано":
            if relevant != "1":
                results.append({
                    "title": title,
                    "organizer": "Не указано",
                    "description": description,
                    "location": location,
                    "start_date": start_date,
                    "end_date": end_date,
                    "tags": tags,
                    "relevant": relevant,
                    "event_type": "Не указано",
                    "event_format": "Не указано",
                    "url": url
                })
                continue

            user_msg = f"location: {location}\ntitle: {title}\ndescription: {description}"

            print(user_msg)

            payload = Chat(
                messages=[
                    Messages(role=MessagesRole.SYSTEM, content=prompt_system_4),
                    Messages(role=MessagesRole.USER, content=user_msg),
                ],
                **model_params,
            )

            try:
                response = giga.chat(payload)
                chat_ans = response.choices[0].message.content.strip()
                print(chat_ans)
                print()

            except Exception as e:
                print(f"Ошибка запроса: {e}", file=sys.stderr)
                chat_ans = ""
                print(chat_ans)
                print()

            organizer = "" if chat_ans == "0" else chat_ans

            results.append({
                "title": title,
                "organizer": organizer,
                "description": description,
                "location": location,
                "start_date": start_date,
                "end_date": end_date,
                "tags": tags,
                "relevant": relevant,
                "event_type": event_type,
                "event_format": event_format,
                "url": url
            })
        else:
            results.append({
                "title": title,
                "organizer": organizer,
                "description": description,
                "location": location,
                "start_date": start_date,
                "end_date": end_date,
                "tags": tags,
                "relevant": relevant,
                "event_type": event_type,
                "event_format": event_format,
                "url": url
            })

    Path(json_path).write_text(
        json.dumps(results, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print(f"Обработано: {len(results)} шт.")
    print(f"Итог сохранён в {Path(json_path).resolve()}")


def gigachat_5(json_path):
    prompt_system_5 = """
    На вход ты получишь 7 параметра:
    - title (заголовок мероприятия)
    - location (место проведения мероприятия)
    - start_date (дата начала мероприятия)
    - end_date (дата окончания мероприятия)
    - event_type (тип мероприятия)
    - event_format (формат мероприятия)
    - description (описание мероприятия)

    Твоя задача: сгенерировать одно связное саммари-событие в виде абзаца
    Требования к саммари:
    1. Формат — единый, связный абзац. Без заголовков, списков, форматирования или обращения к читателю.
    2. Объём — 1–4 предложения (от 150 до 500 символов).
    3. Тональность — нейтрально-дружелюбная, профессиональная, без рекламы или призывов в стиле «не пропустите».

    Обязательно включай в саммари:
    1. дату проведения мероприятия:
    -если start == end — используй только одну дату (например: 8 июня);
    -если start ≠ end — укажи диапазон дат в формате: с 10 по 12 июня;
    2. город из поля location (БЕЗ названия улицы и дома);
    3. формат события (например: очное, онлайн или гибрид);
    4. тип мероприятия (ev_type);
    5. целевую аудиторию (извлекай из description);
    6. ключевые темы, активности или особенности события (из description);
    7. пользу для участников (обобщённо: общение, обмен опытом, знания и т.п.).

    Ни в коем случае не включай в текст:
    1. точный title (перефразируй при необходимости);
    2. повторов или длинных фрагментов из description.

    Если какое-то поле отсутствует или пустое, просто не упоминай его, но сохраняй связность и логичность текста.

    Формат вывода:
    ТОЛЬКО саммари без дополнительной информации 
    """.strip()

    try:
        entries = json.loads(Path(json_path).read_text(encoding="utf-8"))
    except Exception as e:
        print(f"Не удалось открыть {json_path}: {e}", file=sys.stderr)
        return

    giga = GigaChat(
        credentials=GIGACHAT_API_KEY,
        ca_bundle_file=CA_BUNDLE,
        verify_ssl_certs=VERIFY_SSL,
    )

    results = []

    for obj in entries:
        title = html.unescape(obj.get("title", ""))
        description = html.unescape(obj.get("description", ""))
        location = html.unescape(obj.get("location", ""))
        start_date = html.unescape(obj.get("start_date", ""))
        end_date = html.unescape(obj.get("end_date", ""))
        tags = html.unescape(obj.get("tags", []))
        relevant = html.unescape(obj.get("relevant", ""))
        event_type = html.unescape(obj.get("event_type", ""))
        event_format = html.unescape(obj.get("event_format", ""))
        organizer = html.unescape(obj.get("organizer", ""))
        url = html.unescape(obj.get("url", []))

        if relevant != "1":
            results.append({
                "title": title,
                "description": description,
                "location": location,
                "start_date": start_date,
                "end_date": end_date,
                "tags": tags,
                "relevant": relevant,
                "event_type": "Не указано",
                "event_format": "Не указано",
                "organizer": "Не указано",
                "summary": "Не указано",
                "url": url
            })
            continue

        user_msg = f"title: {title}\nlocation: {location}\nstart: {start_date}\nend: {end_date}\nev_type: {event_type}\nev_format: {event_format}\ndescription: {description}"

        print(user_msg)

        payload = Chat(
            messages=[
                Messages(role=MessagesRole.SYSTEM, content=prompt_system_5),
                Messages(role=MessagesRole.USER, content=user_msg),
            ],
            **model_params,
        )

        try:
            response = giga.chat(payload)
            chat_ans = response.choices[0].message.content.strip()
            print(chat_ans)
            print()

        except Exception as e:
            print(f"Ошибка запроса: {e}", file=sys.stderr)
            chat_ans = ""
            print(chat_ans)
            print()

        results.append({
            "title": title,
            "description": description,
            "location": location,
            "start_date": start_date,
            "end_date": end_date,
            "tags": tags,
            "relevant": relevant,
            "event_type": event_type,
            "event_format": event_format,
            "organizer": organizer,
            "summary": chat_ans,
            "url": url
        })

    Path(json_path).write_text(
        json.dumps(results, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print(f"Обработано: {len(results)} шт.")
    print(f"Итог сохранён в {Path(json_path).resolve()}")


if __name__ == "__main__":
    clean()
    gigachat_1()
    deduplicate()
    gigachat_2()
    gigachat_3()
    gigachat_4()
    gigachat_5()
