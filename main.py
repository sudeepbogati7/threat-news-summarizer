from fastapi import FastAPI
from src.api.routers import api_router
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from src.services.news_fetcher import fetch_articles_from_endpoint
import logging
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="News Article Summarizer API")

# Set up logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Include API routers
app.include_router(api_router, prefix="/v1")

# Scheduler setup
scheduler = AsyncIOScheduler(timezone="Asia/Kathmandu")

origins = [
    "http://localhost",
    "http://localhost:3000",
    "https://yourdomain.com",
    "*"
]

# Add CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    try:
        logger.info("Starting scheduler for daily news update")
        scheduler.add_job(
            func=fetch_articles_from_endpoint,
            trigger=CronTrigger(hour=23, minute=41, timezone="Asia/Kathmandu"),
            id="daily_news_update",
            replace_existing=True,
            misfire_grace_time=60  # Allow 60 seconds for missed jobs
        )
        scheduler.start()
        logger.info("Scheduler started successfully")
    except Exception as e:
        logger.error(f"Failed to start scheduler: {str(e)}")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Shutting down scheduler")
    if scheduler.running:
        scheduler.shutdown()
        logger.info("Scheduler shut down successfully")

@app.get("/")
async def root():
    return {"message": "Welcome to the News Article Summarizer API"}