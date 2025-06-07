#!/usr/bin/env python3
"""Launcher script for AgenticRAG MCP server."""

import os
import sys
import subprocess
from pathlib import Path
from dotenv import load_dotenv

# Get the directory where this script is located
SCRIPT_DIR = Path(__file__).parent.absolute()

# Load environment variables from .env file
env_path = SCRIPT_DIR / '.env'
if env_path.exists():
    load_dotenv(env_path)

# Check if we're in a virtual environment
if not hasattr(sys, 'real_prefix') and not (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
    # Not in a virtual environment, try to activate one
    venv_path = SCRIPT_DIR / "venv"
    if venv_path.exists():
        # Use the Python from the virtual environment
        python_path = venv_path / "bin" / "python" if os.name != 'nt' else venv_path / "Scripts" / "python.exe"
        if python_path.exists():
            # Re-run this script with the virtual environment Python
            os.execv(str(python_path), [str(python_path)] + sys.argv)

# Add the project root to Python path
sys.path.insert(0, str(SCRIPT_DIR))

# Import and run the MCP server
from src.mcp_server import main
import asyncio

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        sys.exit(0)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)