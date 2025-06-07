#!/bin/bash

# Quick start script for AgenticRAG MCP Server

# Colors
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}Starting AgenticRAG MCP Server...${NC}"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Virtual environment not found. Please run ./install.sh first.${NC}"
    exit 1
fi

# Activate virtual environment
source venv/bin/activate

# Check if .env exists
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}.env file not found. Please run ./install.sh first.${NC}"
    exit 1
fi

# Get the absolute path
INSTALL_PATH=$(pwd)

echo -e "${GREEN}AgenticRAG is ready!${NC}"
echo
echo -e "${BLUE}To use with Claude:${NC}"
echo "1. If not already added, run:"
echo "   ${YELLOW}claude mcp add agenticrag python3 $INSTALL_PATH/mcp_launcher.py${NC}"
echo
echo "2. Restart Claude to load the MCP server"
echo
echo -e "${BLUE}Available commands in Claude:${NC}"
echo "   - Index a repo: 'Please index /path/to/repo as \"myrepo\"'"
echo "   - Search code: 'Search myrepo for authentication logic'"
echo "   - Get stats: 'Show stats for myrepo'"
echo
echo -e "${GREEN}Happy coding! 🚀${NC}"