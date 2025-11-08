from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, DateTime, Date, Text
from . import db

import datetime


class Event(db.Model):
    __tablename__ = 'events'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    organizer = db.Column(db.String(255), nullable=False, default="Не указано")
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    event_type = db.Column(db.String(255), nullable=False, default="Не указано")
    event_format = db.Column(db.String(255), nullable=False, default="Не указано")
    location = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=False)
    url = db.Column(db.String(1024), unique=True, nullable=False)
    relevant = db.Column(db.Integer, nullable=False)
    summary = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.datetime.utcnow)
