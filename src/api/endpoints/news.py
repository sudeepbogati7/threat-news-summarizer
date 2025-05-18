from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile
from sqlalchemy.orm import Session
from src.database.db import get_db
from src.schemas.news import ArticleResponse, QueryRequest, QueryResponse
from src.core.security import get_current_user
from src.services.rag import query_rag, get_qa_chain
from src.services.news_fetcher import process_articles
from src.models.news import Article
from slowapi import Limiter
from slowapi.util import get_remote_address
import os
import json
import logging
from src.utils.exceptions import DatabaseError

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

# Initialize limiter
limiter = Limiter(key_func=get_remote_address)

router = APIRouter()

@router.post("/fetch-articles", response_model=ArticleResponse)
async def fetch_articles(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """
    Upload a JSON file with news articles and process them for RAG.
    Stores article metadata in
     the database.
    
    
    """
    try:
        if not file.filename.endswith(".json"):
            logger.warning("Invalid file format uploaded for articles")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only JSON files are supported")

        content = await file.read()
        articles = json.loads(content)

        # Validate and store articles in database
        for article in articles:
            existing_article = db.query(Article).filter(Article.url == article.get("url")).first()
            if not existing_article:
                db_article = Article(
                    title=article.get("title"),
                    description=article.get("description"),
                    content=article.get("content"),
                    source_name=article.get("source", {}).get("name"),
                    author=article.get("author"),
                    url=article.get("url"),
                    published_at=article.get("publishedAt")
                )
                db.add(db_article)
        db.commit()

        # Save to file for RAG processing
        os.makedirs("data", exist_ok=True)
        with open("data/articles.json", "w") as f:
            json.dump(articles, f)

        # Process articles for RAG
        process_articles()
        logger.info(f"Successfully fetched and processed {len(articles)} articles")
        return {
            "status": "success",
            "message": "Articles fetched and processed successfully",
            "data": {"article_count": len(articles)}
        }

    except json.JSONDecodeError:
        logger.error("Invalid JSON format in uploaded file")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON format")
    except Exception as e:
        logger.error(f"Unexpected error during article fetching: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to process articles")

@router.post("/chat", response_model=QueryResponse)
@limiter.limit("5/minute")
async def chat(request: QueryRequest, user=Depends(get_current_user)):
    """
    Query news articles via chatbot for authenticated users.
    Returns summarized or relevant information. Limited to 5 requests per minute.
    """
    try:
        qa_chain = get_qa_chain()
        if qa_chain is None:
            logger.warning("Chat query attempted with no articles loaded")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No articles loaded")

        result = query_rag(qa_chain, request.query)
        logger.info(f"Chat query processed for user {user.email}: {request.query}")
        return {
            "status": "success",
            "message": "Query processed successfully",
            "data": {
                "answer": result["answer"],
                "sources": result["sources"]
            }
        }

    except Exception as e:
        logger.error(f"Unexpected error during chat query: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to process query")