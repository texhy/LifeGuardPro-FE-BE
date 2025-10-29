"""Health Check Endpoints"""
from fastapi import APIRouter
from config.database import test_connection, get_database_stats

router = APIRouter()

@router.get("/health")
async def health_check():
    """Basic health check"""
    db_status = test_connection()
    return {
        "status": "healthy" if db_status else "unhealthy",
        "database": "connected" if db_status else "disconnected"
    }

@router.get("/health/detailed")
async def detailed_health():
    """Detailed health check with database stats"""
    db_stats = get_database_stats()
    return {
        "status": "healthy",
        "database": db_stats,
        "version": "1.0.0"
    }

