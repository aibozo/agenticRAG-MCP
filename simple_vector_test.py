#!/usr/bin/env python3
"""Simple test to verify vector store contents."""

import chromadb
from chromadb.config import Settings as ChromaSettings

# Initialize ChromaDB client
client = chromadb.PersistentClient(
    path="./chroma_db",
    settings=ChromaSettings(
        anonymized_telemetry=False,
        allow_reset=False
    )
)

# Try to get the agenticrag_test collection
try:
    collection = client.get_collection("agenticrag_test")
    print(f"Collection 'agenticrag_test' found!")
    print(f"Number of documents: {collection.count()}")
    
    # Get a sample of documents
    results = collection.get(limit=5)
    print(f"\nFirst few documents:")
    for i, (id, doc) in enumerate(zip(results['ids'], results['documents'])):
        print(f"{i+1}. ID: {id[:50]}...")
        print(f"   Content preview: {doc[:100]}...")
        if results['metadatas'] and i < len(results['metadatas']):
            meta = results['metadatas'][i]
            print(f"   File: {meta.get('file_path', 'N/A')}")
        print()
        
except Exception as e:
    print(f"Error: {e}")