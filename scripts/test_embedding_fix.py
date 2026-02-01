"""
Test script to verify the OpenAI embedding client fix.
This tests that the httpx client is created correctly without proxies errors.
"""

import os
import sys
import asyncio

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

async def test_embedding_client():
    """Test that the OpenAI embedding client can be created without proxies error."""
    print("=" * 70)
    print("Testing OpenAI Embedding Client Fix")
    print("=" * 70)
    
    try:
        from config.settings import settings
        from packages.core.rag.vectorstores.pinecone_store import PineconeVectorStore
        
        print("\n[1] Checking API key...")
        if not settings.OPENAI_API_KEY or settings.OPENAI_API_KEY == "your-openai-api-key":
            print("   [ERROR] OPENAI_API_KEY not configured")
            return False
        print("   [OK] API key is set")
        
        print("\n[2] Testing PineconeVectorStore client initialization...")
        store = PineconeVectorStore(tenant_id="test-tenant")
        
        # This should trigger the openai_client property
        print("   Accessing openai_client property...")
        client = store.openai_client
        print("   [OK] OpenAI client created successfully!")
        
        print("\n[3] Testing embedding generation...")
        test_text = "This is a test sentence for embedding generation."
        embedding = await store.generate_embedding(test_text)
        
        if embedding and len(embedding) > 0:
            print(f"   [OK] Successfully generated embedding (dimension: {len(embedding)})")
            return True
        else:
            print("   [ERROR] Embedding generation returned empty result")
            return False
            
    except ValueError as e:
        error_msg = str(e)
        print(f"\n   [ERROR] ValueError: {error_msg}")
        if "proxies" in error_msg.lower():
            print("\n   *** PROXIES ERROR DETECTED ***")
            print("   The fix may not be working. Please check:")
            print("   1. Is the server restarted?")
            print("   2. Are you using the correct virtual environment?")
            print("   3. Check the debug output in the logs above")
        return False
    except Exception as e:
        error_type = type(e).__name__
        error_msg = str(e)
        print(f"\n   [ERROR] {error_type}: {error_msg}")
        import traceback
        print("\n   Full traceback:")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_embedding_client())
    print("\n" + "=" * 70)
    if success:
        print("✅ Test PASSED - Embedding client is working correctly!")
    else:
        print("❌ Test FAILED - Please check the errors above")
    print("=" * 70)
    sys.exit(0 if success else 1)
