from it_events_crawler.utils import extract_metadata, select_relevant_paragraphs, chunk_paragraphs

EVENT_PROMPT_TEMPLATE = """
    Ты — эксперт по извлечению структурированной информации из текста. 
    Твоя задача — проанализировать предоставленный текст страницы, на которой описывается ИТ-мероприятие, и выделить из него следующие сведения:

    Название ИТ-мероприятия. Название, под которым мероприятие указано на странице, без дополнительных пояснений или слоганов. Указывай с заглавной буквы.
    Организатор.
    Дата начала и дата окончания мероприятия в формате DD.MM.YYYY.
    - Игнорируй даты, рядом с которыми указано "опубликовано", "updated", "published", "дата публикации", "обновлено", "новости", "новость", "релиз", "обзор" и другим похожим контекстом.
    - Выбирай только даты, в тексте рядом с которыми явно упоминается, что это дата начала или окончания мероприятия, либо стоят глаголы "пройдёт", "состоится", "стартует", "начнётся", "закончится", "завершится" и другие формы этих глаголов, или типы событий ("конференция", "форум", "митап" и т.д.).
    - Если год рядом с датой не указан, ориентируйся на ближайший явно указанный год в тексте. Если и это невозможно — укажи текущий год.
    - Если после этих правил нельзя уверенно выбрать даты — заполни оба поля значением "Не указано".
    - Дата окончания не может быть раньше даты начала.
    - Если дата окончания не указана явно, то запиши её такой же, как дата начала.
    Тип мероприятия. Укажи тип, к которому относится мероприятие, возможные варианты: "Вебинар", "Воркшоп", "Митап", "Конференция", "Форум/Саммит", "Хакатон/Чемпионат", "Выставка/Шоукейс", "Демо-день/Питч-сессия", "Образовательная программа", "Открытый конкурс", "Нетворкинг-событие", "Клубное событие". 
    Если тип явно не указан, но можно вывести однозначное заключение из контекста — выбери из списка; иначе "Не указано";
    Формат мероприятия. Укажи, как проводится мероприятие. Варианты: очный, онлайн или гибридный. Очный формат означает, что единственный вариант проведение мероприятия - очно(может быть указан какой-то адрес).
    Онлайн формат означает, что единственный вариант проведение мероприятия - онлайн.
    Гибридный формат подразумевает, что мероприятие проводится и очно и онлайн(может быть указан адрес, а также упомянута возможность подключится онлайн). 
    Информацию о формате можно получить или из описания или она будет указана явно.
    Адрес мероприятия. Укажи адрес по которому будет проходить данное мероприятие. Обычно должно быть указано явно или в описании, или в отдельном модуле. 
    Указывай только те компоненты адреса, которые есть на странице, не надо что-либо додумывать. Если, например, есть только улица и дом, то указывай только их. Если есть другие компоненты, то указывай всё что есть. Формат: г. Название_города, ул. Название_улицы, д. Номер_дома.
    Описание мероприятия. Найди указанное на странице описание того, что из себя представляет мероприятия. Если на странице есть достаточно полное описание мероприятия, то ничего не обрабатывай и оставь его.
    Может включать в себя все предыдущие пункты. Если явного описания нет, то на основе всех предыдущих пунктов нужно саммаризовать информацию. Это поле не надо оставлять пустым.

    Инструкции:
    Прочитай весь предоставленный текст.
    Идентифицируй и выдели ключевые фрагменты, содержащие название мероприятия, данные об организаторе, дата или период проведения, тип и формат мероприятия.
    Если какая-то информация отсутствует или её невозможно уверенно определить из предоставленного текста, укажи вместо неё значение «Не указано».
    Не додумывай и не используй информацию, не упомянутую в тексте явно.
    Если информация разбросана по тексту или представлена в виде описания, собери её и представь в требуемой форме.
    При извлечении дат и предпочтительно указывай информацию максимально точно так, как она приведена в исходном тексте и в соответствии с указанным шаблоном.
    Если тип мероприятия не указан явно, постарайся подобрать максимально подходящий вариант из предложенных выше на основе остального контекста.
    Убедись, что итоговый ответ структурирован и соответствует заданному формату.

    Ответ должен быть представлен исключительно в следующем формате (каждое поле начинается с новой строки, каждое значение поля указано в двойных кавычках):
    Название ИТ-мероприятия: "..."
    Организатор: "..."
    Дата начала: "..."
    Дата окончания: "..."
    Тип мероприятия: "..."
    Формат проведения: "..."
    Адрес мероприятия: "..."
    Описание мероприятия: "..."
      
    Пример:

    Входной текст:
    "В ближайшую субботу, 12 июля 2025 года, в конференц-центре 'TechHub', расположенном по адресу улица Московская, д. 91, пройдет ежегодная IT-конференция 'Innovate 2025'. Мероприятие организовано компанией 'TechEvents'. На конференции запланировано выступление ведущих специалистов в области технологий."

    Вывод модели:
    Название ИТ-мероприятия: "Innovate 2025"
    Организатор: "TechEvents"
    Дата начала: "12.07.2025"
    Дата окончания: "12.07.2025"
    Тип мероприятия: "Конференция"
    Формат проведения: "Очный"
    Адрес мероприятия: "ул. Московская, д. 91"
    Описание мероприятия: "В ближайшую суббот пройдёт IT-конференция 'Innovate 2025', на которой пройдут выступления ведущих специалистов в области IT-технологий."
    
    ---  
    Теперь текст страницы:
    Title: {title}  
    Description: {description}  

    {body}
    """


def build_event_prompt(clean_text: str, url: str) -> str:
    # Извлекаем мета
    meta = {"title": "Не указано", "description": "Не указано"}
    # Извлекаем основной чистый текст
    main = clean_text
    # Отбираем нужные абзацы
    keywords = ['дата', 'организатор', 'пройдет', 'проходит', 'мероприятие']
    paras = select_relevant_paragraphs(main, keywords, max_paras=15)
    # Склеиваем в не слишком длинный чанк
    body_snippet = chunk_paragraphs(paras, max_length=12000)

    return EVENT_PROMPT_TEMPLATE.format(
        title=meta['title'] or 'Не указано',
        description=meta['description'] or 'Не указано',
        body=body_snippet
    )
