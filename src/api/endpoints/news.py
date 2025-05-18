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
from dateutil.parser import parse as parse_date
from datetime import datetime

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

# Initialize limiter
# limiter = Limiter(key_func=get_remote_address)

router = APIRouter()

@router.post("/fetch-articles", response_model=ArticleResponse)
async def fetch_articles(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """
    Upload a JSON file with news articles and process them for RAG.
    Stores article metadata in the database.
    """
    try:
        if not file.filename.endswith(".json"):
            logger.warning("Invalid file format uploaded for articles")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only JSON files are supported")

        logger.info(f"Processing uploaded file: {file.filename}")
        content = await file.read()
        articles = json.loads(content)
        logger.info(f"Parsed {len(articles)} articles from uploaded file")

        # Validate and store articles in database
        for article in articles:
            existing_article = db.query(Article).filter(Article.url == article.get("url")).first()
            if not existing_article:
                # Parse published_at string to datetime
                published_at_str = article.get("published_at")
                published_at = None
                if published_at_str:
                    try:
                        published_at = parse_date(published_at_str)
                        if not isinstance(published_at, datetime):
                            logger.warning(f"Invalid published_at format for article {article.get('url')}: {published_at_str}")
                            published_at = None
                    except (ValueError, TypeError) as e:
                        logger.warning(f"Failed to parse published_at for article {article.get('url')}: {str(e)}")
                        published_at = None

                db_article = Article(
                    title=article.get("title"),
                    description=article.get("description"),
                    content=article.get("content"),
                    source_name=article.get("source", {}).get("name"),
                    author=article.get("author"),
                    url=article.get("url"),
                    published_at=published_at
                )
                db.add(db_article)
        db.commit()
        logger.info("Articles stored in database")

        # Save to file for RAG processing
        os.makedirs("data", exist_ok=True)
        # Use absolute path for Windows compatibility
        base_dir = os.path.abspath(os.path.dirname(__file__))
        file_path = os.path.join(base_dir, "..", "..", "..", "data", "articles.json")
        file_path = os.path.normpath(file_path)
        logger.info(f"Saving articles to {file_path}")
        with open(file_path, "w") as f:
            json.dump(articles, f)

        # Process articles for RAG
        process_articles(file_path)
        logger.info(f"Successfully fetched and processed {len(articles)} articles")
        return {
            "status": "success",
            "message": "Articles fetched and processed successfully",
            "data": {"article_count": len(articles)}
        }

    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON format in uploaded file: {str(e)}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid JSON format")
    except Exception as e:
        logger.error(f"Unexpected error during article fetching: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to process articles: {str(e)}")

@router.post("/chat", response_model=QueryResponse)
# @limiter.limit("5/minute")
async def chat(request: QueryRequest, user=Depends(get_current_user)):
    """
    Query news articles via chatbot for authenticated users.
    Returns summarized or relevant information. Limited to 5 requests per minute.
    """
    try:
        qa_chain = get_qa_chain()
        if qa_chain is None:
            logger.warning(f"Chat query attempted with no articles loaded by user {user.email}")
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No articles loaded. Please fetch articles first.")

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

    except HTTPException:
        raise  # Propagate HTTP exceptions (e.g., 400 for no articles)
    except Exception as e:
        logger.error(f"Unexpected error during chat query for user {user.email}: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to process query: {str(e)}")