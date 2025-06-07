from fastapi import FastAPI, HTTPException, Depends, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn

from src.config.settings import settings
from src.utils.logging import get_logger
from src.api import health, repos, queries

logger = get_logger(__name__)

# Security
security = HTTPBearer()

def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)) -> str:
    """Verify API token."""
    if credentials.credentials != settings.api_key:
        raise HTTPException(status_code=403, detail="Invalid authentication credentials")
    return credentials.credentials

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info("starting_application", 
                host=settings.mcp_host, 
                port=settings.mcp_port,
                environment=settings.mcp_env)
    
    # Startup tasks would go here (e.g., initialize connections)
    
    yield
    
    # Shutdown tasks would go here (e.g., close connections)
    logger.info("shutting_down_application")

# Create FastAPI app
app = FastAPI(
    title="AgenticRAG MCP Server",
    description="Intelligent codebase processing with agentic RAG",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, tags=["health"])
app.include_router(repos.router, prefix="/api/v1", tags=["repos"], dependencies=[Depends(verify_token)])
app.include_router(queries.router, prefix="/api/v1", tags=["queries"], dependencies=[Depends(verify_token)])

if __name__ == "__main__":
    uvicorn.run(
        "src.main:app",
        host=settings.mcp_host,
        port=settings.mcp_port,
        reload=settings.is_development,
        log_level=settings.mcp_log_level.lower()
    )