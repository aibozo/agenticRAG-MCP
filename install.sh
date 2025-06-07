#!/bin/bash

# AgenticRAG MCP Server Installation Script
# This script sets up the AgenticRAG MCP server with all dependencies

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}====================================${NC}"
echo -e "${BLUE}AgenticRAG MCP Server Installation${NC}"
echo -e "${BLUE}====================================${NC}"
echo

# Check Python version
echo -e "${YELLOW}Checking Python version...${NC}"
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}Error: Python 3 is not installed.${NC}"
    echo "Please install Python 3.8 or higher and try again."
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
REQUIRED_VERSION="3.8"

if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then
    echo -e "${RED}Error: Python $PYTHON_VERSION is too old.${NC}"
    echo "Please install Python 3.8 or higher and try again."
    exit 1
fi

echo -e "${GREEN}✓ Python $PYTHON_VERSION found${NC}"

# Create virtual environment
echo -e "\n${YELLOW}Creating virtual environment...${NC}"
if [ -d "venv" ]; then
    echo "Virtual environment already exists."
    read -p "Do you want to recreate it? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        rm -rf venv
        python3 -m venv venv
    fi
else
    python3 -m venv venv
fi
echo -e "${GREEN}✓ Virtual environment ready${NC}"

# Activate virtual environment
echo -e "\n${YELLOW}Activating virtual environment...${NC}"
source venv/bin/activate

# Upgrade pip
echo -e "\n${YELLOW}Upgrading pip...${NC}"
pip install --upgrade pip --quiet

# Install dependencies
echo -e "\n${YELLOW}Installing dependencies...${NC}"
echo "This may take a few minutes..."
pip install -r requirements.txt --quiet
echo -e "${GREEN}✓ Dependencies installed${NC}"

# Create necessary directories
echo -e "\n${YELLOW}Creating directories...${NC}"
mkdir -p chroma_db
mkdir -p logs
mkdir -p .mcp
echo -e "${GREEN}✓ Directories created${NC}"

# Set up .env file
echo -e "\n${YELLOW}Setting up environment variables...${NC}"
if [ -f ".env" ]; then
    echo ".env file already exists."
    read -p "Do you want to reconfigure it? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Keeping existing .env file."
    else
        cp .env .env.backup
        echo "Existing .env backed up to .env.backup"
        rm .env
    fi
fi

if [ ! -f ".env" ]; then
    echo -e "\n${BLUE}Please provide your API keys:${NC}"
    
    # Get OpenAI API key
    echo -n "Enter your OpenAI API key (required): "
    read -s OPENAI_KEY
    echo
    
    # Get Anthropic API key (optional)
    echo -n "Enter your Anthropic API key (optional, press Enter to skip): "
    read -s ANTHROPIC_KEY
    echo
    
    # Create .env file
    cat > .env << EOF
# API Keys
OPENAI_API_KEY=$OPENAI_KEY
ANTHROPIC_API_KEY=$ANTHROPIC_KEY

# Vector Database
CHROMA_PERSIST_DIRECTORY=./chroma_db

# Logging
LOG_LEVEL=INFO
LOG_FILE=./logs/agenticrag.log

# Model Configuration
DEFAULT_EMBEDDING_MODEL=text-embedding-3-large
DEFAULT_LLM_MODEL=gpt-4o
EOF
    
    echo -e "${GREEN}✓ Environment variables configured${NC}"
fi

# Test the installation
echo -e "\n${YELLOW}Testing installation...${NC}"
python3 << EOF
try:
    import chromadb
    import openai
    import tiktoken
    from dotenv import load_dotenv
    import os
    
    load_dotenv()
    
    if not os.getenv('OPENAI_API_KEY'):
        raise ValueError("OpenAI API key not found in .env file")
    
    print("All required packages imported successfully!")
except Exception as e:
    print(f"Error: {e}")
    exit(1)
EOF

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Installation test passed${NC}"
else
    echo -e "${RED}✗ Installation test failed${NC}"
    echo "Please check the error message above and try again."
    exit 1
fi

# Get the absolute path of the installation
INSTALL_PATH=$(pwd)

# Generate Claude configuration snippet
echo -e "\n${YELLOW}Generating Claude configuration...${NC}"
cat > claude_config_snippet.json << EOF
{
  "mcpServers": {
    "agenticrag": {
      "command": "python3",
      "args": [
        "$INSTALL_PATH/mcp_launcher.py"
      ]
    }
  }
}
EOF

echo -e "${GREEN}✓ Configuration snippet saved to claude_config_snippet.json${NC}"

# Print success message and next steps
echo
echo -e "${GREEN}====================================${NC}"
echo -e "${GREEN}Installation completed successfully!${NC}"
echo -e "${GREEN}====================================${NC}"
echo
echo -e "${BLUE}Next steps:${NC}"
echo "1. Add the MCP server to Claude:"
echo "   ${YELLOW}claude mcp add agenticrag python3 $INSTALL_PATH/mcp_launcher.py${NC}"
echo
echo "2. Or manually add to your Claude configuration:"
echo "   - macOS/Linux: ~/.config/claude/claude_desktop_config.json"
echo "   - Windows: %APPDATA%\\Claude\\claude_desktop_config.json"
echo "   - Copy the contents of claude_config_snippet.json"
echo
echo "3. Restart Claude to load the new MCP server"
echo
echo -e "${BLUE}Available tools:${NC}"
echo "   - init_repo: Index a repository for semantic search"
echo "   - search_repo: Search indexed repositories using AI"
echo "   - get_repo_stats: Get statistics for indexed repositories"
echo
echo -e "${GREEN}Happy coding! 🚀${NC}"