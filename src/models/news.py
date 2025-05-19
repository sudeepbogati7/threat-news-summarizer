from sqlalchemy import Column, Integer, String, DateTime, Text
from src.database.db import Base
from datetime import datetime
from sqlalchemy.ext.declarative import declarative_base


Base = declarative_base()
class Article(Base):
    __tablename__ = "articles"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    content = Column(Text, nullable=True)
    source_name = Column(String, nullable=True)
    author = Column(String, nullable=True)
    url = Column(String, unique=True, nullable=False)
    published_at = Column(DateTime, nullable=True)