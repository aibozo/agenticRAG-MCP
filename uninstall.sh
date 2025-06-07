#!/bin/bash

# AgenticRAG MCP Server Uninstallation Script

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}====================================${NC}"
echo -e "${BLUE}AgenticRAG MCP Server Uninstallation${NC}"
echo -e "${BLUE}====================================${NC}"
echo

# Confirm uninstallation
echo -e "${YELLOW}This will remove the AgenticRAG MCP server installation.${NC}"
echo -e "${YELLOW}Your indexed data in chroma_db/ will be preserved.${NC}"
echo
read -p "Are you sure you want to uninstall? (y/N) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Uninstallation cancelled."
    exit 0
fi

# Remove virtual environment
if [ -d "venv" ]; then
    echo -e "\n${YELLOW}Removing virtual environment...${NC}"
    rm -rf venv
    echo -e "${GREEN}✓ Virtual environment removed${NC}"
fi

# Ask about data removal
echo
read -p "Do you want to remove indexed data (chroma_db)? (y/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    if [ -d "chroma_db" ]; then
        echo -e "${YELLOW}Removing indexed data...${NC}"
        rm -rf chroma_db
        echo -e "${GREEN}✓ Indexed data removed${NC}"
    fi
fi

# Ask about log removal
read -p "Do you want to remove logs? (y/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    if [ -d "logs" ]; then
        echo -e "${YELLOW}Removing logs...${NC}"
        rm -rf logs
        echo -e "${GREEN}✓ Logs removed${NC}"
    fi
fi

# Ask about config removal
read -p "Do you want to remove configuration files (.env, .mcp)? (y/N) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    if [ -f ".env" ]; then
        echo -e "${YELLOW}Removing .env file...${NC}"
        rm -f .env
        echo -e "${GREEN}✓ .env file removed${NC}"
    fi
    if [ -d ".mcp" ]; then
        echo -e "${YELLOW}Removing .mcp directory...${NC}"
        rm -rf .mcp
        echo -e "${GREEN}✓ .mcp directory removed${NC}"
    fi
fi

# Remove generated files
if [ -f "claude_config_snippet.json" ]; then
    rm -f claude_config_snippet.json
fi

echo
echo -e "${GREEN}====================================${NC}"
echo -e "${GREEN}Uninstallation completed${NC}"
echo -e "${GREEN}====================================${NC}"
echo
echo -e "${BLUE}Next steps:${NC}"
echo "1. Remove the MCP server from Claude:"
echo "   ${YELLOW}claude mcp remove agenticrag${NC}"
echo
echo "2. Or manually remove from Claude configuration:"
echo "   - macOS/Linux: ~/.config/claude/claude_desktop_config.json"
echo "   - Windows: %APPDATA%\\Claude\\claude_desktop_config.json"
echo
echo "3. Delete the agenticrag-mcp directory if no longer needed"
echo
echo -e "${BLUE}Thank you for using AgenticRAG!${NC}"