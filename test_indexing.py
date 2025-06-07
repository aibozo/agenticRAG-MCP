#!/usr/bin/env python3
"""Test script for repository indexing."""

import asyncio
import os
from pathlib import Path
from src.indexing.indexer import init_repo

async def test_indexing():
    """Test indexing on current repository."""
    # Index the current agenticRAG repository
    repo_path = Path(__file__).parent
    repo_name = "agenticrag_test"
    
    print(f"Indexing repository: {repo_path}")
    print(f"Repository name: {repo_name}")
    
    try:
        manifest_path = await init_repo(
            path=str(repo_path),
            repo_name=repo_name,
            ignore_globs=["*.pyc", "__pycache__", "venv", ".git", "chroma_db"]
        )
        
        print(f"\nIndexing completed successfully!")
        print(f"Manifest saved to: {manifest_path}")
        
        # Read and display manifest
        with open(manifest_path, 'r') as f:
            import json
            manifest = json.load(f)
            
        print("\nManifest Summary:")
        print(f"- Total files: {manifest['total_files']}")
        print(f"- Total chunks: {manifest['total_chunks']}")
        print(f"- Total tokens: {manifest['total_tokens']:,}")
        print(f"- Languages: {manifest['languages']}")
        print(f"- Indexing duration: {manifest['indexing_duration_seconds']:.2f} seconds")
        
        if manifest['embedding_stats']:
            print(f"\nEmbedding Stats:")
            print(f"- Total tokens used: {manifest['embedding_stats']['total_tokens_used']:,}")
            print(f"- Estimated cost: ${manifest['embedding_stats']['estimated_cost_usd']:.4f}")
        
    except Exception as e:
        print(f"Error during indexing: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Set up minimal environment
    os.environ.setdefault("OPENAI_API_KEY", "sk-test")  # You'll need to set a real key
    os.environ.setdefault("ANTHROPIC_API_KEY", "sk-ant-test")
    
    asyncio.run(test_indexing())