from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, List, Dict,Any, Union


class QueryRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Query for the chatbot")

class QueryResponse(BaseModel):
    status: str
    message: str
    data: Dict

class Source(BaseModel):
    id: Optional[str] = None
    name: Optional[str] = None


class NewsArticle(BaseModel):
    source: Optional[Source] = None
    author: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    url: Optional[str] = None
    urlToImage: Optional[str] = None
    publishedAt: Optional[str] = None
    content: Optional[str] = None

class ArticleResponse(BaseModel):
    status: str
    message: str
    data: Optional[Union[List[NewsArticle], Dict[str, Any]]] = None

