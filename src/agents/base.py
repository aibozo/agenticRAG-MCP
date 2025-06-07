"""Base classes for agentic RAG system."""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime
import openai
from src.config.settings import settings
from src.utils.logging import get_logger

logger = get_logger(__name__)


class AgentResponse(BaseModel):
    """Standard response format for all agents."""
    
    content: Any = Field(..., description="Main response content")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    tokens_used: int = Field(0, description="Total tokens used in this response")
    cost_usd: float = Field(0.0, description="Estimated cost in USD")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    
    
class AgentState(BaseModel):
    """Shared state for agent workflows."""
    
    query: str = Field(..., description="Original user query")
    repo_name: str = Field(..., description="Repository to search")
    max_iterations: int = Field(5, description="Maximum search iterations")
    current_iteration: int = Field(0, description="Current iteration count")
    search_history: List[Dict[str, Any]] = Field(default_factory=list)
    retrieved_chunks: List[Dict[str, Any]] = Field(default_factory=list)
    total_tokens: int = Field(0, description="Total tokens used so far")
    total_cost: float = Field(0.0, description="Total cost so far")
    sufficient_context: bool = Field(False, description="Whether we have enough context")
    final_answer: Optional[str] = Field(None, description="Final compressed answer")


class Agent(ABC):
    """Base class for all agents."""
    
    def __init__(self, model: str = None):
        self.model = model or settings.retrieval_model
        self.client = openai.AsyncClient(api_key=settings.openai_api_key)
        # Map model names if needed (GPT-4.1 is now available directly)
        self.model_mapping = {
            # No mapping needed - GPT-4.1, gpt-4.1-mini are available
        }
        
    @abstractmethod
    async def run(self, state: AgentState) -> AgentResponse:
        """Execute the agent's main logic."""
        pass
        
    async def _call_llm(self, 
                       messages: List[Dict[str, str]], 
                       tools: Optional[List[Dict]] = None,
                       temperature: float = 0.0) -> Dict[str, Any]:
        """Make an LLM API call with cost tracking."""
        try:
            # Use mapped model name if available
            model_name = self.model_mapping.get(self.model, self.model)
            
            kwargs = {
                "model": model_name,
                "messages": messages,
                "temperature": temperature,
            }
            
            if tools:
                kwargs["tools"] = tools
                kwargs["tool_choice"] = "auto"
                
            response = await self.client.chat.completions.create(**kwargs)
            
            # Calculate costs
            tokens_used = response.usage.total_tokens
            cost = self._calculate_cost(tokens_used)
            
            logger.info("llm_call_complete", 
                       model=self.model,
                       tokens=tokens_used,
                       cost=cost)
            
            return {
                "response": response,
                "tokens": tokens_used,
                "cost": cost
            }
            
        except Exception as e:
            logger.error("llm_call_failed", error=str(e), model=self.model)
            raise
            
    def _calculate_cost(self, tokens: int) -> float:
        """Calculate cost based on model and token count."""
        # Pricing as of 2025 (adjust as needed)
        pricing = {
            "gpt-4.1": {"input": 15.00, "output": 60.00},  # per 1M tokens (estimated)
            "gpt-4.1-mini": {"input": 0.30, "output": 1.20},  # per 1M tokens (estimated)
            "gpt-4o": {"input": 2.50, "output": 10.00},  # per 1M tokens
            "gpt-4o-mini": {"input": 0.15, "output": 0.60},
            "gpt-4-turbo": {"input": 10.00, "output": 30.00},
            "gpt-3.5-turbo": {"input": 0.50, "output": 1.50},
        }
        
        model_key = self.model
        if model_key not in pricing:
            model_key = "gpt-4o"  # default
            
        # Rough estimate: assume 80% input, 20% output
        input_tokens = int(tokens * 0.8)
        output_tokens = int(tokens * 0.2)
        
        cost = (
            (input_tokens * pricing[model_key]["input"] / 1_000_000) +
            (output_tokens * pricing[model_key]["output"] / 1_000_000)
        )
        
        return round(cost, 6)