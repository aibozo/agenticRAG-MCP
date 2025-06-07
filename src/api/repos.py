from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
import uuid
from pathlib import Path

from src.utils.logging import get_logger
from src.workers.indexing_worker import enqueue_indexing_job, get_job_status

router = APIRouter()
logger = get_logger(__name__)

class InitRepoRequest(BaseModel):
    path: str = Field(..., description="Absolute path to the repository")
    repo_name: str = Field(..., description="Name for the repository index")
    ignore_globs: Optional[List[str]] = Field(
        default=None, 
        description="Additional glob patterns to ignore"
    )

class InitRepoResponse(BaseModel):
    job_id: str
    status: str
    message: str
    manifest_path: Optional[str] = None

class JobStatusResponse(BaseModel):
    job_id: str
    status: str
    message: Optional[str] = None
    result: Optional[Dict[str, Any]] = None
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

@router.post("/repos/init", response_model=InitRepoResponse)
async def init_repo(
    request: InitRepoRequest,
    background_tasks: BackgroundTasks
) -> InitRepoResponse:
    """Initialize repository indexing."""
    job_id = str(uuid.uuid4())
    
    # Validate path
    repo_path = Path(request.path)
    if not repo_path.exists():
        raise HTTPException(status_code=400, detail=f"Path does not exist: {request.path}")
    if not repo_path.is_dir():
        raise HTTPException(status_code=400, detail=f"Path is not a directory: {request.path}")
    
    logger.info(
        "init_repo_requested",
        job_id=job_id,
        path=request.path,
        repo_name=request.repo_name
    )
    
    # Enqueue job
    await enqueue_indexing_job(
        job_id=job_id,
        path=request.path,
        repo_name=request.repo_name,
        ignore_globs=request.ignore_globs
    )
    
    return InitRepoResponse(
        job_id=job_id,
        status="queued",
        message=f"Repository indexing job {job_id} has been queued",
        manifest_path=None
    )

@router.get("/repos/jobs/{job_id}", response_model=JobStatusResponse)
async def get_job_status_endpoint(job_id: str) -> JobStatusResponse:
    """Get the status of an indexing job."""
    status = await get_job_status(job_id)
    
    if not status:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")
    
    return JobStatusResponse(
        job_id=job_id,
        status=status.get("status", "unknown"),
        message=status.get("message"),
        result=status.get("result"),
        created_at=status.get("created_at"),
        updated_at=status.get("updated_at")
    )