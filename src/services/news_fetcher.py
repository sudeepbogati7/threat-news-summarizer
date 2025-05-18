from src.services.rag import load_and_process_articles
import httpx
import json
import os
import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

async def fetch_articles_from_endpoint():
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("https://newsapi.org/v2/everything?q=data leak&sortBy=publishedAt&apiKey=e45179448f144edcb12a75674c74e6bf")  # Replace with your endpoint
            response.raise_for_status()
            articles = response.json()
            os.makedirs("data", exist_ok=True)
            with open("data/articles.json", "w") as f:
                json.dump(articles.articles, f)
            load_and_process_articles()
            logger.info("Articles fetched from endpoint and processed successfully")
    except httpx.HTTPError as e:
        logger.error(f"Failed to fetch articles from endpoint: {str(e)}")
        raise Exception(f"Failed to fetch articles: {str(e)}")

def process_articles(file_path: str = "data/articles.json"):
    try:
        load_and_process_articles(file_path)
        logger.info(f"Articles processed from file: {file_path}")
    except Exception as e:
        logger.error(f"Failed to process articles: {str(e)}")
        raise