import chromadb
from chromadb.config import Settings as ChromaSettings
from typing import List, Dict, Any, Optional, Tuple
import hashlib
from datetime import datetime
import json

from src.config.settings import settings
from src.utils.logging import get_logger
from src.indexing.chunker import Chunk
from src.indexing.embedder import EmbeddingResult

logger = get_logger(__name__)


class VectorStore:
    """Manages vector storage using ChromaDB."""
    
    def __init__(self, collection_name: str = None):
        self.collection_name = collection_name or settings.chroma_collection_name
        
        # Initialize ChromaDB client
        if settings.chroma_host and settings.chroma_port:
            # Remote Chroma
            self.client = chromadb.HttpClient(
                host=settings.chroma_host,
                port=settings.chroma_port,
                settings=ChromaSettings(
                    anonymized_telemetry=False,
                    allow_reset=settings.is_development
                )
            )
        else:
            # Local Chroma
            self.client = chromadb.PersistentClient(
                path=settings.chroma_persist_directory,
                settings=ChromaSettings(
                    anonymized_telemetry=False,
                    allow_reset=settings.is_development
                )
            )
        
        # Get or create collection
        try:
            self.collection = self.client.get_collection(self.collection_name)
            logger.info("collection_loaded", name=self.collection_name)
        except Exception as e:
            # ChromaDB raises different exceptions (ValueError, InvalidCollectionException)
            logger.info("collection_not_found", name=self.collection_name, error=str(e))
            self.collection = self.client.create_collection(
                name=self.collection_name,
                metadata={"created_at": datetime.utcnow().isoformat()}
            )
            logger.info("collection_created", name=self.collection_name)
    
    def generate_chunk_id(self, repo_name: str, file_path: str, chunk: Chunk) -> str:
        """Generate unique ID for a chunk."""
        # Use content hash to ensure idempotency
        content_hash = hashlib.sha256(chunk.content.encode()).hexdigest()[:16]
        return f"{repo_name}:{file_path}:{chunk.chunk_index}:{content_hash}"
    
    async def upsert_chunks(
        self,
        repo_name: str,
        file_path: str,
        chunks: List[Chunk],
        embeddings: List[EmbeddingResult],
        git_commit: Optional[str] = None
    ) -> int:
        """Upsert chunks with their embeddings to the vector store."""
        if len(chunks) != len(embeddings):
            raise ValueError("Number of chunks must match number of embeddings")
        
        ids = []
        documents = []
        metadatas = []
        embeddings_list = []
        
        for chunk, embedding in zip(chunks, embeddings):
            chunk_id = self.generate_chunk_id(repo_name, file_path, chunk)
            ids.append(chunk_id)
            documents.append(chunk.content)
            embeddings_list.append(embedding.embedding)
            
            # Build metadata
            metadata = {
                "repo_name": repo_name,
                "file_path": file_path,
                "start_line": chunk.start_line,
                "end_line": chunk.end_line,
                "chunk_index": chunk.chunk_index,
                "total_chunks": chunk.total_chunks,
                "language": chunk.metadata.get("language", "unknown"),
                "token_count": chunk.token_count,
                "indexed_at": datetime.utcnow().isoformat(),
                "embedding_model": embedding.model,
            }
            
            if git_commit:
                metadata["git_commit"] = git_commit
            
            # Add any additional metadata from chunk
            for key, value in chunk.metadata.items():
                if key not in metadata and isinstance(value, (str, int, float, bool)):
                    metadata[key] = value
            
            metadatas.append(metadata)
        
        # Upsert to ChromaDB
        try:
            self.collection.upsert(
                ids=ids,
                embeddings=embeddings_list,
                documents=documents,
                metadatas=metadatas
            )
            
            logger.info(
                "chunks_upserted",
                repo_name=repo_name,
                file_path=file_path,
                chunk_count=len(chunks)
            )
            
            return len(chunks)
            
        except Exception as e:
            logger.error(
                "upsert_failed",
                repo_name=repo_name,
                file_path=file_path,
                error=str(e)
            )
            raise
    
    async def search(
        self,
        query_embedding: List[float],
        repo_name: Optional[str] = None,
        k: int = 10,
        where: Optional[Dict[str, Any]] = None,
        include: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """Search for similar chunks using vector similarity."""
        # Build where clause
        where_clause = where or {}
        if repo_name:
            where_clause["repo_name"] = repo_name
        
        # Default include fields
        if include is None:
            include = ["metadatas", "documents", "distances"]
        
        try:
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=k,
                where=where_clause if where_clause else None,
                include=include
            )
            
            # Format results
            formatted_results = []
            for i in range(len(results['ids'][0])):
                result = {
                    "id": results['ids'][0][i],
                    "score": 1 - results['distances'][0][i],  # Convert distance to similarity
                }
                
                if "documents" in include:
                    result["content"] = results['documents'][0][i]
                
                if "metadatas" in include:
                    result["metadata"] = results['metadatas'][0][i]
                
                formatted_results.append(result)
            
            logger.debug(
                "search_completed",
                repo_name=repo_name,
                k=k,
                results_found=len(formatted_results)
            )
            
            return formatted_results
            
        except Exception as e:
            logger.error("search_failed", error=str(e))
            raise
    
    async def delete_repo(self, repo_name: str) -> int:
        """Delete all chunks for a repository."""
        try:
            # Get all IDs for this repo
            results = self.collection.get(
                where={"repo_name": repo_name},
                limit=10000  # ChromaDB limit
            )
            
            if results['ids']:
                self.collection.delete(ids=results['ids'])
                deleted_count = len(results['ids'])
                
                logger.info(
                    "repo_deleted",
                    repo_name=repo_name,
                    chunks_deleted=deleted_count
                )
                
                return deleted_count
            
            return 0
            
        except Exception as e:
            logger.error("delete_repo_failed", repo_name=repo_name, error=str(e))
            raise
    
    async def get_repo_stats(self, repo_name: str) -> Dict[str, Any]:
        """Get statistics for a repository."""
        try:
            results = self.collection.get(
                where={"repo_name": repo_name},
                limit=10000,
                include=["metadatas"]
            )
            
            if not results['ids']:
                return {
                    "repo_name": repo_name,
                    "total_chunks": 0,
                    "total_files": 0,
                    "languages": {},
                    "total_tokens": 0
                }
            
            # Calculate stats
            files = set()
            languages = {}
            total_tokens = 0
            
            for metadata in results['metadatas']:
                files.add(metadata.get('file_path', ''))
                
                lang = metadata.get('language', 'unknown')
                languages[lang] = languages.get(lang, 0) + 1
                
                total_tokens += metadata.get('token_count', 0)
            
            return {
                "repo_name": repo_name,
                "total_chunks": len(results['ids']),
                "total_files": len(files),
                "languages": languages,
                "total_tokens": total_tokens,
                "indexed_at": results['metadatas'][0].get('indexed_at') if results['metadatas'] else None
            }
            
        except Exception as e:
            logger.error("get_repo_stats_failed", repo_name=repo_name, error=str(e))
            raise
    
    def create_manifest(self, repo_name: str, stats: Dict[str, Any]) -> Dict[str, Any]:
        """Create a manifest for the indexed repository."""
        return {
            "repo_name": repo_name,
            "indexed_at": datetime.utcnow().isoformat(),
            "total_files": stats.get("total_files", 0),
            "total_chunks": stats.get("total_chunks", 0),
            "total_tokens": stats.get("total_tokens", 0),
            "chunking_params": {
                "strategy": "semantic_boundaries_v1",
                "max_tokens": settings.chunk_size_tokens,
                "overlap_tokens": settings.chunk_overlap_tokens
            },
            "languages": stats.get("languages", {}),
            "index_version": "1.0.0",
            "vector_store": {
                "type": "chromadb",
                "collection": self.collection_name,
                "embedding_model": settings.embedding_model
            }
        }