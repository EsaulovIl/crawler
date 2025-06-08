from flask import Blueprint, render_template, jsonify, request
from sqlalchemy import func
from .models import Event
from . import db

# Создаём Blueprint, чтобы потом его зарегистрировать в app.py
bp = Blueprint('main', __name__)


def apply_filters(query):
    """
    Накладывает на SQLAlchemy Query общие условия фильтрации из request.args.
    """
    sd = request.args.get('start_date')
    ed = request.args.get('end_date')
    if sd:
        query = query.filter(Event.start_date >= sd)
    if ed:
        query = query.filter(Event.end_date <= ed)

    org = request.args.get('organizer')
    if org:
        query = query.filter(Event.organizer == org)

    et = request.args.get('event_type')
    if et:
        query = query.filter(Event.event_type == et)

    return query


# Маршрут для домашней страницы(дашборда)
@bp.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')


# Общее количество мероприятий
@bp.route('/api/events_summary')
def events_summary():
    q = db.session.query(func.count(Event.id))
    q = apply_filters(q)
    total = q.scalar() or 0
    return jsonify({'total': total})


# Временной ряд по дням
@bp.route('/api/events_over_time')
def events_over_time():
    # Получаем из запроса явные параметры
    sd = request.args.get('start_date', type=str)
    ed = request.args.get('end_date', type=str)

    # Если один из них не задан — подгружаем диапазон из БД
    if not sd or not ed:
        min_max = db.session.query(
            func.min(Event.start_date),
            func.max(Event.end_date)
        ).one()
        min_date, max_date = min_max
        if not sd and min_date:
            sd = min_date.isoformat()
        if not ed and max_date:
            ed = max_date.isoformat()

    # группируем по дате начала
    q = db.session.query(
        func.to_char(Event.start_date, 'YYYY-MM-DD').label('period'),
        func.count(Event.id).label('count')
    ).filter(Event.start_date >= sd
             ).filter(Event.end_date <= ed)

    q = apply_filters(q)
    q = q.group_by('period').order_by('period')
    data = [{'period': r.period, 'count': r.count} for r in q.all()]
    return jsonify(data)


# API-маршрут, возвращающий JSON с количеством мероприятий по типам
@bp.route('/api/events_by_type')
def events_by_type():
    """
    Возвращает JSON-список, где каждая запись имеет формат {'event_type': ..., 'count': ...}
    """
    q = db.session.query(
        Event.event_type.label('event_type'),
        db.func.count(Event.id).label('count')
    )
    q = apply_filters(q)
    results = q.group_by(Event.event_type).all()
    data = [{'event_type': r.event_type, 'count': r.count} for r in results]
    return jsonify(data)


# API-маршрут, возвращающий JSON с количеством мероприятий по форматам
@bp.route('/api/events_by_format')
def events_by_format():
    q = db.session.query(
        Event.event_format.label('format'),
        func.count(Event.id).label('count')
    )
    q = apply_filters(q)
    q = q.group_by(Event.event_format)
    data = [{'format': r.format, 'count': r.count} for r in q.all()]
    return jsonify(data)


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
