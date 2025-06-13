from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, DateTime, Date, Text
import datetime

Base = declarative_base()


class Event(Base):
    __tablename__ = 'events'
    id = Column(Integer, primary_key=True)
    title = Column(String(255), nullable=False)
    organizer = Column(String(255), nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    event_type = Column(String(255), nullable=False)
    event_format = Column(String(255), nullable=False)
    #location = Column(String(255), nullable=False)
    #description = Column(Text, nullable=False)
    url = Column(String(1024), unique=True, nullable=False)
    #relevant = Column(Integer, nullable=False)
    #summary = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
