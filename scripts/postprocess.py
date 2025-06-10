# На всякий оставил принты лишние, чтобы можно было видеть,
# а что там вообще выводит ИИшка. Почти вс (или даже все)
# можно спокойно удалять

import os
import json, html, sys, re, emoji, sqlite3
import networkx as nx
from pathlib import Path
from fuzzywuzzy import fuzz
from datetime import datetime
from gigachat import GigaChat
from bs4 import BeautifulSoup
from collections import defaultdict
from gigachat.models import Chat, Messages, MessagesRole
from dotenv import load_dotenv

load_dotenv()

GIGACHAT_API_KEY = os.getenv('GIGACHAT_API_KEY')
CA_BUNDLE = None
VERIFY_SSL = False


def clean():
    input_path = "/data/events_structured.json"
    output_path = "/data/events_result.json"

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
        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
            return dt.strftime("%Y-%m-%d")
        except Exception:
            return date_str

    with open(input_path, 'r', encoding='utf-8') as infile:
        data = json.load(infile)

    cleaned = []
    for obj in data:
        obj["title"] = clean_text(obj.get("title", ""))
        obj["location"] = clean_text(obj.get("location", ""))
        obj["description"] = clean_text(obj.get("description", ""))
        obj["start_date"] = convert_date(obj.get("start_date", ""))
        obj["end_date"] = convert_date(obj.get("end_date", ""))

        cleaned.append(obj)

    with open(output_path, 'w', encoding='utf-8') as outfile:
        json.dump(cleaned, outfile, ensure_ascii=False, indent=4)


def gigachat_1():
    input_json = "ГигаЧад_Спарсили_Очистка.json"
    output_json = "ГигаЧад_1_Релевантность.json"

    prompt_system_1 = """
    На вход ты получишь 4 параметра:
    - location (место проведения мероприятия)
    - title (заголовок мероприятния)
    - description (описание мероприятия)

    Твоя задча: Определить релевантность мероприятия
    Мероприятне релевантно, если оно:
    - Отностися к сфере ИТ
    - Проходит ТОЛЬКО в Нижнем Новгороде ИЛИ в формате Онлайн
    Если релевантно, помечай цифрой 1. Если нет — 0

    Формат вывода:
    Только одна цифра (1 или 0), ничего больше 
    """.strip()

    model_params = {
        "model": "GigaChat",
        "temperature": 0.3,
        "top_p": 0.95,
        "max_tokens": 1024,
        "repetition_penalty": 1.05,
        "stream": False,
        "update_interval": 0
    }

    try:
        entries = json.loads(Path(input_json).read_text(encoding="utf-8"))
    except Exception as e:
        print(f"Не удалось открыть {input_json}: {e}", file=sys.stderr)
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

        try:
            start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
            today = datetime.today().date()
            if start_date < today:
                chat_ans = "0"
            else:
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
            "description": description,
            "location": location,
            "start_date": start_date,
            "end_date": end_date,
            "tags": tags,
            "relevant": chat_ans
        })

    Path(output_json).write_text(
        json.dumps(results, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print(f"Обработано: {len(results)} шт.")
    print(f"Итог сохранён в {Path(output_json).resolve()}")


def deduplicate():
    input_file = "ГигаЧад_1_Релевантность.json"
    output_file = "ГигаЧад_Без_Дублей.json"

    try:
        entries = json.loads(Path(input_file).read_text(encoding="utf-8"))
    except Exception as e:
        print(f"Ошибка чтения файла {input_file}: {e}")
        return

    fixed = []
    by_date = defaultdict(list)

    for idx, entry in enumerate(entries):
        if entry.get("relevant") == "0":
            fixed.append((idx, entry))
        else:
            by_date[entry.get("start_date", "")].append((idx, entry))

    def is_duplicate(e1, e2):
        name_sim = fuzz.token_set_ratio(e1['title'], e2['title'])
        loc_sim = fuzz.token_set_ratio(e1['location'], e2['location'])
        return name_sim >= 85 and loc_sim >= 85

    print("\nПоиск дублей...")

    for date, group in by_date.items():
        if len(group) <= 1:
            fixed.extend(group)
            continue

        G = nx.Graph()
        indices = [idx for idx, _ in group]

        for idx in range(len(group)):
            G.add_node(idx)

        for i in range(len(group)):
            for j in range(i + 1, len(group)):
                e1 = group[i][1]
                e2 = group[j][1]
                if is_duplicate(e1, e2):
                    G.add_edge(i, j)
                    print(f"\nДата: {date}")
                    print("Найдено похожее:")
                    print(f" → [{i}] {e1['title']} | {e1['location']}")
                    print(f" → [{j}] {e2['title']} | {e2['location']}")

        components = list(nx.connected_components(G))
        for component in components:
            if len(component) == 1:
                fixed.append(group[list(component)[0]])
                continue

            sorted_component = sorted(
                component,
                key=lambda idx: len(group[idx][1].get("description", "")),
                reverse=True
            )

            print(f"\nГруппа дублей (дата: {date}):")
            for idx_in_group in sorted_component:
                idx, event = group[idx_in_group]
                print(f" - {event['title']} ({len(event.get('description', ''))} символов)")

            for k, idx_in_group in enumerate(sorted_component):
                entry_idx, entry = group[idx_in_group]
                if k == 0:
                    print(f"Оставляем как оригинал: {entry['title']}")
                    fixed.append((entry_idx, entry))
                else:
                    entry["relevant"] = "0"
                    print(f"Помечаем как дубль: {entry['title']}")
                    fixed.append((entry_idx, entry))

    fixed_sorted = sorted(fixed, key=lambda x: x[0])
    cleaned_entries = [entry for _, entry in fixed_sorted]

    Path(output_file).write_text(
        json.dumps(cleaned_entries, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print(f"\nОбработка завершена. Событий: {len(cleaned_entries)}. Файл сохранён в: {output_file}")


def gigachat_2():
    input_json = "ГигаЧад_Без_Дублей.json"
    output_json = "ГигаЧад_2_Тип.json"

    prompt_system_2 = """
    На вход ты получишь 3 параметра:
    - tags (тэг мероприятия)
    - title (заголовок мероприятния)
    - description (описание мероприятия)

    Твоя задча: Классифицировать тему
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

    model_params = {
        "model": "GigaChat",
        "temperature": 0.3,
        "top_p": 0.95,
        "max_tokens": 1024,
        "repetition_penalty": 1.05,
        "stream": False,
        "update_interval": 0
    }

    try:
        entries = json.loads(Path(input_json).read_text(encoding="utf-8"))
    except Exception as e:
        print(f"Не удалось открыть {input_json}: {e}", file=sys.stderr)
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
        if relevant != "1":
            results.append({
                "title": title,
                "description": description,
                "location": location,
                "start_date": start_date,
                "end_date": end_date,
                "tags": tags,
                "relevant": relevant,
                "event_type": ""
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
            "description": description,
            "location": location,
            "start_date": start_date,
            "end_date": end_date,
            "tags": tags,
            "relevant": relevant,
            "ev_type": ev_type_name

        })

    Path(output_json).write_text(
        json.dumps(results, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print(f"Обработано: {len(results)} шт.")
    print(f"Итог сохранён в {Path(output_json).resolve()}")


def gigachat_3():
    input_json = "ГигаЧад_2_Тип.json"
    output_json = "ГигаЧад_3_Формат.json"

    prompt_system_3 = """
    На вход ты получишь 5 параметров:
    - location (место проведения мероприятия)
    - event_type (тип мероприятния)
    - tags (тэг мероприятия)
    - title (заголовок мероприятния)
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

    model_params = {
        "model": "GigaChat",
        "temperature": 0.3,
        "top_p": 0.95,
        "max_tokens": 1024,
        "repetition_penalty": 1.05,
        "stream": False,
        "update_interval": 0
    }

    try:
        entries = json.loads(Path(input_json).read_text(encoding="utf-8"))
    except Exception as e:
        print(f"Не удалось открыть {input_json}: {e}", file=sys.stderr)
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

        if relevant != "1":
            results.append({
                "title": title,
                "description": description,
                "location": location,
                "start_date": start_date,
                "end_date": end_date,
                "tags": tags,
                "relevant": relevant,
                "event_type": "",
                "event_format": ""
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
            "description": description,
            "location": location,
            "start_date": start_date,
            "end_date": end_date,
            "tags": tags,
            "relevant": relevant,
            "event_type": event_type,
            "event_format": ev_format_name
        })

    Path(output_json).write_text(
        json.dumps(results, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print(f"Обработано: {len(results)} шт.")
    print(f"Итог сохранён в {Path(output_json).resolve()}")


def gigachat_4():
    input_json = "ГигаЧад_3_Формат.json"
    output_json = "ГигаЧад_4_Организатор.json"

    prompt_system_4 = """
    На вход ты получишь 3 параметра:
    - location (место проведения мероприятия)
    - title (заголовок мероприятния)
    - description (описание мероприятия)

    Твоя задача: найти и вывести Организатора мероприятия
    Как найти:
    - В тексте явно указано «Организатор мероприятия» или что-то похожее
    - Из описания понятно, кто именно организует мероприятие

    Не додумывай и не придумывай ничего нового, опирайся только на информацию, которая тебе отправляется
    Если организатор отсутствует, выводи цифру 0

    Формат вывода:
    Организатор мероприятия полностью (только название организатора, без воодных слов и без «организатор...») или ТОЛЬКО ОДНУ цифру 0  
    """.strip()

    model_params = {
        "model": "GigaChat",
        "temperature": 0.3,
        "top_p": 0.95,
        "max_tokens": 1024,
        "repetition_penalty": 1.05,
        "stream": False,
        "update_interval": 0
    }

    try:
        entries = json.loads(Path(input_json).read_text(encoding="utf-8"))
    except Exception as e:
        print(f"Не удалось открыть {input_json}: {e}", file=sys.stderr)
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

        if relevant != "1":
            results.append({
                "title": title,
                "description": description,
                "location": location,
                "start_date": start_date,
                "end_date": end_date,
                "tags": tags,
                "relevant": relevant,
                "event_type": "",
                "event_format": "",
                "organizer": ""

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
            "description": description,
            "location": location,
            "start_date": start_date,
            "end_date": end_date,
            "tags": tags,
            "relevant": relevant,
            "event_type": event_type,
            "event_format": event_format,
            "organizer": organizer
        })

    Path(output_json).write_text(
        json.dumps(results, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print(f"Обработано: {len(results)} шт.")
    print(f"Итог сохранён в {Path(output_json).resolve()}")


def gigachat_5():
    input_json = "ГигаЧад_4_Организатор.json"
    output_json = "ГигаЧад_5_Саммари.json"

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
    ТОЛЬКО саммари без дополнительной инфомрации 
    """.strip()

    model_params = {
        "model": "GigaChat",
        "temperature": 0.3,
        "top_p": 0.95,
        "max_tokens": 1024,
        "repetition_penalty": 1.05,
        "stream": False,
        "update_interval": 0
    }

    try:
        entries = json.loads(Path(input_json).read_text(encoding="utf-8"))
    except Exception as e:
        print(f"Не удалось открыть {input_json}: {e}", file=sys.stderr)
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

        if relevant != "1":
            results.append({
                "title": title,
                "description": description,
                "location": location,
                "start_date": start_date,
                "end_date": end_date,
                "tags": tags,
                "relevant": relevant,
                "event_type": "",
                "event_format": "",
                "organizer": "",
                "summary": ""
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
            "summary": chat_ans
        })

    Path(output_json).write_text(
        json.dumps(results, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    print(f"Обработано: {len(results)} шт.")
    print(f"Итог сохранён в {Path(output_json).resolve()}")


def json_to_sqlite():
    json_path = "ГигаЧад_5_Саммари.json"
    db_path = "ГигаЧад_Финал.db"

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        description TEXT,
        location TEXT,
        start_date TEXT,
        end_date TEXT,
        relevant INTEGER,
        event_type TEXT,
        event_format TEXT,
        organizer TEXT,
        summary TEXT
    )
    """)

    cursor.execute("DELETE FROM events")

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    for event in data:
        cursor.execute("""
            INSERT INTO events (title, description, location, start_date, end_date, relevant, event_type, event_format, organizer, summary)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            event.get("title"),
            event.get("description"),
            event.get("location"),
            event.get("start_date"),
            event.get("end_date"),
            int(event.get("relevant", 0)),
            event.get("event_type"),
            event.get("event_format"),
            event.get("event_organizer"),
            event.get("summary")
        ))

    conn.commit()
    conn.close()

    print(f"Загружено {len(data)} событий в базу {db_path}.")


if __name__ == "__main__":
    clean()
    gigachat_1()
    deduplicate()
    gigachat_2()
    gigachat_3()
    gigachat_4()
    gigachat_5()
    json_to_sqlite()
