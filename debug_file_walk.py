#!/usr/bin/env python3
"""Debug file walk to see what's being ignored."""

import os
from pathlib import Path
from src.indexing.file_walker import FileWalker

# Test the file walker
walker = FileWalker(["*.pyc", "__pycache__", "venv", ".git", "chroma_db"])
root_path = Path(__file__).parent

print(f"Walking: {root_path}")
print(f"Ignore patterns: {walker.ignore_patterns}")

files = list(walker.walk(str(root_path)))
print(f"\nFound {len(files)} files")

if files:
    print("\nFirst 10 files:")
    for f in files[:10]:
        print(f"  - {f.relative_path} ({f.size} bytes)")
else:
    print("\nNo files found! Checking what's being ignored...")
    
    # Walk manually to debug
    for root, dirs, filenames in os.walk(root_path):
        # Skip hidden and ignored dirs
        dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['venv', '__pycache__', 'chroma_db']]
        
        for filename in filenames:
            if filename.endswith('.py'):
                full_path = os.path.join(root, filename)
                rel_path = os.path.relpath(full_path, root_path)
                print(f"  Found Python file: {rel_path}")
                
                # Check if it would be ignored
                file_info = walker._create_file_info(Path(full_path), root_path)
                if file_info:
                    print(f"    -> Would be included")
                else:
                    print(f"    -> Would be ignored")