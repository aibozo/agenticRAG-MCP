#!/usr/bin/env python3
"""Test script to verify AgenticRAG installation."""

import sys
import os
from pathlib import Path

def test_imports():
    """Test that all required packages can be imported."""
    print("Testing imports...")
    
    try:
        import chromadb
        print("✓ ChromaDB")
    except ImportError as e:
        print(f"✗ ChromaDB: {e}")
        return False
        
    try:
        import openai
        print("✓ OpenAI")
    except ImportError as e:
        print(f"✗ OpenAI: {e}")
        return False
        
    try:
        import tiktoken
        print("✓ Tiktoken")
    except ImportError as e:
        print(f"✗ Tiktoken: {e}")
        return False
        
    try:
        import langgraph
        print("✓ LangGraph")
    except ImportError as e:
        print(f"✗ LangGraph: {e}")
        return False
        
    try:
        from dotenv import load_dotenv
        print("✓ Python-dotenv")
    except ImportError as e:
        print(f"✗ Python-dotenv: {e}")
        return False
        
    return True

def test_environment():
    """Test environment variables."""
    print("\nTesting environment...")
    
    from dotenv import load_dotenv
    load_dotenv()
    
    if not os.getenv('OPENAI_API_KEY'):
        print("✗ OPENAI_API_KEY not found in environment")
        return False
    else:
        print("✓ OPENAI_API_KEY found")
        
    if os.getenv('ANTHROPIC_API_KEY'):
        print("✓ ANTHROPIC_API_KEY found (optional)")
    else:
        print("! ANTHROPIC_API_KEY not found (optional)")
        
    return True

def test_directories():
    """Test that required directories exist."""
    print("\nTesting directories...")
    
    dirs = ['chroma_db', 'logs', '.mcp', 'src']
    all_exist = True
    
    for dir_name in dirs:
        if Path(dir_name).exists():
            print(f"✓ {dir_name}/")
        else:
            print(f"✗ {dir_name}/ (missing)")
            all_exist = False
            
    return all_exist

def test_mcp_server():
    """Test that MCP server can be imported."""
    print("\nTesting MCP server...")
    
    try:
        from src.mcp_server import MCPServer
        print("✓ MCP server importable")
        return True
    except ImportError as e:
        print(f"✗ MCP server: {e}")
        return False

def main():
    """Run all tests."""
    print("AgenticRAG Installation Test")
    print("=" * 40)
    
    tests = [
        test_imports,
        test_environment,
        test_directories,
        test_mcp_server
    ]
    
    all_passed = True
    for test in tests:
        if not test():
            all_passed = False
            
    print("\n" + "=" * 40)
    if all_passed:
        print("✓ All tests passed! AgenticRAG is ready to use.")
        sys.exit(0)
    else:
        print("✗ Some tests failed. Please run ./install.sh to complete setup.")
        sys.exit(1)

if __name__ == "__main__":
    main()