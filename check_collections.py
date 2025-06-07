#!/usr/bin/env python3
"""Check available collections in ChromaDB."""

import chromadb
from chromadb.config import Settings as ChromaSettings
from dotenv import load_dotenv

load_dotenv()

# Initialize ChromaDB client
client = chromadb.PersistentClient(
    path="./chroma_db",
    settings=ChromaSettings(
        anonymized_telemetry=False,
        allow_reset=False
    )
)

# List collections
collections = client.list_collections()
print(f"Found {len(collections)} collections:")
for collection_name in collections:
    # In newer ChromaDB, list_collections returns just names
    try:
        # Get the actual collection to access its properties
        col = client.get_collection(collection_name)
        print(f"  - {collection_name} (count: {col.count()})")
    except Exception as e:
        print(f"  - {collection_name} (error: {e})")

if not collections:
    print("\nNo collections found. You need to index a repository first.")
    print("Run: python test_indexing.py")