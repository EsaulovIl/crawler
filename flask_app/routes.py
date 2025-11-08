from flask import Blueprint, render_template, jsonify, request, make_response
import logging
import csv, io
from sqlalchemy import func, extract, desc
from datetime import date
from .models import Event
from concurrent.futures import ThreadPoolExecutor
from crawler.crawl_pipeline import run_spiders_subprocess
from . import db

# Создаём Blueprint, чтобы потом его зарегистрировать в app.py
bp = Blueprint('main', __name__)

_executor = ThreadPoolExecutor(max_workers=1)

SPIDERS = ["it52", "alleventsit", "itc2go"]

pipe_logger = logging.getLogger("pipeline")


def _log_future(fut):
    exc = fut.exception()
    if exc:
        pipe_logger.exception("Background pipeline failed", exc_info=exc)
    else:
        pipe_logger.info("Pipeline finished OK")


@bp.post("/api/refresh")
def api_refresh():
    """
    Стартует полный пайплайн в фоне.
    Отдаёт 202 — «принято».
    """
    _executor.submit(run_spiders_subprocess).add_done_callback(_log_future)
    return jsonify({"status": "started"}), 202


@bp.route("/api/download_csv")
def download_csv():
    """
    Отдаёт CSV-файл со всеми колонками таблицы events.
    При наличии query-параметров применяются те же
    фильтры, что и для остальных API (reuse apply_filters).
    """
    # формируем запрос
    query = apply_filters(db.session.query(Event))  # :contentReference[oaicite:0]{index=0}

    # собираем CSV в память (можно заменить генератором для стриминга)
    sio = io.StringIO()
    writer = csv.writer(sio, delimiter=';', quoting=csv.QUOTE_MINIMAL)

    columns = (
        "id", "title", "organizer",
        "start_date", "end_date",
        "event_type", "event_format",
        "location", "description",
        "url", "relevant", "summary",
        "created_at",
    )
    writer.writerow(columns)

    for ev in query.order_by(Event.id).all():
        writer.writerow([getattr(ev, c) for c in columns])

    # отдаём как attachment
    resp = make_response(sio.getvalue())
    resp.headers["Content-Disposition"] = "attachment; filename=events.csv"
    resp.headers["Content-Type"] = "text/csv; charset=utf-8-sig"  # BOM для Excel
    return resp


def apply_filters(query):
    """
    Накладывает на SQLAlchemy Query общие условия фильтрации из request.args.
    """
    if request.args.get('show_all') not in ('1', 'true', 'yes'):
        query = query.filter(Event.relevant == 1)

    sd = request.args.get('start_date')
    ed = request.args.get('end_date')
    if sd:
        query = query.filter(Event.start_date >= sd)
    if ed:
        query = query.filter(Event.end_date <= ed)

    orgs = request.args.getlist('organizer[]')
    if not orgs:
        csv = request.args.get('organizer', '')
        orgs = [s.strip() for s in csv.split(',') if s.strip()]
    if orgs:
        query = query.filter(Event.organizer.in_(orgs))

    etypes = request.args.getlist('event_type[]')
    if not etypes:
        csv = request.args.get('event_type', '')
        etypes = [s.strip() for s in csv.split(',') if s.strip()]
    if etypes:
        query = query.filter(Event.event_type.in_(etypes))

    formats = request.args.getlist('format[]') or \
              request.args.get('format', '').split(',')
    formats = [f.strip() for f in formats if f.strip()]
    if formats:
        query = query.filter(Event.event_format.in_(formats))

    return query


# Маршрут для домашней дашборда
@bp.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')


@bp.route("/api/summary")
def api_summary():
    today = date.today()
    total = db.session.query(Event).count()
    planned = db.session.query(Event).filter(Event.start_date >= today).count()
    finished = db.session.query(Event).filter(Event.end_date < today).count()
    return jsonify({
        "total": total,
        "planned": planned,
        "finished": finished,
        "today": today.strftime("%d %B")
    })


# Временной ряд по дням
@bp.route("/api/trend_by_type")
def api_trend_by_type():
    q = db.session.query(
        Event.event_type.label("event_type"),
        extract('year', Event.start_date).label("year"),
        func.count().label("cnt")
    )
    q = apply_filters(q)
    q = q.group_by("event_type", "year")
    q = q.order_by("event_type", "year")

    return jsonify([
        {"event_type": r.event_type, "year": int(r.year), "count": r.cnt}
        for r in q.all()
    ])


@bp.route("/api/top_event_types_radar")
def top_event_types_radar():
    limit = 5
    base_q = apply_filters(db.session.query(Event))

    # Считаем суммарно по типам мероприятий
    subq = (base_q.with_entities(Event.event_type,
                                 func.count().label("cnt"))
            .group_by(Event.event_type)
            .order_by(desc("cnt"))
            .limit(limit)
            .subquery())

    top_types = [r.event_type for r in db.session.query(subq.c.event_type)]

    # Разбивка по годам
    year_col = func.extract('year', Event.start_date)
    rows = (base_q.with_entities(year_col.label('year'),
                                 Event.event_type,
                                 func.count().label('cnt'))
            .filter(Event.event_type.in_(top_types))
            .group_by('year', Event.event_type)
            .order_by('year')
            .all())

    return jsonify([{"year": int(y), "event_type": t, "count": c}
                    for y, t, c in rows])


@bp.route("/api/events_by_organizer")
def api_events_by_organizer():
    query = db.session.query(
        Event.organizer.label("organizer"),
        func.count().label("count")
    )
    query = apply_filters(query)
    query = query.group_by(Event.organizer).order_by(func.count().desc())
    result = [{"organizer": r.organizer, "count": r.count} for r in query.all()]
    return jsonify(result)


# API-маршрут, возвращающий JSON с количеством мероприятий по форматам
@bp.route("/api/events_by_type_format")
def events_by_type_format():
    """
    Кол-во событий в разрезе тип - формат
    с учётом всех фильтров из request.args.
    """
    q = db.session.query(
        Event.event_type,
        Event.event_format,
        func.count().label("cnt")
    )

    q = apply_filters(q)
    q = q.group_by(Event.event_type, Event.event_format)

    rows = q.all()
    return jsonify([{
        "event_type": et,
        "event_format": ef,
        "count": c
    } for et, ef, c in rows])


@bp.route("/api/events_by_format")
def api_events_by_format():
    q = db.session.query(
        Event.event_format.label("event_format"),
        func.count().label("count")
    )

    q = apply_filters(q)
    q = q.group_by(Event.event_format) \
        .order_by(func.count().desc())

    return jsonify([{
        "event_format": r.event_format,
        "count": r.count
    } for r in q.all()])


@bp.route("/api/yearly_totals")
def api_yearly_totals():
    q = db.session.query(
        func.extract('year', Event.start_date).label("year"),
        func.count().label("cnt")
    )
    q = q.group_by("year").order_by("year")
    return jsonify([{"year": int(y), "cnt": c} for y, c in q.all()])


@bp.route("/api/top_type_current_year")
def api_top_type_current():
    import datetime
    this_year = datetime.date.today().year

    sub = (db.session.query(Event.event_type,
                            func.count().label("cnt"))
           .filter(func.extract('year', Event.start_date) == this_year)
           .group_by(Event.event_type)
           .order_by(desc("cnt"))
           .limit(1)
           .first())
    if not sub:
        return jsonify({"type": None, "series": []})

    top_type = sub.event_type

    earliest = db.session.query(func.min(Event.start_date)).scalar()
    begin_year = earliest.year if earliest else date.today().year
    rows = (db.session.query(
        func.extract('year', Event.start_date).label("year"),
        func.count().label("cnt"))
            .filter(Event.event_type == top_type,
                    func.extract('year', Event.start_date) >= begin_year)
            .group_by("year")
            .all())
    data = {int(y): c for y, c in rows}
    series = [data.get(y, 0) for y in range(begin_year, this_year + 1)]

    return jsonify({
        "type": top_type,
        "begin_year": begin_year,
        "series": series
    })


@bp.route("/api/events_by_event_type")
def api_events_by_event_type():
    q = (db.session
         .query(Event.event_type.label("event_type"),
                func.count().label("count")))
    q = apply_filters(q)
    q = q.group_by(Event.event_type).order_by(func.count().desc())

    return jsonify([{"event_type": t, "count": c} for t, c in q.all()])


@bp.route("/api/event_types_by_year")
def api_event_types_by_year():
    """
    Вернёт количество событий каждого типа по годам.
    """
    q = (db.session
         .query(func.extract('year', Event.start_date).label('year'),
                Event.event_type,
                func.count().label('cnt')))

    q = apply_filters(q)
    q = q.group_by('year', Event.event_type)
    q = q.order_by('year')

    rows = q.all()
    return jsonify([{
        "year": int(y),
        "event_type": et,
        "count": c
    } for y, et, c in rows])


# Список организаторов
@bp.route('/api/organizers')
def list_organizers():
    orgs = db.session.query(Event.organizer).distinct().order_by(Event.organizer).all()
    return jsonify([o.organizer for o in orgs])


# Список типов мероприятий
@bp.route('/api/event_types')
def list_event_types():
    types = db.session.query(Event.event_type).distinct().order_by(Event.event_type).all()
    return jsonify([t.event_type for t in types])


# Список форматов мероприятий
@bp.route("/api/formats")
def api_formats():
    res = db.session.query(Event.event_format.distinct()).all()
    return jsonify([r[0] for r in res])
