import tiktoken
from typing import List, Tuple, Optional, Dict, Any
from dataclasses import dataclass
import re

from src.config.settings import settings
from src.utils.logging import get_logger

logger = get_logger(__name__)

@dataclass
class Chunk:
    """Represents a chunk of text from a file."""
    content: str
    start_line: int
    end_line: int
    start_char: int
    end_char: int
    chunk_index: int
    total_chunks: int
    token_count: int
    metadata: Dict[str, Any]


class TextChunker:
    """Chunks text files respecting code boundaries when possible."""
    
    def __init__(
        self,
        chunk_size: int = None,
        chunk_overlap: int = None,
        encoding_name: str = "cl100k_base"  # GPT-4 encoding
    ):
        self.chunk_size = chunk_size or settings.chunk_size_tokens
        self.chunk_overlap = chunk_overlap or settings.chunk_overlap_tokens
        self.encoding = tiktoken.get_encoding(encoding_name)
        
        # Patterns for semantic boundaries
        self.boundary_patterns = {
            'python': [
                r'^class\s+\w+',
                r'^def\s+\w+',
                r'^async\s+def\s+\w+',
                r'^@\w+',  # Decorators
            ],
            'javascript': [
                r'^function\s+\w+',
                r'^const\s+\w+\s*=\s*function',
                r'^const\s+\w+\s*=\s*\(',
                r'^class\s+\w+',
                r'^export\s+',
            ],
            'typescript': [
                r'^function\s+\w+',
                r'^const\s+\w+\s*=\s*function',
                r'^const\s+\w+\s*=\s*\(',
                r'^class\s+\w+',
                r'^interface\s+\w+',
                r'^type\s+\w+',
                r'^export\s+',
            ],
            'java': [
                r'^public\s+class\s+\w+',
                r'^private\s+class\s+\w+',
                r'^protected\s+class\s+\w+',
                r'^public\s+\w+\s+\w+\s*\(',
                r'^private\s+\w+\s+\w+\s*\(',
                r'^protected\s+\w+\s+\w+\s*\(',
            ],
        }
    
    def count_tokens(self, text: str) -> int:
        """Count tokens in text using tiktoken."""
        return len(self.encoding.encode(text))
    
    def _find_boundaries(self, lines: List[str], language: Optional[str]) -> List[int]:
        """Find semantic boundaries in code based on language patterns."""
        boundaries = [0]  # Always start at beginning
        
        if language and language in self.boundary_patterns:
            patterns = self.boundary_patterns[language]
            for i, line in enumerate(lines):
                stripped = line.strip()
                for pattern in patterns:
                    if re.match(pattern, stripped):
                        boundaries.append(i)
                        break
        
        boundaries.append(len(lines))  # Always end at the end
        return sorted(set(boundaries))
    
    def _split_by_tokens(self, text: str, max_tokens: int) -> List[str]:
        """Split text when it exceeds max tokens, trying to break at newlines."""
        if self.count_tokens(text) <= max_tokens:
            return [text]
        
        lines = text.split('\n')
        chunks = []
        current_chunk = []
        current_tokens = 0
        
        for line in lines:
            line_tokens = self.count_tokens(line + '\n')
            
            if current_tokens + line_tokens > max_tokens and current_chunk:
                # Save current chunk
                chunks.append('\n'.join(current_chunk))
                current_chunk = [line]
                current_tokens = line_tokens
            else:
                current_chunk.append(line)
                current_tokens += line_tokens
        
        if current_chunk:
            chunks.append('\n'.join(current_chunk))
        
        return chunks
    
    def chunk_text(
        self, 
        content: str, 
        language: Optional[str] = None,
        file_path: Optional[str] = None
    ) -> List[Chunk]:
        """Chunk text content into overlapping chunks."""
        lines = content.split('\n')
        
        # Find semantic boundaries if language is known
        boundaries = self._find_boundaries(lines, language)
        
        chunks = []
        chunk_index = 0
        
        # Process each boundary section
        for i in range(len(boundaries) - 1):
            start_idx = boundaries[i]
            end_idx = boundaries[i + 1]
            
            # Get lines for this section
            section_lines = lines[start_idx:end_idx]
            section_text = '\n'.join(section_lines)
            
            # If section is small enough, keep it as one chunk
            if self.count_tokens(section_text) <= self.chunk_size:
                chunk_start_char = sum(len(line) + 1 for line in lines[:start_idx])
                chunk_end_char = chunk_start_char + len(section_text)
                
                chunks.append(Chunk(
                    content=section_text,
                    start_line=start_idx + 1,  # 1-indexed
                    end_line=end_idx,
                    start_char=chunk_start_char,
                    end_char=chunk_end_char,
                    chunk_index=chunk_index,
                    total_chunks=0,  # Will be updated later
                    token_count=self.count_tokens(section_text),
                    metadata={
                        'language': language,
                        'file_path': file_path,
                        'boundary_type': 'semantic'
                    }
                ))
                chunk_index += 1
            else:
                # Split large section into smaller chunks
                sub_chunks = self._split_by_tokens(section_text, self.chunk_size)
                
                for j, sub_chunk in enumerate(sub_chunks):
                    # Calculate line numbers for sub-chunk
                    sub_lines = sub_chunk.split('\n')
                    chunk_start_line = start_idx + sum(
                        len(self._split_by_tokens('\n'.join(section_lines[:k]), self.chunk_size)[0].split('\n'))
                        for k in range(j)
                    ) + 1
                    chunk_end_line = chunk_start_line + len(sub_lines) - 1
                    
                    chunk_start_char = sum(len(line) + 1 for line in lines[:chunk_start_line - 1])
                    chunk_end_char = chunk_start_char + len(sub_chunk)
                    
                    chunks.append(Chunk(
                        content=sub_chunk,
                        start_line=chunk_start_line,
                        end_line=chunk_end_line,
                        start_char=chunk_start_char,
                        end_char=chunk_end_char,
                        chunk_index=chunk_index,
                        total_chunks=0,  # Will be updated later
                        token_count=self.count_tokens(sub_chunk),
                        metadata={
                            'language': language,
                            'file_path': file_path,
                            'boundary_type': 'token_split'
                        }
                    ))
                    chunk_index += 1
        
        # Update total_chunks for all chunks
        total_chunks = len(chunks)
        for chunk in chunks:
            chunk.total_chunks = total_chunks
        
        # Add overlap if requested
        if self.chunk_overlap > 0 and len(chunks) > 1:
            chunks = self._add_overlap(chunks, lines)
        
        logger.debug(
            "text_chunked",
            file_path=file_path,
            total_chunks=len(chunks),
            total_tokens=sum(c.token_count for c in chunks)
        )
        
        return chunks
    
    def _add_overlap(self, chunks: List[Chunk], lines: List[str]) -> List[Chunk]:
        """Add overlapping content between chunks."""
        overlapped_chunks = []
        
        for i, chunk in enumerate(chunks):
            if i == 0:
                # First chunk - add overlap from next chunk
                if i + 1 < len(chunks):
                    next_chunk = chunks[i + 1]
                    overlap_lines = lines[next_chunk.start_line - 1:next_chunk.start_line + 5]
                    overlap_text = '\n'.join(overlap_lines)
                    
                    if self.count_tokens(overlap_text) <= self.chunk_overlap:
                        chunk.content += '\n' + overlap_text
                        chunk.end_line = min(chunk.end_line + len(overlap_lines), len(lines))
                        chunk.token_count = self.count_tokens(chunk.content)
            
            elif i == len(chunks) - 1:
                # Last chunk - add overlap from previous chunk
                prev_chunk = chunks[i - 1]
                overlap_lines = lines[max(0, chunk.start_line - 6):chunk.start_line - 1]
                overlap_text = '\n'.join(overlap_lines)
                
                if self.count_tokens(overlap_text) <= self.chunk_overlap:
                    chunk.content = overlap_text + '\n' + chunk.content
                    chunk.start_line = max(1, chunk.start_line - len(overlap_lines))
                    chunk.token_count = self.count_tokens(chunk.content)
            
            else:
                # Middle chunks - add overlap from both sides
                prev_chunk = chunks[i - 1]
                next_chunk = chunks[i + 1]
                
                # Previous overlap
                prev_overlap_lines = lines[max(0, chunk.start_line - 4):chunk.start_line - 1]
                prev_overlap_text = '\n'.join(prev_overlap_lines)
                
                # Next overlap
                next_overlap_lines = lines[next_chunk.start_line - 1:next_chunk.start_line + 3]
                next_overlap_text = '\n'.join(next_overlap_lines)
                
                if (self.count_tokens(prev_overlap_text) + self.count_tokens(next_overlap_text)) <= self.chunk_overlap:
                    chunk.content = prev_overlap_text + '\n' + chunk.content + '\n' + next_overlap_text
                    chunk.start_line = max(1, chunk.start_line - len(prev_overlap_lines))
                    chunk.end_line = min(chunk.end_line + len(next_overlap_lines), len(lines))
                    chunk.token_count = self.count_tokens(chunk.content)
            
            overlapped_chunks.append(chunk)
        
        return overlapped_chunks