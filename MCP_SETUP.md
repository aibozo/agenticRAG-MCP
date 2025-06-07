# MCP Setup for AgenticRAG

## Installation

1. Clone the repository and set up the environment:
```bash
git clone <your-repo-url> agenticrag
cd agenticrag
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

2. Configure your API keys:
```bash
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY and ANTHROPIC_API_KEY
```

## Claude Desktop Configuration

Add this to your Claude Desktop configuration file:

### Windows
Location: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "agenticrag": {
      "command": "python",
      "args": [
        "C:\\path\\to\\agenticrag\\mcp_launcher.py"
      ],
      "env": {
        "OPENAI_API_KEY": "your-openai-api-key",
        "ANTHROPIC_API_KEY": "your-anthropic-api-key"
      }
    }
  }
}
```

### macOS/Linux
Location: `~/.config/claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "agenticrag": {
      "command": "python3",
      "args": [
        "/home/username/agenticrag/mcp_launcher.py"
      ],
      "env": {
        "OPENAI_API_KEY": "your-openai-api-key",
        "ANTHROPIC_API_KEY": "your-anthropic-api-key"
      }
    }
  }
}
```

## Claude Code Configuration

For Claude Code, add to your configuration:

```json
{
  "mcpServers": {
    "agenticrag": {
      "command": "python3",
      "args": [
        "/home/riley/Programming/agenticRAG/mcp_launcher.py"
      ],
      "env": {
        "OPENAI_API_KEY": "sk-...",
        "ANTHROPIC_API_KEY": "sk-ant-..."
      }
    }
  }
}
```

## Available Tools

Once configured, Claude will have access to these tools:

### `init_repo`
Index a repository for semantic search.
```
Parameters:
- path: Absolute path to the repository
- repo_name: Name for the repository index
- ignore_globs: (optional) Additional patterns to ignore
```

### `search_repo`
Search an indexed repository (coming in Phase C).
```
Parameters:
- query: Natural language search query
- repo_name: Name of the repository to search
- k: (optional) Number of results to return
```

### `get_repo_stats`
Get statistics for an indexed repository.
```
Parameters:
- repo_name: Name of the repository
```

## Testing

To test the MCP server manually:
```bash
# Start the server
python mcp_launcher.py

# In another terminal, send a test request
echo '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}' | python mcp_launcher.py
```

## Troubleshooting

1. **Module not found errors**: Make sure you're in the project directory and the virtual environment is activated.

2. **API key errors**: Ensure your API keys are set in the environment variables or .env file.

3. **Permission errors**: Make sure the launcher script is executable:
   ```bash
   chmod +x mcp_launcher.py
   ```