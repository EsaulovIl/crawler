# crawler/crawl_pipeline.py
import argparse
import json
import logging
import os
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path
from typing import List, Dict

# ── Post-processing helpers
from crawler.it_events_crawler.postprocess import (
    clean,
    gigachat_1,
    deduplicate,
    gigachat_2,
    gigachat_3,
    gigachat_4,
    gigachat_5,
)

# ── Flask / SQLAlchemy
from flask_app.app import create_app
from flask_app.models import Event
from flask_app import db

JSON_PATH = Path("crawler/data/events.json")
SPIDER_FEED_TMPL = Path("crawler/data/{name}_items.json")

BASE_DIR = Path(__file__).resolve().parent
# имена Scrapy-пауков (их атрибут name)
SPIDER_NAMES = [
    "it52",
    "alleventsit",
    "itc2go",
    "events",
]

logger = logging.getLogger("pipeline")


def _merge_spider_feeds(spiders: list[str]) -> Path:
    """Считывает data/<spider>_items.json каждого паука и
       пишет объединённый список в JSON_PATH.

       Возвращает путь к итоговому файлу (JSON_PATH)."""
    merged: list[dict] = []
    for name in spiders:
        feed = SPIDER_FEED_TMPL.with_name(f"{name}_items.json")
        if not feed.exists():
            logger.warning("Файл %s не найден — паук %s, возможно, упал", feed, name)
            continue
        merged.extend(json.loads(feed.read_text(encoding="utf-8")))
    JSON_PATH.write_text(
        json.dumps(merged, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    logger.info("[PIPELINE] Объединили %s объектов из %s файлов",
                len(merged), len(spiders))
    return JSON_PATH


def run_spiders_subprocess(spiders: List[str] | None = None) -> None:
    """
    Запускает каждый Scrapy-паук в отдельном подпроцессе:
        $ python -m scrapy crawl <spider>

    Функция **блокирующая** — вызывайте её в Thread/ProcessPool, если
    нужно не держать Flask.
    """
    spiders = spiders or SPIDER_NAMES

    env = os.environ.copy()
    env["SCRAPY_SETTINGS_MODULE"] = "it_events_crawler.settings"

    for name in spiders:
        logger.info("➡  run spider %s", name)
        subprocess.run(
            [sys.executable, "-m", "scrapy", "crawl", name],
            cwd=BASE_DIR,  # запускаемся из каталога, где лежит пакет и data/
            env=env,  # передаём переменную окружения
            check=True,
            stdout=sys.stdout,
            stderr=sys.stderr,
        )

    merged_file = _merge_spider_feeds(spiders)

    _run_postprocess_and_save(merged_file)


# Пост-обработка LLM / очистка
def _run_postprocess_and_save(json_path: Path) -> None:
    run_postprocess(json_path)
    save_to_db(json_path)


def run_postprocess(json_path: Path) -> None:
    clean(json_path)
    gigachat_1(json_path)
    deduplicate(json_path)
    gigachat_2(json_path)
    gigachat_3(json_path)
    gigachat_4(json_path)
    gigachat_5(json_path)


def _clean(val: str | None) -> str | None:
    """Пустые строки и «Не указано» превращаем в None."""
    if not val:
        return None
    val = val.strip()
    return None if val in ("", "Не указано") else val


def _safe_int(v, default=0):
    try:
        return int(v)
    except (TypeError, ValueError):
        return default


def save_to_db(json_path: Path) -> None:
    events = json.loads(json_path.read_text(encoding="utf-8"))
    app = create_app()
    with app.app_context(), db.session.no_autoflush:  # ← блокируем ранний flush
        for ev in events:
            row = db.session.query(Event).filter_by(url=ev["url"]).first()
            if not row:
                row = Event(url=ev["url"])

            # обязательные поля всегда заполняем безопасным значением
            row.title = _clean(ev.get("title")) or "Без названия"
            row.organizer = _clean(ev.get("organizer")) or "Не указано"
            row.start_date = date.fromisoformat(ev["start_date"])
            row.end_date = date.fromisoformat(ev["end_date"])

            # остальные — если есть что записать
            for fld in ("event_type", "event_format", "location",
                        "description", "summary"):
                val = _clean(ev.get(fld))
                if val:
                    setattr(row, fld, val)

            row.relevant = _safe_int(ev.get("relevant", 0))

            db.session.add(row)

        db.session.commit()


def main() -> None:
    """
    Позволяет запускать файл напрямую:

        $ python -m crawler.crawl_pipeline               # краулинг + БД
        $ python -m crawler.crawl_pipeline --file ready.json
        $ python -m crawler.crawl_pipeline --spiders it52
    """
    parser = argparse.ArgumentParser(
        "Full crawl → LLM → DB pipeline (subprocess edition)"
    )
    parser.add_argument(
        "--file",
        help="готовый JSON вместо автоматического краулинга",
    )
    parser.add_argument(
        "--spiders",
        nargs="+",
        help="список пауков (по умолчанию все из SPIDER_NAMES)",
    )
    args = parser.parse_args()

    if args.file:
        shutil.copy(args.file, JSON_PATH)
        _run_postprocess_and_save(JSON_PATH)
    else:
        run_spiders_subprocess(args.spiders)


if __name__ == "__main__":
    main()
