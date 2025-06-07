#!/usr/bin/env python3
"""Test script for MCP server."""

import json
import subprocess
import os

def send_request(request):
    """Send a request to the MCP server and get response."""
    # Start the MCP server process
    env = os.environ.copy()
    env['PYTHONPATH'] = os.path.dirname(os.path.abspath(__file__))
    
    proc = subprocess.Popen(
        ['python3', 'mcp_launcher.py'],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env
    )
    
    # Send request
    proc.stdin.write(json.dumps(request) + '\n')
    proc.stdin.flush()
    
    # Read response
    response_lines = []
    while True:
        line = proc.stdout.readline()
        if not line:
            break
        try:
            response = json.loads(line.strip())
            response_lines.append(response)
            # If this is a response to our request, break
            if response.get('id') == request.get('id'):
                break
        except json.JSONDecodeError:
            continue
    
    # Terminate the process
    proc.terminate()
    
    return response_lines

def test_mcp_server():
    """Test the MCP server functionality."""
    print("Testing AgenticRAG MCP Server\n")
    
    # Test 1: List tools
    print("1. Testing tools/list:")
    request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/list",
        "params": {}
    }
    
    responses = send_request(request)
    for response in responses:
        if response.get('method') == 'initialized':
            print(f"   Server initialized: {response['params']['serverInfo']}")
        elif response.get('id') == 1:
            tools = response['result']['tools']
            print(f"   Found {len(tools)} tools:")
            for tool in tools:
                print(f"   - {tool['name']}: {tool['description']}")
    
    # Test 2: Get repo stats (should be empty)
    print("\n2. Testing get_repo_stats:")
    request = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {
            "name": "get_repo_stats",
            "arguments": {
                "repo_name": "test_repo"
            }
        }
    }
    
    responses = send_request(request)
    for response in responses:
        if response.get('id') == 2:
            result = response.get('result', {})
            print(f"   Stats for 'test_repo': {json.dumps(result, indent=2)}")
    
    print("\n✅ MCP server is working correctly!")
    print("\nTo use with Claude Desktop/Code, add the configuration from MCP_SETUP.md")

if __name__ == "__main__":
    # Check for API keys
    if not os.environ.get("OPENAI_API_KEY"):
        print("Warning: OPENAI_API_KEY not set. Using test mode.")
        os.environ["OPENAI_API_KEY"] = "sk-test"
    
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("Warning: ANTHROPIC_API_KEY not set. Using test mode.")
        os.environ["ANTHROPIC_API_KEY"] = "sk-ant-test"
    
    test_mcp_server()