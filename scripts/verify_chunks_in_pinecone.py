"""
Script to verify chunks stored in Pinecone for a source.

Usage:
    python scripts/verify_chunks_in_pinecone.py <source_id> [tenant_id]
"""

import sys
import os
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from dotenv import load_dotenv
load_dotenv()

from config.settings import settings
from packages.core.rag.vectorstores.pinecone_store import PineconeVectorStore
from pinecone import Pinecone
import uuid


def verify_chunks(source_id: str, tenant_id: str = None):
    """Verify chunks in Pinecone for a source."""
    tenant_id = tenant_id or settings.DATABASE_URL.split('/')[-1] if settings.DATABASE_URL else "default"
    
    print(f"Verifying chunks for source: {source_id}")
    print(f"Tenant ID: {tenant_id}")
    print(f"Pinecone Index: {settings.PINECONE_INDEX_NAME}")
    print()
    
    # Initialize Pinecone
    pc = Pinecone(api_key=settings.PINECONE_API_KEY)
    index = pc.Index(settings.PINECONE_INDEX_NAME)
    
    # Get namespace
    namespace = str(uuid.UUID(tenant_id)) if tenant_id else "default"
    print(f"Namespace: {namespace}")
    print()
    
    # Query with filter to count chunks
    try:
        # Use a dummy query to get all chunks for this source
        # We'll use fetch with filter instead
        filter_dict = {"source_id": source_id}
        
        # Query with a dummy vector (all zeros) to get matches
        # But better: use list operation if available, or query with high top_k
        dummy_vector = [0.0] * settings.OPENAI_EMBEDDING_DIMENSIONS
        
        print(f"Querying Pinecone with filter: {filter_dict}")
        results = index.query(
            vector=dummy_vector,
            top_k=10000,  # High number to get all chunks
            include_metadata=True,
            namespace=namespace,
            filter=filter_dict
        )
        
        matches = results.get("matches", [])
        print(f"Found {len(matches)} chunks in Pinecone")
        print()
        
        if matches:
            print("Sample chunks:")
            for i, match in enumerate(matches[:5]):
                chunk_id = match.get("id", "N/A")
                score = match.get("score", 0)
                metadata = match.get("metadata", {})
                text_preview = metadata.get("text", "")[:100] if metadata.get("text") else "N/A"
                print(f"  {i+1}. ID: {chunk_id}, Score: {score:.4f}")
                print(f"     Text preview: {text_preview}...")
                print()
        else:
            print("WARNING: No chunks found in Pinecone!")
            print("This could mean:")
            print("  1. Chunks were never indexed")
            print("  2. Chunks were deleted")
            print("  3. Source ID doesn't match")
            print("  4. Wrong namespace")
        
        return len(matches)
        
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/verify_chunks_in_pinecone.py <source_id> [tenant_id]")
        sys.exit(1)
    
    source_id = sys.argv[1]
    tenant_id = sys.argv[2] if len(sys.argv) > 2 else None
    
    count = verify_chunks(source_id, tenant_id)
    print(f"\nTotal chunks in Pinecone: {count}")
