import httpx
import json
import os
import logging
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from src.services.rag import load_and_process_articles

# Set up logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

@retry(
    stop=stop_after_attempt(3),  # Retry up to 3 times
    wait=wait_exponential(multiplier=1, min=2, max=10),  # Exponential backoff: 2s, 4s, 8s
    retry=retry_if_exception_type((httpx.ReadTimeout, httpx.ConnectTimeout)),  # Retry on timeout errors
    before_sleep=lambda retry_state: logger.warning(
        f"Retrying fetch_articles_from_endpoint (attempt {retry_state.attempt_number}) due to {retry_state.outcome.exception()}"
    )
)
async def fetch_articles_from_endpoint():
    """
    Fetch news articles from the NewsAPI endpoint and save them to a file.
    """
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:  # Set timeout to 30 seconds
            response = await client.get(
                "https://newsapi.org/v2/everything",
                params={
                    "q": "data leak",
                    "sortBy": "publishedAt",
                    "apiKey": "e45179448f144edcb12a75674c74e6bf"
                }
            )
            response.raise_for_status()  # Raise an exception for non-2xx status codes
            data = response.json()

            if data.get("status") != "ok":
                logger.error(f"NewsAPI returned non-ok status: {data.get('status')}")
                raise Exception(f"NewsAPI returned non-ok status: {data.get('status')}")

            articles = data.get("articles", [])
            if not articles:
                logger.warning("No articles found in the response")

            # Save articles to file
            os.makedirs("data", exist_ok=True)
            with open("data/articles.json", "w") as f:
                json.dump(articles, f)
            
            # Process the saved articles
            load_and_process_articles("data/articles.json")
            logger.info(f"Successfully fetched and processed {len(articles)} articles")
            return articles

    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error occurred: {str(e)}, status code: {e.response.status_code}")
        raise Exception(f"Failed to fetch articles: HTTP {e.response.status_code}")
    except httpx.RequestError as e:
        logger.error(f"Request error occurred: {str(e)}")
        raise Exception(f"Failed to fetch articles: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error occurred: {str(e)}")
        raise Exception(f"Failed to fetch articles: {str(e)}")

def process_articles(file_path: str = "data/articles.json"):
    """
    Process articles from a specified file.
    """
    try:
        if not os.path.exists(file_path):
            logger.error(f"File not found: {file_path}")
            raise FileNotFoundError(f"File not found: {file_path}")
        
        load_and_process_articles(file_path)
        logger.info(f"Articles processed from file: {file_path}")
    
    except FileNotFoundError as e:
        logger.error(f"Failed to process articles: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Failed to process articles: {str(e)}")
        raise