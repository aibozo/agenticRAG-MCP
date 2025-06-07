#!/bin/bash
# Development setup script for AgenticRAG without Docker

echo "Setting up AgenticRAG development environment..."

# Create necessary directories
mkdir -p chroma_db logs data

# Check if Redis is installed
if ! command -v redis-server &> /dev/null; then
    echo "Redis is not installed. On Ubuntu/Debian, install with:"
    echo "  sudo apt-get update && sudo apt-get install redis-server"
    echo "On macOS with Homebrew:"
    echo "  brew install redis"
    exit 1
fi

# Create Python virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies
echo "Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Copy .env.example to .env if it doesn't exist
if [ ! -f ".env" ]; then
    echo "Creating .env file from template..."
    cp .env.example .env
    echo ""
    echo "⚠️  IMPORTANT: Edit .env file and add your API keys:"
    echo "  - OPENAI_API_KEY"
    echo "  - ANTHROPIC_API_KEY"
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "To start the development environment:"
echo "1. In terminal 1: redis-server"
echo "2. In terminal 2: source venv/bin/activate && python -m src.main"
echo "3. In terminal 3: source venv/bin/activate && python -m src.run_worker"