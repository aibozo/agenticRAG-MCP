#!/usr/bin/env python3
"""Test MCP protocol communication."""

import subprocess
import json
import sys

def send_request(proc, request):
    """Send a request and get response."""
    proc.stdin.write(json.dumps(request) + '\n')
    proc.stdin.flush()
    response_line = proc.stdout.readline()
    if response_line:
        return json.loads(response_line)
    return None

# Start the MCP server
proc = subprocess.Popen(
    ['./venv/bin/python', 'mcp_launcher.py'],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
    bufsize=1
)

try:
    # Send initialize
    init_request = {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}
    print("Sending:", init_request)
    response = send_request(proc, init_request)
    print("Response:", response)
    if response and 'result' in response:
        print("Protocol Version:", response['result'].get('protocolVersion'))
    
    # Send tools/list
    tools_request = {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
    print("\nSending:", tools_request)
    response = send_request(proc, tools_request)
    print("Response:", response)
    
finally:
    proc.terminate()