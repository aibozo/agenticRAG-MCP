#!/usr/bin/env python3
"""Debug why search isn't working."""

import asyncio
from dotenv import load_dotenv
from src.storage.vector_store import VectorStore
from src.indexing.embedder import Embedder

load_dotenv()

async def debug_search():
    vector_store = VectorStore(collection_name="agenticrag_test")
    embedder = Embedder()
    
    # First, check what's in the collection
    print("Checking collection contents...")
    collection = vector_store.collection
    print(f"Total documents: {collection.count()}")
    
    # Get sample documents
    sample = collection.get(limit=3)
    print("\nSample documents:")
    for i, (id, meta) in enumerate(zip(sample['ids'], sample['metadatas'])):
        print(f"{i+1}. {meta['file_path']} - repo: {meta.get('repo_name', 'N/A')}")
    
    # Now test search with a simple query
    query = "TextChunker"
    print(f"\nSearching for: '{query}'")
    
    embedding_result = await embedder.embed_single(query)
    
    # Try direct ChromaDB query
    results = collection.query(
        query_embeddings=[embedding_result.embedding],
        n_results=5,
        where={"repo_name": "agenticrag_test"}
    )
    
    print(f"\nDirect ChromaDB results: {len(results['ids'][0])} found")
    
    # Also try via vector_store.search
    results2 = await vector_store.search(
        query_embedding=embedding_result.embedding,
        repo_name="agenticrag_test",
        k=5
    )
    
    print(f"VectorStore.search results: {len(results2)} found")

if __name__ == "__main__":
    asyncio.run(debug_search())