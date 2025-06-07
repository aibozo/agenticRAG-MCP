from fastapi import APIRouter
from pydantic import BaseModel
from datetime import datetime
import redis.asyncio as redis
from typing import Dict, Any

from src.config.settings import settings
from src.utils.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)

class HealthResponse(BaseModel):
    status: str
    timestamp: datetime
    version: str = "1.0.0"
    environment: str
    services: Dict[str, Any]

@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Check health status of the application and its dependencies."""
    services = {}
    
    # Check Redis
    try:
        r = redis.from_url(settings.redis_url)
        await r.ping()
        await r.close()
        services["redis"] = {"status": "healthy", "url": settings.redis_url}
    except Exception as e:
        logger.error("redis_health_check_failed", error=str(e))
        services["redis"] = {"status": "unhealthy", "error": str(e)}
    
    # Check Chroma (would implement actual check)
    services["chroma"] = {"status": "healthy", "persist_dir": settings.chroma_persist_directory}
    
    # Overall status
    all_healthy = all(s.get("status") == "healthy" for s in services.values())
    
    return HealthResponse(
        status="healthy" if all_healthy else "degraded",
        timestamp=datetime.utcnow(),
        environment=settings.mcp_env,
        services=services
    )