"""Retriever Agent that searches and self-evaluates results."""

import json
from typing import List, Dict, Any
from src.agents.base import Agent, AgentResponse, AgentState
from src.storage.vector_store import VectorStore
from src.utils.logging import get_logger

logger = get_logger(__name__)


class RetrieverAgent(Agent):
    """Agent that retrieves relevant code chunks with self-evaluation."""
    
    def __init__(self, vector_store: VectorStore, model: str = None):
        super().__init__(model)
        self.vector_store = vector_store
        
    async def run(self, state: AgentState) -> AgentResponse:
        """Execute retrieval with self-evaluation loop."""
        
        # Generate search query
        search_query = await self._generate_search_query(state)
        
        # Search vector store
        chunks = await self._search_chunks(
            query=search_query,
            repo_name=state.repo_name,
            k=20  # Get more initially, we'll filter
        )
        
        # Add to state
        state.search_history.append({
            "iteration": state.current_iteration,
            "query": search_query,
            "chunks_found": len(chunks)
        })
        
        # Merge with existing chunks (dedup by ID)
        existing_ids = {c.get("id") for c in state.retrieved_chunks}
        new_chunks = [c for c in chunks if c.get("id") not in existing_ids]
        state.retrieved_chunks.extend(new_chunks)
        
        # Self-evaluate
        evaluation = await self._self_evaluate(state)
        
        # Update state
        state.sufficient_context = evaluation["sufficient"]
        state.current_iteration += 1
        
        # Log evaluation
        logger.info("retriever_evaluation",
                   iteration=state.current_iteration,
                   sufficient=evaluation["sufficient"],
                   reasoning=evaluation["reasoning"])
        
        return AgentResponse(
            content={
                "search_query": search_query,
                "new_chunks": len(new_chunks),
                "total_chunks": len(state.retrieved_chunks),
                "evaluation": evaluation
            },
            metadata={
                "agent": "retriever",
                "iteration": state.current_iteration
            },
            tokens_used=evaluation.get("tokens", 0),
            cost_usd=evaluation.get("cost", 0.0)
        )
        
    async def _generate_search_query(self, state: AgentState) -> str:
        """Generate an optimized search query based on context."""
        
        messages = [
            {
                "role": "system",
                "content": """You are an expert code search assistant. Generate search queries to find relevant code.
                
Your task:
1. Analyze the user's question
2. Consider what code/files would help answer it
3. Generate a search query optimized for semantic similarity

Guidelines:
- Use technical terms and specific function/class names if mentioned
- Include programming concepts related to the question
- Be specific but not overly narrow
- Consider synonyms and related terms"""
            },
            {
                "role": "user",
                "content": f"""User Question: {state.query}
Repository: {state.repo_name}

Previous searches: {json.dumps(state.search_history, indent=2) if state.search_history else "None"}

Generate a search query to find relevant code in the codebase. 
Do NOT include repository names, site: operators, or other search engine syntax.
Just include relevant keywords, function names, and technical terms.
Return only the query text, nothing else."""
            }
        ]
        
        result = await self._call_llm(messages, temperature=0.3)
        response = result["response"]
        
        # Update state costs
        state.total_tokens += result["tokens"]
        state.total_cost += result["cost"]
        
        return response.choices[0].message.content.strip()
        
    async def _search_chunks(self, query: str, repo_name: str, k: int) -> List[Dict[str, Any]]:
        """Search vector store for relevant chunks."""
        
        logger.info("searching_chunks", query=query, repo=repo_name, k=k)
        
        # First, we need to generate embeddings for the query
        from src.indexing.embedder import Embedder
        embedder = Embedder()
        
        # Get embedding for query
        embedding_result = await embedder.embed_single(query)
        if not embedding_result:
            logger.error("failed_to_embed_query", query=query)
            return []
            
        query_embedding = embedding_result.embedding
        
        results = await self.vector_store.search(
            query_embedding=query_embedding,
            repo_name=repo_name,
            k=k
        )
        
        # Format results
        chunks = []
        for item in results:
            chunk_data = {
                "id": item["id"],
                "content": item["content"],
                "file_path": item["metadata"]["file_path"],
                "start_line": item["metadata"]["start_line"],
                "end_line": item["metadata"]["end_line"],
                "language": item["metadata"].get("language", "unknown"),
                "score": item.get("score", 0.0)  # ChromaDB returns score, not distance
            }
            chunks.append(chunk_data)
            
        return chunks
        
    async def _self_evaluate(self, state: AgentState) -> Dict[str, Any]:
        """Evaluate if we have sufficient context to answer the question."""
        
        # Prepare chunks summary for evaluation
        chunks_summary = []
        for chunk in state.retrieved_chunks[-10:]:  # Last 10 chunks for context
            chunks_summary.append({
                "file": chunk["file_path"],
                "lines": f"{chunk['start_line']}-{chunk['end_line']}",
                "preview": chunk["content"][:200] + "..." if len(chunk["content"]) > 200 else chunk["content"]
            })
            
        messages = [
            {
                "role": "system",
                "content": """You are evaluating whether the retrieved code chunks provide sufficient context to answer a question.

Evaluate based on:
1. **Coverage**: Do the chunks cover all aspects of the question?
2. **Relevance**: Are the chunks directly related to what's being asked?
3. **Completeness**: Is there enough implementation detail?
4. **Gaps**: What important information might be missing?

Return a JSON object with:
{
    "sufficient": true/false,
    "reasoning": "Brief explanation",
    "missing_aspects": ["list", "of", "missing", "topics"],
    "confidence": 0.0-1.0
}"""
            },
            {
                "role": "user", 
                "content": f"""Question: {state.query}

Retrieved chunks: {json.dumps(chunks_summary, indent=2)}

Total chunks retrieved: {len(state.retrieved_chunks)}
Search iterations completed: {state.current_iteration + 1}

Evaluate if we have sufficient context to answer the question."""
            }
        ]
        
        result = await self._call_llm(messages, temperature=0.0)
        response = result["response"]
        
        try:
            # Parse JSON response
            evaluation = json.loads(response.choices[0].message.content)
            evaluation["tokens"] = result["tokens"]
            evaluation["cost"] = result["cost"]
            
            # Update state costs
            state.total_tokens += result["tokens"]
            state.total_cost += result["cost"]
            
            return evaluation
            
        except json.JSONDecodeError:
            logger.error("evaluation_parse_error", 
                        response=response.choices[0].message.content)
            return {
                "sufficient": state.current_iteration >= 2,  # Fallback after 2 iterations
                "reasoning": "Failed to parse evaluation",
                "missing_aspects": [],
                "confidence": 0.5,
                "tokens": result["tokens"],
                "cost": result["cost"]
            }