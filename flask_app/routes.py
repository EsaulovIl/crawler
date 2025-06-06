from flask import Blueprint, render_template, jsonify
from .models import Event
from . import db

# Создаём Blueprint, чтобы потом его зарегистрировать в app.py
bp = Blueprint('main', __name__)

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
    results = db.session.query(
        Event.event_type, db.func.count(Event.id).label('cnt')
    ).group_by(Event.event_type).all()
    data = [{'event_type': r.event_type, 'count': r.cnt} for r in results]
    return jsonify(data)