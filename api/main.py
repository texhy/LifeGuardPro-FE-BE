"""
LifeGuard-Pro Chatbot API
FastAPI Application Entry Point
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import logging
import os

from api.routes import chat, session, health, email, email_test
from api.middleware import LoggingMiddleware, RateLimitMiddleware
from config.settings import settings
from config.database import test_connection

# Setup logging
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(settings.LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("🚀 Starting LifeGuard-Pro API...")
    if not test_connection():
        logger.error("Database connection failed!")
        raise Exception("Database connection failed!")
    logger.info("✅ Database connected")
    
    yield
    
    # Shutdown
    logger.info("👋 Shutting down...")

# Initialize FastAPI
app = FastAPI(
    title="LifeGuard-Pro Chatbot API",
    description="AI-powered training assistant for lifeguard and CPR courses",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.ENVIRONMENT == "development" else None,
    redoc_url="/redoc" if settings.ENVIRONMENT == "development" else None,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Custom middleware
app.add_middleware(LoggingMiddleware)
app.add_middleware(RateLimitMiddleware, max_requests=100, window_seconds=60)

# Include routers
app.include_router(health.router, prefix="/api/v1", tags=["Health"])
app.include_router(session.router, prefix="/api/v1/session", tags=["Session"])
app.include_router(chat.router, prefix="/api/v1/chat", tags=["Chat"])
app.include_router(email.router, tags=["Email"])  # Root level for n8n integration
app.include_router(email_test.router, prefix="/api", tags=["Email Test"])  # Test endpoint for email classification

@app.get("/")
async def root():
    return {
        "service": "LifeGuard-Pro Chatbot API",
        "version": "1.0.0",
        "status": "operational",
        "docs": "/docs" if settings.ENVIRONMENT == "development" else "disabled"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "api.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.ENVIRONMENT == "development"
    )

