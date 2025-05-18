from sqlalchemy import Column, Integer, String, DateTime
from src.database.db import Base
from datetime import datetime

class Article(Base):
    __tablename__ = "articles"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(String)
    content = Column(String)
    source_name = Column(String)
    author = Column(String)
    url = Column(String, unique=True)
    published_at = Column(DateTime, default=datetime.utcnow)