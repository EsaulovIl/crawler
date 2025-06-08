from flask import Blueprint, render_template, jsonify, request
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


# API-маршрут, возвращающий JSON
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


@bp.route('/api/organizers')
def list_organizers():
    orgs = db.session.query(Event.organizer).distinct().order_by(Event.organizer).all()
    return jsonify([o.organizer for o in orgs])


@bp.route('/api/event_types')
def list_event_types():
    types = db.session.query(Event.event_type).distinct().order_by(Event.event_type).all()
    return jsonify([t.event_type for t in types])
