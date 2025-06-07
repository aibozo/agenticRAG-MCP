"""Compressor Agent that summarizes retrieved chunks into actionable insights."""

import json
from typing import List, Dict, Any
from src.agents.base import Agent, AgentResponse, AgentState
from src.config.settings import settings
from src.utils.logging import get_logger

logger = get_logger(__name__)


class CompressorAgent(Agent):
    """Agent that compresses retrieved chunks into concise, high-value insights."""
    
    def __init__(self, model: str = None):
        # Use a more cost-effective model for compression by default
        super().__init__(model or settings.compression_model)
        
    async def run(self, state: AgentState) -> AgentResponse:
        """Compress retrieved chunks into a concise answer."""
        
        if not state.retrieved_chunks:
            return AgentResponse(
                content="No code chunks were retrieved to analyze.",
                metadata={"agent": "compressor", "chunks_processed": 0}
            )
            
        # Group chunks by file for better organization
        chunks_by_file = self._group_chunks_by_file(state.retrieved_chunks)
        
        # Compress the chunks
        compressed_result = await self._compress_chunks(
            query=state.query,
            chunks_by_file=chunks_by_file
        )
        
        # Update state with final answer
        state.final_answer = compressed_result["answer"]
        
        return AgentResponse(
            content=compressed_result["answer"],
            metadata={
                "agent": "compressor",
                "chunks_processed": len(state.retrieved_chunks),
                "files_referenced": len(chunks_by_file),
                "key_insights": compressed_result.get("insights", [])
            },
            tokens_used=compressed_result.get("tokens", 0),
            cost_usd=compressed_result.get("cost", 0.0)
        )
        
    def _group_chunks_by_file(self, chunks: List[Dict[str, Any]]) -> Dict[str, List[Dict]]:
        """Group chunks by file path for better context."""
        chunks_by_file = {}
        
        for chunk in chunks:
            file_path = chunk["file_path"]
            if file_path not in chunks_by_file:
                chunks_by_file[file_path] = []
            chunks_by_file[file_path].append(chunk)
            
        # Sort chunks within each file by line number
        for file_path in chunks_by_file:
            chunks_by_file[file_path].sort(key=lambda x: x["start_line"])
            
        return chunks_by_file
        
    async def _compress_chunks(self, query: str, chunks_by_file: Dict[str, List[Dict]]) -> Dict[str, Any]:
        """Compress chunks into a concise answer with citations."""
        
        # Prepare context for compression
        context_parts = []
        for file_path, chunks in chunks_by_file.items():
            context_parts.append(f"\n=== {file_path} ===")
            for chunk in chunks[:5]:  # Limit chunks per file
                context_parts.append(f"\nLines {chunk['start_line']}-{chunk['end_line']}:")
                context_parts.append(chunk['content'])
                
        context = "\n".join(context_parts)
        
        # Truncate if too long (considering token limits)
        max_context_chars = 40000  # ~10k tokens
        if len(context) > max_context_chars:
            context = context[:max_context_chars] + "\n\n[... context truncated ...]"
            
        messages = [
            {
                "role": "system",
                "content": """You are an expert code analyst. Compress the retrieved code into a concise, actionable answer.

Your task:
1. Answer the user's question directly based on the code
2. Reference specific files and line numbers
3. Highlight key insights and patterns
4. Keep the response under 4KB while preserving critical details

Format your response as JSON:
{
    "answer": "Your comprehensive answer with citations like file.py:123",
    "insights": ["Key insight 1", "Key insight 2", ...],
    "files_referenced": ["file1.py", "file2.py", ...],
    "needs_clarification": false,
    "clarification_reason": "Optional: what additional info would help"
}"""
            },
            {
                "role": "user",
                "content": f"""Question: {query}

Retrieved Code Context:
{context}

Provide a comprehensive answer based on this code."""
            }
        ]
        
        result = await self._call_llm(messages, temperature=0.0)
        response = result["response"]
        
        try:
            # Parse JSON response
            compressed = json.loads(response.choices[0].message.content)
            compressed["tokens"] = result["tokens"]
            compressed["cost"] = result["cost"]
            
            logger.info("compression_complete",
                       answer_length=len(compressed["answer"]),
                       insights_count=len(compressed.get("insights", [])),
                       tokens=result["tokens"])
            
            return compressed
            
        except json.JSONDecodeError:
            # Fallback to plain text if JSON parsing fails
            logger.warning("compression_json_parse_failed")
            
            return {
                "answer": response.choices[0].message.content,
                "insights": [],
                "files_referenced": list(chunks_by_file.keys()),
                "needs_clarification": False,
                "tokens": result["tokens"],
                "cost": result["cost"]
            }