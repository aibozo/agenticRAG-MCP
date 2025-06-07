#!/usr/bin/env python3
"""Test script for the agentic RAG system."""

import asyncio
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables first
load_dotenv()

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.storage.vector_store import VectorStore
from src.agents.workflow import AgenticRAG
from src.utils.logging import get_logger

logger = get_logger(__name__)


async def test_agentic_rag():
    """Test the agentic RAG system with a sample query."""
    
    # Initialize components
    print("Initializing vector store...")
    vector_store = VectorStore(collection_name="agenticrag_test")
    
    # Check if we have any indexed repos
    try:
        # This is a simple test - in reality, you'd check properly
        test_repo = "agenticrag_test"  # The repo we just indexed
        
        print(f"\nInitializing AgenticRAG...")
        agentic_rag = AgenticRAG(vector_store)
        
        # Test queries
        test_queries = [
            "How does the chunking system work?",
            "What is the purpose of the RetrieverAgent class?",
            "How are embeddings generated in this codebase?",
        ]
        
        for query in test_queries:
            print(f"\n{'='*80}")
            print(f"Query: {query}")
            print(f"{'='*80}")
            
            try:
                result = await agentic_rag.query(
                    question=query,
                    repo_name=test_repo,
                    max_iterations=3
                )
                
                print(f"\nAnswer:\n{result['answer']}")
                
                print(f"\nMetadata:")
                for key, value in result['metadata'].items():
                    print(f"  {key}: {value}")
                
                if result.get('chunks'):
                    print(f"\nTop Sources:")
                    for i, chunk in enumerate(result['chunks'][:3], 1):
                        print(f"  {i}. {chunk['file']} (lines {chunk['lines']})")
                        
            except Exception as e:
                print(f"Error: {e}")
                import traceback
                traceback.print_exc()
                
    except Exception as e:
        print(f"Setup error: {e}")
        print("\nMake sure you've indexed a repository first using:")
        print("  python test_indexing.py")


if __name__ == "__main__":
    print("Testing Agentic RAG System")
    print("=" * 80)
    
    # Check for OpenAI API key
    import os
    if not os.getenv("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY not set in environment")
        sys.exit(1)
        
    asyncio.run(test_agentic_rag())