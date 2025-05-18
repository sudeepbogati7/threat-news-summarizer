from fastapi import FastAPI
from src.api.routers import api_router
from src.database.db import Base, engine
from fastapi.middleware.cors import CORSMiddleware


origins = [
    "http://localhost",
    "http://localhost:3000",  # Example: React/Vue frontend
    "https://yourdomain.com",  # Your production domain
    "*"  # Allows all origins (use cautiously, for development only)
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