# AgenticRAG MCP Server

An intelligent codebase processing server that provides agentic RAG (Retrieval-Augmented Generation) capabilities through the Model Context Protocol (MCP).

## Features

- **Intelligent Code Indexing**: Automatically chunks and embeds codebases for semantic search
- **Agentic Retrieval**: Self-critiquing retrieval loop that ensures comprehensive context
- **Multi-Model Architecture**: Uses GPT-4o for retrieval and Claude 3 for planning
- **Live Updates**: File system watching for automatic re-indexing
- **Cost Control**: Built-in telemetry and budget management

## Quick Installation

### 1. Clone and Install

```bash
# Clone the repository
git clone https://github.com/yourusername/agenticrag-mcp.git
cd agenticrag-mcp

# Run the installation script
./install.sh
```

The install script will:
- Check Python version (3.8+ required)
- Create a virtual environment
- Install all dependencies
- Prompt for your API keys
- Create necessary directories
- Generate Claude configuration

### 2. Add to Claude

After installation, add AgenticRAG to Claude:

**Windows (Claude Desktop):**
1. Open `%APPDATA%\Claude\claude_desktop_config.json`
2. Add the configuration from `claude_config_snippet.json`

**macOS/Linux (Claude Desktop):**
1. Open `~/.config/claude/claude_desktop_config.json`
2. Add the configuration from `claude_config_snippet.json`

### 3. Restart Claude

Restart Claude to load the new MCP server.

## Manual Installation

If you prefer to install manually:

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy and configure environment
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY

# Add to Claude Desktop
claude mcp add agenticrag python3 /path/to/agenticrag-mcp/mcp_launcher.py
```

## Usage

Once installed, you can use these tools in Claude:

### Initialize a Repository
```
Please index the repository at /path/to/my/project as "myproject"
```

### Search Your Code
```
Search myproject for "how does authentication work?"
```

### Get Repository Statistics
```
Show me the stats for myproject
```

## Example Conversation

```
You: Can you index my FastAPI project at ~/projects/api?

Claude: I'll index your FastAPI project for you.
        [Calls init_repo tool]
        ✓ Successfully indexed repository 'api'
        - Total files: 47
        - Total chunks: 312
        - Total tokens: 52,841
        - Duration: 4.32 seconds

You: How does the authentication middleware work?

Claude: Let me search for information about the authentication middleware.
        [Calls search_repo tool]
        Based on my search, the authentication middleware in your FastAPI project:
        
        1. JWT Token Validation (auth/middleware.py, lines 15-45):
           - Validates Bearer tokens on protected routes
           - Extracts user claims from JWT payload
           - Returns 401 for invalid/expired tokens
        
        2. User Context (auth/middleware.py, lines 50-72):
           - Adds user object to request state
           - Enables access via request.state.user
        
        The middleware is registered in main.py on line 23.
```

## Configuration

### Required Environment Variables
```bash
# .env file
OPENAI_API_KEY=sk-...        # Required for embeddings and GPT-4
ANTHROPIC_API_KEY=sk-ant-... # Optional, for Claude models
```

### Optional Configuration
```bash
# Vector Database
CHROMA_PERSIST_DIRECTORY=./chroma_db

# Logging
LOG_LEVEL=INFO
LOG_FILE=./logs/agenticrag.log

# Models
DEFAULT_EMBEDDING_MODEL=text-embedding-3-large
DEFAULT_LLM_MODEL=gpt-4o
```

## Architecture

```
agenticrag-mcp/
├── src/
│   ├── agents/          # Agentic RAG implementation
│   │   ├── base.py      # Base agent class
│   │   ├── retriever.py # Self-evaluating retriever
│   │   ├── compressor.py # Result compression
│   │   └── workflow.py  # LangGraph orchestration
│   ├── indexing/        # Code indexing pipeline
│   │   ├── chunker.py   # Semantic code chunking
│   │   ├── embedder.py  # OpenAI embeddings
│   │   └── indexer.py   # Repository indexer
│   ├── storage/         # Vector storage
│   │   └── vector_store.py # ChromaDB interface
│   └── mcp_server.py    # MCP server implementation
├── mcp_launcher.py      # MCP entry point
├── install.sh           # Installation script
└── requirements.txt     # Python dependencies
```

## How It Works

1. **Indexing**: The system chunks your code respecting language boundaries and creates embeddings
2. **Retrieval**: When you search, an AI agent generates optimized queries and retrieves relevant chunks
3. **Self-Evaluation**: The agent evaluates if it has enough context and can perform additional searches
4. **Compression**: Results are intelligently summarized to provide clear, actionable answers

## Troubleshooting

### "No module named 'chromadb'"
Activate the virtual environment:
```bash
source venv/bin/activate
```

### "OpenAI API key not found"
Make sure your `.env` file contains:
```bash
OPENAI_API_KEY=your-key-here
```

### "MCP server not found in Claude"
1. Ensure you've added the configuration to Claude's config file
2. Restart Claude Desktop completely
3. Check the logs in `./logs/agenticrag.log`

### Search returns no results
Ensure you've indexed the repository first using the init_repo tool.

## Development

### Running Tests
```bash
source venv/bin/activate
python -m pytest tests/
```

### Local Testing
```bash
# Test indexing
python test_indexing.py

# Test agentic RAG
python test_agentic_rag.py
```

## Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Acknowledgments

- Built for [Claude Desktop](https://claude.ai) using the [Model Context Protocol](https://github.com/anthropics/mcp)
- Uses [ChromaDB](https://www.trychroma.com/) for vector storage
- Powered by [OpenAI](https://openai.com/) embeddings and [LangGraph](https://github.com/langchain-ai/langgraph)

If you prefer manual installation:

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy and configure environment
cp .env.example .env
# Edit .env with your API keys
```

## Usage

Once installed, you can use these tools in Claude:

### Index a Repository
```
Use the init_repo tool to index a codebase:
- path: /path/to/your/project
- repo_name: my-project
```

### Search Code
```
Use the search_repo tool to find relevant code:
- query: "How does the authentication system work?"
- repo_name: my-project
```

### Get Statistics
```
Use the get_repo_stats tool to see indexing statistics:
- repo_name: my-project
```

## Example Conversation

```
User: Index my Python project at /home/user/myproject

Claude: I'll index your Python project for semantic search.
[Uses init_repo tool with path="/home/user/myproject" and repo_name="myproject"]

User: Find all the database connection code

Claude: I'll search for database connection code in your project.
[Uses search_repo tool with query="database connection" and repo_name="myproject"]
[Returns relevant code snippets with file paths and explanations]
```

## Configuration

The server can be configured via environment variables in `.env`:

```bash
# API Keys (required)
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...

# Optional configurations
CHUNK_SIZE_TOKENS=1280        # Size of code chunks
MAX_FILE_SIZE_MB=2           # Maximum file size to index
DAILY_BUDGET_USD=100         # Cost control limit
```

## Troubleshooting

### Module Not Found
- Ensure virtual environment is activated: `source venv/bin/activate`
- Check installation: `pip list | grep agenticrag`

### API Key Errors
- Verify keys in `.env` file
- Ensure no extra spaces or quotes around keys
- Check key permissions for required models

### Claude Can't Find Tools
- Verify configuration path is absolute, not relative
- Check Claude logs: Help → Show Logs
- Ensure MCP server section exists in config

### Server Won't Start
- Check Python version: `python3 --version` (need 3.8+)
- Verify Redis is running: `redis-cli ping`
- Check port availability: `lsof -i:8000`

### Performance Issues
- Adjust `CHUNK_SIZE_TOKENS` for your codebase
- Increase `EMBEDDING_BATCH_SIZE` for faster indexing
- Monitor costs with `get_repo_stats` tool

## Development

### Running Tests
```bash
# Activate virtual environment
source venv/bin/activate

# Run all tests
pytest

# Run with coverage
pytest --cov=src
```

### Code Formatting
```bash
# Format code
black src tests

# Lint code
ruff check src tests
```

### Project Structure
```
agenticrag-mcp/
├── src/                    # Source code
│   ├── agents/            # AI agents
│   ├── api/              # API endpoints
│   ├── indexing/         # Code indexing
│   └── storage/          # Vector storage
├── tests/                 # Test files
├── install.sh            # Installation script
├── requirements.txt      # Dependencies
└── .env.example         # Environment template
```

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature-name`
3. Make your changes and test
4. Submit a pull request

## License

MIT License - see LICENSE file for details

## Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/agenticrag-mcp/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/agenticrag-mcp/discussions)
- **Documentation**: [Wiki](https://github.com/yourusername/agenticrag-mcp/wiki)