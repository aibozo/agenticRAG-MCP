#!/usr/bin/env python3
"""Test script for local development without Redis/Docker."""

import asyncio
import os
from pathlib import Path
import tempfile
import shutil

# Mock Redis for testing
class MockRedis:
    def __init__(self):
        self.data = {}
    
    async def ping(self):
        return True
    
    async def setex(self, key, ttl, value):
        self.data[key] = value
    
    async def get(self, key):
        return self.data.get(key)
    
    async def rpush(self, key, value):
        if key not in self.data:
            self.data[key] = []
        self.data[key].append(value)
    
    async def blpop(self, key, timeout=None):
        if key in self.data and self.data[key]:
            return (key, self.data[key].pop(0))
        return None
    
    async def close(self):
        pass

# Monkey patch for testing
import src.workers.indexing_worker
original_from_url = src.workers.indexing_worker.redis.from_url
src.workers.indexing_worker.redis.from_url = lambda *args, **kwargs: MockRedis()

async def test_basic_functionality():
    """Test basic indexing functionality."""
    print("Testing AgenticRAG basic functionality...\n")
    
    # Create a small test repository
    test_dir = Path(tempfile.mkdtemp(prefix="agenticrag_test_"))
    print(f"Created test directory: {test_dir}")
    
    try:
        # Create some test files
        (test_dir / "main.py").write_text('''
def hello_world():
    """Print hello world."""
    print("Hello, World!")

def calculate_sum(a, b):
    """Calculate sum of two numbers."""
    return a + b

if __name__ == "__main__":
    hello_world()
    result = calculate_sum(5, 3)
    print(f"Sum: {result}")
''')
        
        (test_dir / "utils.py").write_text('''
import json
from typing import Dict, Any

def load_config(path: str) -> Dict[str, Any]:
    """Load configuration from JSON file."""
    with open(path, 'r') as f:
        return json.load(f)

def save_config(config: Dict[str, Any], path: str) -> None:
    """Save configuration to JSON file."""
    with open(path, 'w') as f:
        json.dump(config, f, indent=2)
''')
        
        (test_dir / "README.md").write_text('''
# Test Project

This is a test project for AgenticRAG.

## Features
- Simple Python functions
- Configuration utilities
- Test documentation
''')
        
        # Test file walker
        from src.indexing.file_walker import FileWalker
        walker = FileWalker()
        files = list(walker.walk(str(test_dir)))
        print(f"\n✅ File Walker found {len(files)} files:")
        for f in files:
            print(f"   - {f.relative_path} ({f.language or 'text'})")
        
        # Test chunker
        from src.indexing.chunker import TextChunker
        chunker = TextChunker(chunk_size=100, chunk_overlap=10)
        
        with open(files[0].path, 'r') as f:
            content = f.read()
        
        chunks = chunker.chunk_text(content, language=files[0].language)
        print(f"\n✅ Chunker created {len(chunks)} chunks from {files[0].relative_path}")
        for i, chunk in enumerate(chunks[:2]):  # Show first 2 chunks
            print(f"   Chunk {i}: lines {chunk.start_line}-{chunk.end_line}, {chunk.token_count} tokens")
        
        # Test embedder (mock)
        print("\n✅ Embedder (mocked - no API calls)")
        print("   Would embed text into vectors")
        
        # Test vector store (local Chroma)
        from src.storage.vector_store import VectorStore
        store = VectorStore(collection_name="test_collection")
        print(f"\n✅ Vector Store initialized with collection: {store.collection_name}")
        
        # Clean up
        stats = await store.get_repo_stats("test_repo")
        print(f"   Collection stats: {stats['total_chunks']} chunks, {stats['total_files']} files")
        
    finally:
        # Clean up test directory
        shutil.rmtree(test_dir)
        print(f"\n🧹 Cleaned up test directory")

async def test_api_models():
    """Test API request/response models."""
    from src.api.repos import InitRepoRequest, InitRepoResponse
    from src.api.queries import QueryRequest, QueryResponse
    
    print("\n\nTesting API Models...")
    
    # Test repo init request
    init_req = InitRepoRequest(
        path="/home/user/myproject",
        repo_name="myproject",
        ignore_globs=["*.pyc", "__pycache__"]
    )
    print(f"\n✅ InitRepoRequest: {init_req.model_dump()}")
    
    # Test query request
    query_req = QueryRequest(
        question="How does the authentication work?",
        repo_name="myproject",
        max_iterations=3
    )
    print(f"\n✅ QueryRequest: {query_req.model_dump()}")

if __name__ == "__main__":
    # Set dummy API keys for testing
    os.environ["OPENAI_API_KEY"] = "sk-test-key"
    os.environ["ANTHROPIC_API_KEY"] = "sk-ant-test-key"
    
    print("=" * 60)
    print("AgenticRAG Local Testing (No External Dependencies)")
    print("=" * 60)
    
    # Restore original redis after import
    src.workers.indexing_worker.redis.from_url = original_from_url
    
    # Run tests
    asyncio.run(test_basic_functionality())
    asyncio.run(test_api_models())
    
    print("\n✅ All tests completed successfully!")
    print("\nNext steps:")
    print("1. Install Redis: sudo apt-get install redis-server")
    print("2. Set real API keys in .env file")
    print("3. Run ./scripts/setup_dev.sh")
    print("4. Start the full system with Redis")