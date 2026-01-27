#!/usr/bin/env python3
"""
Test script that simulates the actual error scenario.

This will help identify if the error is still occurring.
"""

import sys
import os
import asyncio
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

async def test_actual_embeddings_call():
    """Test the actual embeddings call that would fail."""
    print("=" * 70)
    print("Testing Actual Embeddings Generation")
    print("=" * 70)
    
    try:
        # Import exactly what the source_service uses
        from packages.core.rag.vectorstores.pinecone_store import PineconeVectorStore
        
        # Set environment (use actual API key if available, otherwise test key)
        test_key = os.environ.get('OPENAI_API_KEY', 'test-key-12345')
        os.environ['OPENAI_API_KEY'] = test_key
        os.environ['PINECONE_API_KEY'] = os.environ.get('PINECONE_API_KEY', 'test-key-12345')
        
        print("\n[1/4] Creating PineconeVectorStore...")
        tenant_id = "test-tenant-123"
        vector_store = PineconeVectorStore(tenant_id)
        print("  [OK] Vector store created")
        
        print("\n[2/4] Accessing openai_client property...")
        client = vector_store.openai_client
        print("  [OK] OpenAI client retrieved")
        print(f"  [INFO] Client type: {type(client)}")
        
        print("\n[3/4] Calling embeddings.create()...")
        try:
            response = client.embeddings.create(
                model="text-embedding-3-small",
                input="This is a test text for embedding generation"
            )
            print("  [SUCCESS] Embeddings generated successfully!")
            print(f"  [INFO] Response type: {type(response)}")
            print(f"  [INFO] Embedding dimension: {len(response.data[0].embedding)}")
            return True
        except Exception as e:
            error_type = type(e).__name__
            error_msg = str(e)
            
            print(f"  [ERROR] Exception occurred: {error_type}")
            print(f"  [ERROR] Message: {error_msg}")
            
            # Check for proxies error specifically
            if 'proxies' in error_msg.lower() and 'unexpected keyword argument' in error_msg.lower():
                print("\n" + "=" * 70)
                print("[CRITICAL] PROXIES ERROR DETECTED!")
                print("=" * 70)
                print("The error is still occurring. This means:")
                print("1. The fix might not be applied correctly")
                print("2. There might be cached code being used")
                print("3. The server might not have reloaded")
                import traceback
                traceback.print_exc()
                return False
            else:
                # Other errors (like auth) are expected with test keys
                if 'authentication' in error_msg.lower() or 'api key' in error_msg.lower():
                    print("  [OK] Authentication error expected with test key")
                    print("  [OK] The structure is correct - no proxies error!")
                    return True
                else:
                    print(f"  [WARN] Unexpected error: {error_type}")
                    import traceback
                    traceback.print_exc()
                    return False
        
    except Exception as e:
        error_msg = str(e)
        if 'proxies' in error_msg.lower():
            print("\n" + "=" * 70)
            print("[CRITICAL] PROXIES ERROR DETECTED DURING INITIALIZATION!")
            print("=" * 70)
            import traceback
            traceback.print_exc()
            return False
        else:
            print(f"\n[ERROR] Unexpected error: {error_msg}")
            import traceback
            traceback.print_exc()
            return False

def main():
    """Run the test."""
    result = asyncio.run(test_actual_embeddings_call())
    
    print("\n" + "=" * 70)
    if result:
        print("[SUCCESS] No proxies error detected!")
        print("The fix is working correctly.")
    else:
        print("[FAILURE] Proxies error still occurring!")
        print("Please check:")
        print("1. Backend server has been restarted")
        print("2. Python cache has been cleared")
        print("3. Code files contain the fix")
    print("=" * 70)
    
    return 0 if result else 1

if __name__ == "__main__":
    sys.exit(main())
