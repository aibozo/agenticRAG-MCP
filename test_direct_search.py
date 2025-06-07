#!/usr/bin/env python3
"""Test direct vector search."""

import asyncio
from dotenv import load_dotenv
from src.storage.vector_store import VectorStore
from src.indexing.embedder import Embedder

load_dotenv()

async def test_search():
    # Initialize components
    vector_store = VectorStore(collection_name="agenticrag_test")
    embedder = Embedder()
    
    # Test queries
    queries = [
        "TextChunker class",
        "how does chunking work",
        "RetrieverAgent",
        "embeddings generation"
    ]
    
    for query in queries:
        print(f"\n{'='*60}")
        print(f"Query: {query}")
        print(f"{'='*60}")
        
        # Generate embedding
        embedding_result = await embedder.embed_single(query)
        
        # Search
        results = await vector_store.search(
            query_embedding=embedding_result.embedding,
            repo_name="agenticrag_test",
            k=5
        )
        
        print(f"Found {len(results)} results:")
        for i, result in enumerate(results, 1):
            print(f"\n{i}. Keys: {list(result.keys())}")
            print(f"   File: {result['metadata']['file_path']}")
            print(f"   Lines: {result['metadata']['start_line']}-{result['metadata']['end_line']}")
            print(f"   Content preview: {result.get('content', result.get('document', 'N/A'))[:100]}...")

if __name__ == "__main__":
    asyncio.run(test_search())