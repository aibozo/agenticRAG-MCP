import asyncio
import json
import redis.asyncio as redis
from typing import Optional, Dict, Any, List
from datetime import datetime

from src.config.settings import settings
from src.utils.logging import get_logger
from src.indexing.indexer import init_repo

logger = get_logger(__name__)


class IndexingWorker:
    """Worker that processes repository indexing jobs from Redis queue."""
    
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self.running = False
        self.job_queue = "agenticrag:indexing:queue"
        self.job_status_prefix = "agenticrag:indexing:status:"
        self.job_result_prefix = "agenticrag:indexing:result:"
    
    async def connect(self):
        """Connect to Redis."""
        self.redis_client = redis.from_url(
            settings.redis_url,
            max_connections=settings.redis_max_connections,
            decode_responses=True
        )
        await self.redis_client.ping()
        logger.info("worker_connected_to_redis")
    
    async def disconnect(self):
        """Disconnect from Redis."""
        if self.redis_client:
            await self.redis_client.close()
    
    async def update_job_status(
        self,
        job_id: str,
        status: str,
        message: Optional[str] = None,
        result: Optional[Dict[str, Any]] = None
    ):
        """Update job status in Redis."""
        status_data = {
            "status": status,
            "updated_at": datetime.utcnow().isoformat(),
            "message": message
        }
        
        if result:
            status_data["result"] = result
        
        # Store status
        await self.redis_client.setex(
            f"{self.job_status_prefix}{job_id}",
            86400,  # 24 hour TTL
            json.dumps(status_data)
        )
        
        # Store result separately if provided
        if result:
            await self.redis_client.setex(
                f"{self.job_result_prefix}{job_id}",
                86400,  # 24 hour TTL
                json.dumps(result)
            )
    
    async def process_job(self, job_data: Dict[str, Any]):
        """Process a single indexing job."""
        job_id = job_data["job_id"]
        
        try:
            logger.info(
                "processing_indexing_job",
                job_id=job_id,
                repo_name=job_data["repo_name"]
            )
            
            # Update status to processing
            await self.update_job_status(
                job_id,
                "processing",
                "Indexing repository..."
            )
            
            # Run the indexing
            manifest_path = await init_repo(
                path=job_data["path"],
                repo_name=job_data["repo_name"],
                ignore_globs=job_data.get("ignore_globs")
            )
            
            # Update status to completed
            await self.update_job_status(
                job_id,
                "completed",
                "Repository indexed successfully",
                result={
                    "manifest_path": manifest_path,
                    "completed_at": datetime.utcnow().isoformat()
                }
            )
            
            logger.info(
                "indexing_job_completed",
                job_id=job_id,
                manifest_path=manifest_path
            )
            
        except Exception as e:
            logger.error(
                "indexing_job_failed",
                job_id=job_id,
                error=str(e)
            )
            
            # Update status to failed
            await self.update_job_status(
                job_id,
                "failed",
                f"Indexing failed: {str(e)}"
            )
    
    async def run(self):
        """Main worker loop."""
        await self.connect()
        self.running = True
        
        logger.info("indexing_worker_started")
        
        try:
            while self.running:
                try:
                    # Block waiting for job with timeout
                    job_data = await self.redis_client.blpop(
                        self.job_queue,
                        timeout=5
                    )
                    
                    if job_data:
                        _, job_json = job_data
                        job = json.loads(job_json)
                        await self.process_job(job)
                    
                except asyncio.CancelledError:
                    break
                except Exception as e:
                    logger.error("worker_error", error=str(e))
                    await asyncio.sleep(5)  # Back off on error
                    
        finally:
            await self.disconnect()
            logger.info("indexing_worker_stopped")
    
    def stop(self):
        """Stop the worker."""
        self.running = False


async def enqueue_indexing_job(
    job_id: str,
    path: str,
    repo_name: str,
    ignore_globs: Optional[List[str]] = None
) -> None:
    """Enqueue an indexing job to Redis."""
    redis_client = redis.from_url(settings.redis_url, decode_responses=True)
    
    try:
        job_data = {
            "job_id": job_id,
            "path": path,
            "repo_name": repo_name,
            "ignore_globs": ignore_globs,
            "created_at": datetime.utcnow().isoformat()
        }
        
        # Add to queue
        await redis_client.rpush(
            "agenticrag:indexing:queue",
            json.dumps(job_data)
        )
        
        # Set initial status
        await redis_client.setex(
            f"agenticrag:indexing:status:{job_id}",
            86400,  # 24 hour TTL
            json.dumps({
                "status": "queued",
                "created_at": datetime.utcnow().isoformat(),
                "message": "Job queued for processing"
            })
        )
        
        logger.info("job_enqueued", job_id=job_id, repo_name=repo_name)
        
    finally:
        await redis_client.close()


async def get_job_status(job_id: str) -> Optional[Dict[str, Any]]:
    """Get job status from Redis."""
    redis_client = redis.from_url(settings.redis_url, decode_responses=True)
    
    try:
        status_json = await redis_client.get(f"agenticrag:indexing:status:{job_id}")
        if status_json:
            return json.loads(status_json)
        return None
    finally:
        await redis_client.close()


if __name__ == "__main__":
    # Run worker when module is executed directly
    worker = IndexingWorker()
    try:
        asyncio.run(worker.run())
    except KeyboardInterrupt:
        worker.stop()