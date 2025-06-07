import asyncio
from pathlib import Path
from typing import List, Optional, Dict, Any
import json
from datetime import datetime
import git
from concurrent.futures import ThreadPoolExecutor
import os

from src.config.settings import settings
from src.utils.logging import get_logger
from src.indexing.file_walker import FileWalker, FileInfo
from src.indexing.chunker import TextChunker
from src.indexing.embedder import Embedder, EmbeddingCache
from src.storage.vector_store import VectorStore

logger = get_logger(__name__)


class RepoIndexer:
    """Orchestrates the indexing of a repository."""
    
    def __init__(
        self,
        repo_path: str,
        repo_name: str,
        ignore_patterns: Optional[List[str]] = None
    ):
        self.repo_path = Path(repo_path).resolve()
        self.repo_name = repo_name
        self.ignore_patterns = ignore_patterns or []
        
        # Initialize components
        self.file_walker = FileWalker(ignore_patterns)
        self.chunker = TextChunker()
        self.embedder = Embedder()
        self.embedding_cache = EmbeddingCache()
        self.vector_store = VectorStore(collection_name=repo_name)
        
        # Stats tracking
        self.stats = {
            "files_processed": 0,
            "files_skipped": 0,
            "chunks_created": 0,
            "tokens_processed": 0,
            "embeddings_created": 0,
            "embeddings_cached": 0,
            "errors": []
        }
    
    def _get_git_commit(self) -> Optional[str]:
        """Get current git commit hash if in a git repository."""
        try:
            repo = git.Repo(self.repo_path, search_parent_directories=True)
            return repo.head.commit.hexsha
        except:
            return None
    
    async def _process_file(self, file_info: FileInfo) -> bool:
        """Process a single file: read, chunk, embed, and store."""
        try:
            # Read file content
            with open(file_info.path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # Skip empty files
            if not content.strip():
                logger.debug("skipping_empty_file", path=str(file_info.path))
                self.stats["files_skipped"] += 1
                return False
            
            # Chunk the content
            chunks = self.chunker.chunk_text(
                content,
                language=file_info.language,
                file_path=file_info.relative_path
            )
            
            if not chunks:
                logger.warning("no_chunks_created", path=str(file_info.path))
                self.stats["files_skipped"] += 1
                return False
            
            # Prepare texts for embedding
            texts_to_embed = []
            cached_embeddings = []
            
            for chunk in chunks:
                # Check cache first
                cached = self.embedding_cache.get(chunk.content)
                if cached:
                    cached_embeddings.append((chunk, cached))
                    self.stats["embeddings_cached"] += 1
                else:
                    texts_to_embed.append(chunk)
            
            # Embed uncached chunks
            embeddings = []
            if texts_to_embed:
                chunk_texts = [chunk.content for chunk in texts_to_embed]
                embedding_results = await self.embedder.embed_texts(chunk_texts)
                
                # Cache the results
                for chunk, embedding in zip(texts_to_embed, embedding_results):
                    self.embedding_cache.put(chunk.content, embedding)
                    embeddings.append((chunk, embedding))
                    self.stats["embeddings_created"] += 1
            
            # Combine cached and new embeddings
            all_chunks_embeddings = cached_embeddings + embeddings
            all_chunks_embeddings.sort(key=lambda x: x[0].chunk_index)
            
            # Separate chunks and embeddings
            chunks = [item[0] for item in all_chunks_embeddings]
            embeddings = [item[1] for item in all_chunks_embeddings]
            
            # Store in vector database
            git_commit = self._get_git_commit()
            await self.vector_store.upsert_chunks(
                repo_name=self.repo_name,
                file_path=file_info.relative_path,
                chunks=chunks,
                embeddings=embeddings,
                git_commit=git_commit
            )
            
            # Update stats
            self.stats["files_processed"] += 1
            self.stats["chunks_created"] += len(chunks)
            self.stats["tokens_processed"] += sum(chunk.token_count for chunk in chunks)
            
            logger.info(
                "file_processed",
                path=file_info.relative_path,
                chunks=len(chunks),
                tokens=sum(chunk.token_count for chunk in chunks)
            )
            
            return True
            
        except Exception as e:
            logger.error(
                "file_processing_error",
                path=str(file_info.path),
                error=str(e)
            )
            self.stats["errors"].append({
                "file": str(file_info.path),
                "error": str(e)
            })
            return False
    
    async def index_repository(self, max_concurrent: int = 5) -> str:
        """Index the entire repository and return manifest path."""
        start_time = datetime.utcnow()
        
        logger.info(
            "indexing_started",
            repo_path=str(self.repo_path),
            repo_name=self.repo_name
        )
        
        # Clear existing data for this repo
        await self.vector_store.delete_repo(self.repo_name)
        
        # Collect all files to process
        files_to_process = list(self.file_walker.walk(str(self.repo_path)))
        
        logger.info(
            "files_discovered",
            total_files=len(files_to_process)
        )
        
        # Process files concurrently with semaphore to limit parallelism
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def process_with_semaphore(file_info):
            async with semaphore:
                return await self._process_file(file_info)
        
        # Process all files
        tasks = [process_with_semaphore(file_info) for file_info in files_to_process]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Log any exceptions
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(
                    "task_exception",
                    file=files_to_process[i].relative_path,
                    error=str(result)
                )
        
        # Get final stats from vector store
        repo_stats = await self.vector_store.get_repo_stats(self.repo_name)
        
        # Create manifest
        manifest = self.vector_store.create_manifest(self.repo_name, repo_stats)
        manifest["indexing_stats"] = self.stats
        manifest["indexing_duration_seconds"] = (datetime.utcnow() - start_time).total_seconds()
        manifest["git_commit"] = self._get_git_commit()
        manifest["ignore_patterns"] = self.ignore_patterns
        
        # Add embedder usage stats
        manifest["embedding_stats"] = self.embedder.get_usage_stats()
        manifest["cache_stats"] = self.embedding_cache.get_stats()
        
        # Save manifest
        manifest_dir = self.repo_path / ".mcp"
        manifest_dir.mkdir(exist_ok=True)
        manifest_path = manifest_dir / "manifest.json"
        
        with open(manifest_path, 'w') as f:
            json.dump(manifest, f, indent=2)
        
        logger.info(
            "indexing_completed",
            repo_name=self.repo_name,
            duration_seconds=manifest["indexing_duration_seconds"],
            files_processed=self.stats["files_processed"],
            chunks_created=self.stats["chunks_created"],
            tokens_processed=self.stats["tokens_processed"],
            manifest_path=str(manifest_path)
        )
        
        return str(manifest_path)


async def init_repo(
    path: str,
    repo_name: str,
    ignore_globs: Optional[List[str]] = None
) -> str:
    """Initialize repository indexing - main entry point."""
    indexer = RepoIndexer(path, repo_name, ignore_globs)
    return await indexer.index_repository()