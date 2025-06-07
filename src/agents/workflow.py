"""LangGraph workflow for orchestrating agentic RAG."""

from typing import Dict, Any, Optional
from langgraph.graph import StateGraph, END
from src.agents.base import AgentState
from src.agents.retriever import RetrieverAgent  
from src.agents.compressor import CompressorAgent
from src.storage.vector_store import VectorStore
from src.utils.logging import get_logger
from src.config.settings import settings

logger = get_logger(__name__)


def should_continue_retrieval(state: Dict[str, Any]) -> str:
    """Decide whether to continue retrieval or move to compression."""
    
    # Stop conditions:
    # 1. We have sufficient context
    # 2. We've hit max iterations
    # 3. We've exceeded token budget
    
    if state.get("sufficient_context", False):
        logger.info("retrieval_complete", reason="sufficient_context", 
                   iterations=state.get("current_iteration", 0))
        return "compress"
        
    if state.get("current_iteration", 0) >= state.get("max_iterations", 5):
        logger.info("retrieval_complete", reason="max_iterations", 
                   iterations=state.get("current_iteration", 0))
        return "compress"
        
    if state.get("total_tokens", 0) > settings.max_tokens_retrieval:
        logger.info("retrieval_complete", reason="token_limit", 
                   tokens=state.get("total_tokens", 0))
        return "compress"
        
    # Continue retrieval
    return "retrieve"


def retrieve_node(state: Dict[str, Any], retriever: RetrieverAgent) -> Dict[str, Any]:
    """Execute retrieval agent."""
    # Convert dict to AgentState
    agent_state = AgentState(**state)
    logger.info("retrieve_node_start", iteration=agent_state.current_iteration)
    
    # Run async function in sync context
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        response = loop.run_until_complete(retriever.run(agent_state))
    finally:
        loop.close()
    
    # Return state updates as dict
    return agent_state.dict()


def compress_node(state: Dict[str, Any], compressor: CompressorAgent) -> Dict[str, Any]:
    """Execute compression agent."""
    # Convert dict to AgentState
    agent_state = AgentState(**state)
    logger.info("compress_node_start", chunks_count=len(agent_state.retrieved_chunks))
    
    # Run async function in sync context
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        response = loop.run_until_complete(compressor.run(agent_state))
    finally:
        loop.close()
    
    # Return state updates as dict
    return agent_state.dict()


def create_rag_workflow(vector_store: VectorStore, 
                       retrieval_model: Optional[str] = None,
                       compression_model: Optional[str] = None) -> StateGraph:
    """Create the agentic RAG workflow using LangGraph."""
    
    # Initialize agents
    retriever = RetrieverAgent(vector_store, model=retrieval_model)
    compressor = CompressorAgent(model=compression_model)
    
    # Create workflow using dict state
    from typing import TypedDict
    
    workflow = StateGraph(dict)
    
    # Add nodes with bound agents
    # LangGraph requires sync functions, but we can use functools.partial
    from functools import partial
    
    workflow.add_node("retrieve", partial(retrieve_node, retriever=retriever))
    workflow.add_node("compress", partial(compress_node, compressor=compressor))
    
    # Add edges
    workflow.set_entry_point("retrieve")
    workflow.add_conditional_edges(
        "retrieve",
        should_continue_retrieval,
        {
            "retrieve": "retrieve",  # Loop back
            "compress": "compress"   # Move to compression
        }
    )
    workflow.add_edge("compress", END)
    
    return workflow.compile()


class AgenticRAG:
    """High-level interface for the agentic RAG system."""
    
    def __init__(self, vector_store: VectorStore):
        self.vector_store = vector_store
        self.workflow = create_rag_workflow(vector_store)
        
    async def query(self, 
                   question: str, 
                   repo_name: str,
                   max_iterations: int = 5) -> Dict[str, Any]:
        """Execute an agentic RAG query."""
        
        # Initialize state
        initial_state = AgentState(
            query=question,
            repo_name=repo_name,
            max_iterations=max_iterations
        )
        
        logger.info("agentic_rag_start", 
                   query=question,
                   repo=repo_name,
                   max_iterations=max_iterations)
        
        try:
            # Run workflow (LangGraph uses sync invoke)
            final_state = self.workflow.invoke(initial_state.dict())
            
            logger.info("agentic_rag_complete",
                       iterations=final_state["current_iteration"],
                       chunks_retrieved=len(final_state["retrieved_chunks"]),
                       total_tokens=final_state["total_tokens"],
                       total_cost=final_state["total_cost"])
            
            # Format response
            return {
                "answer": final_state["final_answer"],
                "metadata": {
                    "iterations": final_state["current_iteration"],
                    "chunks_used": len(final_state["retrieved_chunks"]),
                    "tokens_used": final_state["total_tokens"],
                    "cost_usd": final_state["total_cost"],
                    "search_history": final_state["search_history"]
                },
                "chunks": [
                    {
                        "file": chunk["file_path"],
                        "lines": f"{chunk['start_line']}-{chunk['end_line']}",
                        "content": chunk["content"][:200] + "..." if len(chunk["content"]) > 200 else chunk["content"]
                    }
                    for chunk in final_state["retrieved_chunks"][:5]  # Top 5 chunks
                ]
            }
            
        except Exception as e:
            logger.error("agentic_rag_error", error=str(e))
            raise