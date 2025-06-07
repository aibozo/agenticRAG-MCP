from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

from src.utils.logging import get_logger
from src.storage.vector_store import VectorStore
from src.agents.workflow import AgenticRAG

router = APIRouter()
logger = get_logger(__name__)

# Create a single instance of AgenticRAG
_agentic_rag = None

def get_agentic_rag() -> AgenticRAG:
    """Get or create the AgenticRAG instance."""
    global _agentic_rag
    if _agentic_rag is None:
        vector_store = VectorStore()
        _agentic_rag = AgenticRAG(vector_store)
    return _agentic_rag

class QueryRequest(BaseModel):
    question: str = Field(..., description="Natural language question about the codebase")
    repo_name: str = Field(..., description="Name of the indexed repository")
    max_iterations: int = Field(default=3, description="Maximum retrieval iterations")
    include_sources: bool = Field(default=True, description="Include source file references")

class ChunkReference(BaseModel):
    file_path: str
    start_line: int
    end_line: int
    relevance_score: float

class QueryResponse(BaseModel):
    answer: str
    sources: Optional[List[ChunkReference]] = None
    tokens_used: Dict[str, int]
    processing_time_ms: int
    iterations: int

@router.post("/queries", response_model=QueryResponse)
async def query_repo(
    request: QueryRequest,
    agentic_rag: AgenticRAG = Depends(get_agentic_rag)
) -> QueryResponse:
    """Query an indexed repository using agentic RAG."""
    start_time = datetime.utcnow()
    
    logger.info(
        "query_requested",
        repo_name=request.repo_name,
        question_length=len(request.question),
        max_iterations=request.max_iterations
    )
    
    try:
        # Execute agentic RAG query
        result = await agentic_rag.query(
            question=request.question,
            repo_name=request.repo_name,
            max_iterations=request.max_iterations
        )
        
        # Extract sources if requested
        sources = None
        if request.include_sources and result.get("chunks"):
            sources = []
            for chunk in result["chunks"][:5]:  # Top 5 sources
                # Parse lines from format "123-456"
                lines = chunk["lines"].split("-")
                sources.append(ChunkReference(
                    file_path=chunk["file"],
                    start_line=int(lines[0]),
                    end_line=int(lines[1]) if len(lines) > 1 else int(lines[0]),
                    relevance_score=0.9  # We don't have actual scores from the workflow
                ))
        
        processing_time = int((datetime.utcnow() - start_time).total_seconds() * 1000)
        
        # Extract token usage
        metadata = result.get("metadata", {})
        tokens_used = {
            "retrieval": int(metadata.get("tokens_used", 0) * 0.8),  # Estimate split
            "compression": int(metadata.get("tokens_used", 0) * 0.2),
            "total": metadata.get("tokens_used", 0)
        }
        
        return QueryResponse(
            answer=result["answer"] or "No relevant information found.",
            sources=sources,
            tokens_used=tokens_used,
            processing_time_ms=processing_time,
            iterations=metadata.get("iterations", 1)
        )
        
    except Exception as e:
        logger.error("query_failed", error=str(e), repo=request.repo_name)
        raise HTTPException(
            status_code=500,
            detail=f"Query failed: {str(e)}"
        )

class CostStatsResponse(BaseModel):
    period_start: datetime
    period_end: datetime
    total_cost_usd: float
    breakdown: Dict[str, Dict[str, Any]]
    daily_budget_remaining: float

@router.get("/costs", response_model=CostStatsResponse)
async def get_cost_stats() -> CostStatsResponse:
    """Get token usage and cost statistics for the last 24 hours."""
    now = datetime.utcnow()
    
    # TODO: Implement actual cost tracking
    # For now, return placeholder response
    
    return CostStatsResponse(
        period_start=now.replace(hour=0, minute=0, second=0, microsecond=0),
        period_end=now,
        total_cost_usd=12.34,
        breakdown={
            "gpt-4o": {
                "tokens": 150000,
                "cost_usd": 10.50
            },
            "gpt-4o-mini": {
                "tokens": 500000,
                "cost_usd": 1.50
            },
            "text-embedding-3-large": {
                "tokens": 1000000,
                "cost_usd": 0.34
            }
        },
        daily_budget_remaining=87.66
    )