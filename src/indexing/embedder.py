import openai
from typing import List, Dict, Any, Optional
import asyncio
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
import numpy as np
from dataclasses import dataclass
import time

from src.config.settings import settings
from src.utils.logging import get_logger

logger = get_logger(__name__)

@dataclass
class EmbeddingResult:
    """Result of embedding operation."""
    text: str
    embedding: List[float]
    model: str
    token_count: int
    
    @property
    def dimension(self) -> int:
        return len(self.embedding)


class Embedder:
    """Handles text embedding using OpenAI's API."""
    
    def __init__(self, model: str = None, batch_size: int = None):
        self.client = openai.AsyncOpenAI(api_key=settings.openai_api_key)
        self.model = model or settings.embedding_model
        self.batch_size = batch_size or settings.embedding_batch_size
        self.total_tokens_used = 0
        
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=60),
        retry=retry_if_exception_type((openai.RateLimitError, openai.APITimeoutError))
    )
    async def _embed_batch(self, texts: List[str]) -> List[EmbeddingResult]:
        """Embed a batch of texts with retry logic."""
        try:
            start_time = time.time()
            
            response = await self.client.embeddings.create(
                model=self.model,
                input=texts,
                encoding_format="float"
            )
            
            results = []
            for i, embedding_data in enumerate(response.data):
                result = EmbeddingResult(
                    text=texts[i],
                    embedding=embedding_data.embedding,
                    model=response.model,
                    token_count=response.usage.prompt_tokens // len(texts)  # Approximate
                )
                results.append(result)
            
            # Track usage
            self.total_tokens_used += response.usage.prompt_tokens
            
            elapsed = time.time() - start_time
            logger.info(
                "batch_embedded",
                batch_size=len(texts),
                tokens_used=response.usage.prompt_tokens,
                elapsed_seconds=elapsed,
                model=self.model
            )
            
            return results
            
        except openai.RateLimitError as e:
            logger.warning("rate_limit_hit", error=str(e), batch_size=len(texts))
            raise
        except Exception as e:
            logger.error("embedding_error", error=str(e), batch_size=len(texts))
            raise
    
    async def embed_texts(self, texts: List[str]) -> List[EmbeddingResult]:
        """Embed multiple texts, handling batching automatically."""
        if not texts:
            return []
        
        results = []
        
        # Process in batches
        for i in range(0, len(texts), self.batch_size):
            batch = texts[i:i + self.batch_size]
            batch_results = await self._embed_batch(batch)
            results.extend(batch_results)
            
            # Small delay between batches to avoid rate limits
            if i + self.batch_size < len(texts):
                await asyncio.sleep(0.1)
        
        return results
    
    async def embed_single(self, text: str) -> EmbeddingResult:
        """Embed a single text."""
        results = await self.embed_texts([text])
        return results[0] if results else None
    
    def estimate_cost(self, token_count: int) -> float:
        """Estimate cost for embedding tokens."""
        # Pricing as of 2024 for text-embedding-3-large
        cost_per_million = 0.13  # USD
        return (token_count / 1_000_000) * cost_per_million
    
    def get_usage_stats(self) -> Dict[str, Any]:
        """Get usage statistics."""
        return {
            "total_tokens_used": self.total_tokens_used,
            "estimated_cost_usd": self.estimate_cost(self.total_tokens_used),
            "model": self.model
        }


class EmbeddingCache:
    """Simple in-memory cache for embeddings to avoid re-computation."""
    
    def __init__(self, max_size: int = 10000):
        self.cache: Dict[str, EmbeddingResult] = {}
        self.max_size = max_size
        self.hits = 0
        self.misses = 0
    
    def get(self, text: str) -> Optional[EmbeddingResult]:
        """Get embedding from cache."""
        if text in self.cache:
            self.hits += 1
            return self.cache[text]
        self.misses += 1
        return None
    
    def put(self, text: str, result: EmbeddingResult) -> None:
        """Store embedding in cache."""
        if len(self.cache) >= self.max_size:
            # Simple FIFO eviction
            oldest = next(iter(self.cache))
            del self.cache[oldest]
        
        self.cache[text] = result
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_requests = self.hits + self.misses
        hit_rate = self.hits / total_requests if total_requests > 0 else 0
        
        return {
            "size": len(self.cache),
            "max_size": self.max_size,
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": hit_rate
        }