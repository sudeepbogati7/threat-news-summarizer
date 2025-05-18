from fastapi import FastAPI
# from src.api.v1.routers import api_router
# from src.database.db import Base, engine

app = FastAPI(title="News Article Summarizer API")

# Create database tables
# Base.metadata.create_all(bind=engine)

# Include API routers
# app.include_router(api_router, prefix="/v1")