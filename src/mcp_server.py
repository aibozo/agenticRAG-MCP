#!/usr/bin/env python3
"""MCP (Model Context Protocol) server for AgenticRAG."""

import asyncio
import json
import sys
import os
from typing import Dict, Any, Optional, List
from pathlib import Path
from dotenv import load_dotenv

# Add src to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables from .env file
env_path = Path(__file__).parent.parent / '.env'
if env_path.exists():
    load_dotenv(env_path)

from src.indexing.indexer import init_repo
from src.storage.vector_store import VectorStore
from src.agents.workflow import AgenticRAG
from src.config.settings import settings
from src.utils.logging import get_logger

logger = get_logger(__name__)

class MCPServer:
    """MCP server implementation for AgenticRAG."""
    
    def __init__(self):
        # Don't initialize vector store in constructor, do it lazily
        self._vector_store = None
        self._agentic_rag = None
        self.request_id = 0
        
    @property
    def vector_store(self):
        """Lazy initialization of vector store."""
        if self._vector_store is None:
            self._vector_store = VectorStore()
        return self._vector_store
        
    @property
    def agentic_rag(self):
        """Lazy initialization of agentic RAG."""
        if self._agentic_rag is None:
            self._agentic_rag = AgenticRAG(self.vector_store)
        return self._agentic_rag
        
    async def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle a JSON-RPC request."""
        method = request.get("method")
        params = request.get("params", {})
        request_id = request.get("id")
        
        try:
            if method == "tools/list":
                result = await self.list_tools()
            elif method == "tools/call":
                tool_name = params.get("name")
                tool_params = params.get("arguments", {})
                result = await self.call_tool(tool_name, tool_params)
            elif method == "notifications/initialized":
                # This is a notification, not a request, so we don't send a response
                logger.info("client_initialized")
                return None
            else:
                raise ValueError(f"Unknown method: {method}")
            
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": result
            }
            
        except Exception as e:
            logger.error("request_error", method=method, error=str(e))
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32603,
                    "message": str(e)
                }
            }
    
    async def list_tools(self) -> Dict[str, Any]:
        """List available tools."""
        return {
            "tools": [
                {
                    "name": "init_repo",
                    "description": "Index a repository for semantic search",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "string",
                                "description": "Absolute path to the repository"
                            },
                            "repo_name": {
                                "type": "string",
                                "description": "Name for the repository index"
                            },
                            "ignore_globs": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "Additional glob patterns to ignore"
                            }
                        },
                        "required": ["path", "repo_name"]
                    }
                },
                {
                    "name": "search_repo",
                    "description": "Search an indexed repository",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Natural language search query"
                            },
                            "repo_name": {
                                "type": "string",
                                "description": "Name of the repository to search"
                            },
                            "k": {
                                "type": "integer",
                                "description": "Number of results to return",
                                "default": 10
                            }
                        },
                        "required": ["query", "repo_name"]
                    }
                },
                {
                    "name": "get_repo_stats",
                    "description": "Get statistics for an indexed repository",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "repo_name": {
                                "type": "string",
                                "description": "Name of the repository"
                            }
                        },
                        "required": ["repo_name"]
                    }
                }
            ]
        }
    
    async def call_tool(self, name: str, params: Dict[str, Any]) -> Any:
        """Call a specific tool."""
        if name == "init_repo":
            path = params.get("path")
            repo_name = params.get("repo_name")
            ignore_globs = params.get("ignore_globs")
            
            # Validate path
            repo_path = Path(path)
            if not repo_path.exists():
                raise ValueError(f"Path does not exist: {path}")
            if not repo_path.is_dir():
                raise ValueError(f"Path is not a directory: {path}")
            
            # Run indexing
            manifest_path = await init_repo(path, repo_name, ignore_globs)
            
            # Read manifest
            with open(manifest_path, 'r') as f:
                manifest = json.load(f)
            
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Successfully indexed repository '{repo_name}'\n\n" +
                               f"Stats:\n" +
                               f"- Total files: {manifest.get('total_files', 0)}\n" +
                               f"- Total chunks: {manifest.get('total_chunks', 0)}\n" +
                               f"- Total tokens: {manifest.get('total_tokens', 0)}\n" +
                               f"- Duration: {manifest.get('indexing_duration_seconds', 0):.2f} seconds\n\n" +
                               f"Manifest saved to: {manifest_path}"
                    }
                ]
            }
            
        elif name == "search_repo":
            query = params.get("query")
            repo_name = params.get("repo_name")
            max_iterations = params.get("max_iterations", 3)
            
            # Use agentic RAG for search with the correct collection
            try:
                # Create AgenticRAG with the correct collection/repo name
                vector_store = VectorStore(collection_name=repo_name)
                agentic_rag = AgenticRAG(vector_store)
                
                result = await agentic_rag.query(
                    question=query,
                    repo_name=repo_name,
                    max_iterations=max_iterations
                )
                
                # Format response for MCP - must have content array
                answer_text = result.get("answer", "No answer generated")
                
                # Build a formatted response
                response_parts = [answer_text]
                
                # Add sources if available
                chunks = result.get("chunks", [])
                if chunks:
                    response_parts.append("\n\nSources:")
                    for i, chunk in enumerate(chunks[:5], 1):
                        response_parts.append(f"{i}. {chunk['file']} (lines {chunk['lines']})")
                
                # Add metadata summary
                metadata = result.get("metadata", {})
                if metadata:
                    response_parts.append(f"\n\nMetadata:")
                    response_parts.append(f"- Iterations: {metadata.get('iterations', 0)}")
                    response_parts.append(f"- Chunks retrieved: {metadata.get('chunks_used', 0)}")
                    response_parts.append(f"- Cost: ${metadata.get('cost_usd', 0):.4f}")
                
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": "\n".join(response_parts)
                        }
                    ]
                }
                
            except Exception as e:
                logger.error("search_repo_error", error=str(e))
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": f"Error searching repository: {str(e)}"
                        }
                    ],
                    "is_error": True
                }
            
        elif name == "get_repo_stats":
            repo_name = params.get("repo_name")
            # Use vector store with the correct collection name
            vector_store = VectorStore(collection_name=repo_name)
            stats = await vector_store.get_repo_stats(repo_name)
            
            # Format stats for MCP response
            stats_text = f"Repository: {repo_name}\n\n"
            stats_text += f"Total chunks: {stats.get('total_chunks', 0)}\n"
            stats_text += f"Unique files: {stats.get('total_files', 0)}\n"
            stats_text += f"Total tokens: {stats.get('total_tokens', 0)}\n"
            
            if stats.get('languages'):
                stats_text += "\nLanguages:\n"
                for lang, count in stats['languages'].items():
                    stats_text += f"  - {lang}: {count} chunks\n"
            
            return {
                "content": [
                    {
                        "type": "text",
                        "text": stats_text
                    }
                ]
            }
            
        else:
            raise ValueError(f"Unknown tool: {name}")
    
    async def run(self):
        """Run the MCP server."""
        logger.info("mcp_server_started")
        
        # Wait for initialization request first
        try:
            line = await asyncio.get_event_loop().run_in_executor(
                None, sys.stdin.readline
            )
            
            if line:
                request = json.loads(line.strip())
                
                # Handle initialization
                if request.get("method") == "initialize":
                    # Send initialized response
                    init_response = {
                        "jsonrpc": "2.0",
                        "id": request.get("id"),
                        "result": {
                            "protocolVersion": "2024-11-05",
                            "capabilities": {
                                "tools": {}
                            },
                            "serverInfo": {
                                "name": "agenticrag",
                                "version": "1.0.0"
                            }
                        }
                    }
                    print(json.dumps(init_response), flush=True)
                    
        except Exception as e:
            logger.error("initialization_error", error=str(e))
        
        # Read requests from stdin
        while True:
            try:
                line = await asyncio.get_event_loop().run_in_executor(
                    None, sys.stdin.readline
                )
                
                if not line:
                    break
                
                request = json.loads(line.strip())
                response = await self.handle_request(request)
                
                # Only send response if it's not None (notifications don't get responses)
                if response is not None:
                    print(json.dumps(response), flush=True)
                
            except json.JSONDecodeError as e:
                logger.error("invalid_json", error=str(e))
            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error("server_error", error=str(e))
        
        logger.info("mcp_server_stopped")

async def main():
    """Main entry point."""
    server = MCPServer()
    await server.run()

if __name__ == "__main__":
    # Ensure we have required environment variables
    if not os.environ.get("OPENAI_API_KEY"):
        print("Error: OPENAI_API_KEY environment variable is required", file=sys.stderr)
        sys.exit(1)
    
    asyncio.run(main())