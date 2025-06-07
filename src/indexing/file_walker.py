import os
import fnmatch
from pathlib import Path
from typing import List, Generator, Tuple, Optional
from dataclasses import dataclass
import hashlib
from datetime import datetime

from src.config.settings import settings
from src.utils.logging import get_logger

logger = get_logger(__name__)

@dataclass
class FileInfo:
    """Information about a file to be indexed."""
    path: Path
    relative_path: str
    size_bytes: int
    modified_time: datetime
    content_hash: Optional[str] = None
    
    @property
    def extension(self) -> str:
        return self.path.suffix.lower()
    
    @property
    def language(self) -> Optional[str]:
        """Detect programming language from file extension."""
        lang_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.jsx': 'javascript',
            '.ts': 'typescript',
            '.tsx': 'typescript',
            '.java': 'java',
            '.cpp': 'cpp',
            '.c': 'c',
            '.h': 'c',
            '.hpp': 'cpp',
            '.cs': 'csharp',
            '.go': 'go',
            '.rs': 'rust',
            '.rb': 'ruby',
            '.php': 'php',
            '.swift': 'swift',
            '.kt': 'kotlin',
            '.scala': 'scala',
            '.r': 'r',
            '.sql': 'sql',
            '.sh': 'bash',
            '.yaml': 'yaml',
            '.yml': 'yaml',
            '.json': 'json',
            '.xml': 'xml',
            '.md': 'markdown',
            '.rst': 'restructuredtext',
            '.txt': 'text',
        }
        return lang_map.get(self.extension)


class FileWalker:
    """Walks a directory tree and yields files for indexing."""
    
    def __init__(self, ignore_patterns: Optional[List[str]] = None):
        self.ignore_patterns = self._load_ignore_patterns(ignore_patterns)
        self.max_file_size = settings.max_file_size_mb * 1024 * 1024  # Convert to bytes
        
    def _load_ignore_patterns(self, additional_patterns: Optional[List[str]] = None) -> List[str]:
        """Load ignore patterns from .agenticragignore and merge with additional patterns."""
        patterns = []
        
        # Default patterns
        default_patterns = [
            '__pycache__',
            '*.pyc',
            '*.pyo',
            'node_modules',
            'venv',
            'env',
            '.git',
            '.svn',
            '.hg',
        ]
        patterns.extend(default_patterns)
        
        # Load from .agenticragignore if exists
        ignore_file = Path('.agenticragignore')
        if ignore_file.exists():
            with open(ignore_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        patterns.append(line)
        
        # Add additional patterns
        if additional_patterns:
            patterns.extend(additional_patterns)
            
        return list(set(patterns))  # Remove duplicates
    
    def _should_ignore(self, path: Path, root: Path) -> bool:
        """Check if a path should be ignored based on patterns."""
        relative_path = str(path.relative_to(root))
        
        # Check if it's a hidden file (starts with .)
        if path.name.startswith('.') and path.name != '.':
            return True
            
        for pattern in self.ignore_patterns:
            # Check against full relative path
            if fnmatch.fnmatch(relative_path, pattern):
                return True
            # Check against filename only
            if fnmatch.fnmatch(path.name, pattern):
                return True
            # Check if any parent directory matches
            for parent in path.relative_to(root).parents:
                if fnmatch.fnmatch(str(parent), pattern):
                    return True
                    
        return False
    
    def _is_binary(self, file_path: Path) -> bool:
        """Check if a file is binary."""
        try:
            with open(file_path, 'rb') as f:
                chunk = f.read(1024)
                if b'\0' in chunk:
                    return True
                # Check for high ratio of non-printable characters
                non_printable = sum(1 for byte in chunk if byte < 32 or byte > 126)
                return non_printable / len(chunk) > 0.3
        except Exception:
            return True
    
    def walk(self, root_path: str) -> Generator[FileInfo, None, None]:
        """Walk directory tree and yield FileInfo objects for indexable files."""
        root = Path(root_path).resolve()
        
        if not root.exists():
            raise ValueError(f"Path does not exist: {root}")
        if not root.is_dir():
            raise ValueError(f"Path is not a directory: {root}")
            
        logger.info("starting_file_walk", root_path=str(root))
        
        total_files = 0
        skipped_files = 0
        
        for dirpath, dirnames, filenames in os.walk(root):
            current_dir = Path(dirpath)
            
            # Filter directories to prevent walking into ignored paths
            dirnames[:] = [
                d for d in dirnames 
                if not self._should_ignore(current_dir / d, root)
            ]
            
            for filename in filenames:
                file_path = current_dir / filename
                
                # Skip ignored files
                if self._should_ignore(file_path, root):
                    skipped_files += 1
                    continue
                
                # Skip binary files
                if self._is_binary(file_path):
                    logger.debug("skipping_binary_file", path=str(file_path))
                    skipped_files += 1
                    continue
                
                # Check file size
                try:
                    stat = file_path.stat()
                    if stat.st_size > self.max_file_size:
                        logger.debug(
                            "skipping_large_file", 
                            path=str(file_path),
                            size_mb=stat.st_size / 1024 / 1024
                        )
                        skipped_files += 1
                        continue
                        
                    # Create FileInfo
                    file_info = FileInfo(
                        path=file_path,
                        relative_path=str(file_path.relative_to(root)),
                        size_bytes=stat.st_size,
                        modified_time=datetime.fromtimestamp(stat.st_mtime)
                    )
                    
                    total_files += 1
                    yield file_info
                    
                except Exception as e:
                    logger.error("error_reading_file", path=str(file_path), error=str(e))
                    skipped_files += 1
                    continue
        
        logger.info(
            "file_walk_completed", 
            total_files=total_files,
            skipped_files=skipped_files
        )
    
    def calculate_content_hash(self, file_info: FileInfo) -> str:
        """Calculate SHA256 hash of file content."""
        hasher = hashlib.sha256()
        try:
            with open(file_info.path, 'rb') as f:
                while chunk := f.read(8192):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except Exception as e:
            logger.error("error_hashing_file", path=str(file_info.path), error=str(e))
            raise