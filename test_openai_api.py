#!/usr/bin/env python3
"""Test OpenAI API connection and available models."""

import os
from dotenv import load_dotenv
import openai

# Load environment
load_dotenv()

api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    print("Error: OPENAI_API_KEY not found in environment")
    exit(1)

print(f"API Key: {api_key[:10]}...{api_key[-4:]}")

# Initialize client
client = openai.Client(api_key=api_key)

# Test 1: List available models
print("\n=== Available Models ===")
try:
    models = client.models.list()
    gpt_models = [m.id for m in models if 'gpt' in m.id]
    print("GPT Models:")
    for model in sorted(gpt_models):
        print(f"  - {model}")
except Exception as e:
    print(f"Error listing models: {e}")

# Test 2: Try a simple chat completion
print("\n=== Testing Chat Completion ===")
try:
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",  # Use the cheapest model for testing
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Say 'API is working!' in 5 words or less."}
        ],
        max_tokens=20,
        temperature=0
    )
    print(f"Response: {response.choices[0].message.content}")
    print(f"Tokens used: {response.usage.total_tokens}")
except Exception as e:
    print(f"Error with chat completion: {e}")

# Test 3: Try embeddings
print("\n=== Testing Embeddings ===")
try:
    response = client.embeddings.create(
        model="text-embedding-3-small",  # Use small model for testing
        input="Test embedding"
    )
    print(f"Embedding dimensions: {len(response.data[0].embedding)}")
    print(f"Tokens used: {response.usage.total_tokens}")
except Exception as e:
    print(f"Error with embeddings: {e}")

print("\n=== API Test Complete ===")