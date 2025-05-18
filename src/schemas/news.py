from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, List, Dict

class ArticleResponse(BaseModel):
    status: str
    message: str
    data: Dict

class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Query for the chatbot")

class QueryResponse(BaseModel):
    status: str
    message: str
    data: Dict