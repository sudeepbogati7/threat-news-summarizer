from fastapi import FastAPI
from services.news_fetcher import fetch_articles_from_endpoint
from src.api.routers import api_router
from src.database.db import Base, engine
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import logging
from apscheduler.triggers.cron import CronTrigger


# Scheduler setup
scheduler = AsyncIOScheduler(timezone="Asia/Kathmandu")

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

origins = [
    "http://localhost",
    "http://localhost:3000",
    "https://yourdomain.com",
    "*" 
]

app = FastAPI(title="News Article Summarizer API")

# Add CORSMiddleware to the application
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # List of allowed origins
    allow_credentials=True,  # Allow cookies and credentials
    allow_methods=["*"],  # Allow all HTTP methods (GET, POST, etc.)
    allow_headers=["*"],  # Allow all headers
)
# Create database tables
Base.metadata.create_all(bind=engine)

# Include API routers
app.include_router(api_router, prefix="/v1")


@app.on_event("startup")
async def startup_event():
    try:
        logger.info("Starting scheduler for daily news update")
        # Schedule fetch_articles_from_endpoint to run daily at 2:00 AM Nepal Time
        scheduler.add_job(
            fetch_articles_from_endpoint,
            trigger=CronTrigger(hour=2, minute=0, timezone="Asia/Kathmandu"),
            args=[None],  # Pass None for file; fetch_articles_from_endpoint will handle data source
            id="daily_news_update",
            replace_existing=True
        )
        scheduler.start()
        logger.info("Scheduler started successfully")
    except Exception as e:
        logger.error(f"Failed to start scheduler: {str(e)}")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down scheduler")
    scheduler.shutdown()

@app.get("/")
async def root():
    return {"message": "Welcome to the News Article Summarizer API"}