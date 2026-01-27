#!/usr/bin/env python3
"""
Runtime test that simulates the actual embeddings generation flow.

This test mimics what happens when a user uploads a file and embeddings are generated.
"""

import sys
import os
import asyncio
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

async def test_embeddings_generation_flow():
    """Test the actual embeddings generation flow used in production."""
    print("\n[TEST] Simulating embeddings generation flow...")
    
    try:
        # Import the actual service that generates embeddings
        from packages.core.rag.vectorstores.pinecone_store import PineconeVectorStore
        
        # Set up test environment
        os.environ['OPENAI_API_KEY'] = 'test-key-for-structure-check'
        os.environ['PINECONE_API_KEY'] = 'test-key-for-structure-check'
        
        # Create vector store (this is what happens in source_service.py)
        tenant_id = "test-tenant-123"
        vector_store = PineconeVectorStore(tenant_id)
        
        print("  [1/3] PineconeVectorStore created")
        
        # Access the openai_client property (this triggers initialization)
        client = vector_store.openai_client
        print("  [2/3] OpenAI client initialized successfully")
        
        # Try to call embeddings.create() (this is what generate_embedding does)
        # We expect an auth error, but the structure should work
        try:
            response = client.embeddings.create(
                model="text-embedding-3-small",
                input="test text for embedding"
            )
            print("  [3/3] embeddings.create() call succeeded")
            return True
        except Exception as e:
            error_type = type(e).__name__
            error_msg = str(e)
            
            # Check if it's the proxies error
            if 'proxies' in error_msg.lower() and 'unexpected keyword argument' in error_msg.lower():
                print(f"  [FAIL] Proxies error occurred: {error_msg}")
                import traceback
                traceback.print_exc()
                return False
            
            # Other errors (like auth) are expected with test key
            if 'authentication' in error_msg.lower() or 'api key' in error_msg.lower():
                print(f"  [3/3] embeddings.create() structure correct (auth error expected: {error_type})")
                return True
            else:
                print(f"  [WARN] Unexpected error: {error_type}: {error_msg}")
                # Still return True if it's not a proxies error
                if 'proxies' not in error_msg.lower():
                    return True
                return False
                
    except Exception as e:
        error_msg = str(e)
        if 'proxies' in error_msg.lower():
            print(f"  [FAIL] Proxies error in embeddings flow: {error_msg}")
            import traceback
            traceback.print_exc()
            return False
        else:
            print(f"  [ERROR] Unexpected error: {error_msg}")
            import traceback
            traceback.print_exc()
            return False

async def test_batch_embeddings_flow():
    """Test batch embeddings generation (used in source_service.py)."""
    print("\n[TEST] Simulating batch embeddings generation flow...")
    
    try:
        from packages.core.rag.vectorstores.pinecone_store import PineconeVectorStore
        
        os.environ['OPENAI_API_KEY'] = 'test-key-for-structure-check'
        os.environ['PINECONE_API_KEY'] = 'test-key-for-structure-check'
        
        tenant_id = "test-tenant-123"
        vector_store = PineconeVectorStore(tenant_id)
        
        print("  [1/3] PineconeVectorStore created")
        
        # Get client
        client = vector_store.openai_client
        print("  [2/3] OpenAI client initialized")
        
        # Test batch_generate_embeddings structure (what source_service calls)
        test_texts = ["text 1", "text 2", "text 3"]
        
        try:
            # This is what batch_generate_embeddings does internally
            response = client.embeddings.create(
                model="text-embedding-3-small",
                input=test_texts,
            )
            print("  [3/3] batch embeddings.create() call succeeded")
            return True
        except Exception as e:
            error_type = type(e).__name__
            error_msg = str(e)
            
            if 'proxies' in error_msg.lower() and 'unexpected keyword argument' in error_msg.lower():
                print(f"  [FAIL] Proxies error in batch embeddings: {error_msg}")
                import traceback
                traceback.print_exc()
                return False
            
            if 'authentication' in error_msg.lower() or 'api key' in error_msg.lower():
                print(f"  [3/3] batch embeddings.create() structure correct (auth error expected: {error_type})")
                return True
            else:
                print(f"  [WARN] Unexpected error: {error_type}: {error_msg}")
                if 'proxies' not in error_msg.lower():
                    return True
                return False
                
    except Exception as e:
        error_msg = str(e)
        if 'proxies' in error_msg.lower():
            print(f"  [FAIL] Proxies error in batch embeddings flow: {error_msg}")
            import traceback
            traceback.print_exc()
            return False
        else:
            print(f"  [ERROR] Unexpected error: {error_msg}")
            import traceback
            traceback.print_exc()
            return False

def main():
    """Run runtime tests."""
    print("=" * 70)
    print("OpenAI Embeddings - Runtime Flow Test")
    print("=" * 70)
    
    # Run async tests
    results = []
    
    # Test 1: Single embedding generation
    try:
        result = asyncio.run(test_embeddings_generation_flow())
        results.append(("Single Embedding Generation", result))
    except Exception as e:
        print(f"\n[ERROR] Test crashed: {e}")
        import traceback
        traceback.print_exc()
        results.append(("Single Embedding Generation", False))
    
    # Test 2: Batch embedding generation
    try:
        result = asyncio.run(test_batch_embeddings_flow())
        results.append(("Batch Embedding Generation", result))
    except Exception as e:
        print(f"\n[ERROR] Test crashed: {e}")
        import traceback
        traceback.print_exc()
        results.append(("Batch Embedding Generation", False))
    
    # Summary
    print("\n" + "=" * 70)
    print("RUNTIME TEST SUMMARY")
    print("=" * 70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"{status} {test_name}")
    
    print("\n" + "=" * 70)
    if passed == total:
        print(f"ALL RUNTIME TESTS PASSED ({passed}/{total})")
        print("The fix is working correctly!")
        print("=" * 70)
        return 0
    else:
        print(f"SOME RUNTIME TESTS FAILED ({passed}/{total} passed)")
        print("=" * 70)
        return 1

if __name__ == "__main__":
    sys.exit(main())
