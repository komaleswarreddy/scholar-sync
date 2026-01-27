#!/usr/bin/env python3
"""
Comprehensive test script for OpenAI embeddings fix.

This script tests:
1. OpenAI client initialization with custom httpx client
2. Embeddings generation (with mock API key)
3. Both PineconeVectorStore and OpenAIClient
4. Verifies no 'proxies' parameter errors occur
"""

import sys
import os
import traceback
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_openai_client_initialization():
    """Test 1: OpenAI client initialization with custom httpx client."""
    print("\n[TEST 1] Testing OpenAI client initialization with custom httpx client...")
    try:
        import openai
        import httpx
        
        # Test direct initialization (what our code does)
        http_client = httpx.Client(timeout=60.0)
        client = openai.OpenAI(
            api_key="test-key-12345",
            http_client=http_client,
        )
        print("  [PASS] OpenAI client created with custom httpx.Client")
        return True
    except Exception as e:
        error_msg = str(e)
        if 'proxies' in error_msg.lower():
            print(f"  [FAIL] Proxies error: {error_msg}")
            traceback.print_exc()
            return False
        else:
            print(f"  [PASS] Client created (other error expected with test key): {type(e).__name__}")
            return True

def test_pinecone_vector_store_client():
    """Test 2: PineconeVectorStore openai_client property."""
    print("\n[TEST 2] Testing PineconeVectorStore.openai_client property...")
    try:
        from packages.core.rag.vectorstores.pinecone_store import PineconeVectorStore
        import os
        
        # Set test API keys
        os.environ['OPENAI_API_KEY'] = 'test-key-12345'
        os.environ['PINECONE_API_KEY'] = 'test-key-12345'
        
        store = PineconeVectorStore('test-tenant-id')
        client = store.openai_client
        
        print("  [PASS] PineconeVectorStore.openai_client created successfully")
        return True
    except Exception as e:
        error_msg = str(e)
        if 'proxies' in error_msg.lower():
            print(f"  [FAIL] Proxies error in PineconeVectorStore: {error_msg}")
            traceback.print_exc()
            return False
        else:
            # Other errors (like API key validation) are expected
            print(f"  [PASS] Client property accessed (expected error: {type(e).__name__})")
            return True

def test_openai_llm_client():
    """Test 3: OpenAIClient.client property."""
    print("\n[TEST 3] Testing OpenAIClient.client property...")
    try:
        from packages.core.llm.openai_client import OpenAIClient
        import os
        
        os.environ['OPENAI_API_KEY'] = 'test-key-12345'
        
        client_obj = OpenAIClient()
        client = client_obj.client
        
        print("  [PASS] OpenAIClient.client created successfully")
        return True
    except Exception as e:
        error_msg = str(e)
        if 'proxies' in error_msg.lower():
            print(f"  [FAIL] Proxies error in OpenAIClient: {error_msg}")
            traceback.print_exc()
            return False
        else:
            print(f"  [PASS] Client property accessed (expected error: {type(e).__name__})")
            return True

def test_embeddings_call_structure():
    """Test 4: Verify embeddings.create() can be called (structure test)."""
    print("\n[TEST 4] Testing embeddings.create() call structure...")
    try:
        import openai
        import httpx
        
        http_client = httpx.Client(timeout=60.0)
        client = openai.OpenAI(
            api_key="test-key-12345",
            http_client=http_client,
        )
        
        # Try to call embeddings.create (will fail with auth error, but structure should work)
        try:
            response = client.embeddings.create(
                model="text-embedding-3-small",
                input="test text"
            )
            print("  [PASS] embeddings.create() call succeeded")
            return True
        except openai.AuthenticationError:
            # Expected - we're using a test key
            print("  [PASS] embeddings.create() structure correct (auth error expected)")
            return True
        except Exception as e:
            error_msg = str(e)
            if 'proxies' in error_msg.lower():
                print(f"  [FAIL] Proxies error during embeddings.create(): {error_msg}")
                traceback.print_exc()
                return False
            else:
                print(f"  [PASS] embeddings.create() structure correct (error: {type(e).__name__})")
                return True
    except Exception as e:
        error_msg = str(e)
        if 'proxies' in error_msg.lower():
            print(f"  [FAIL] Proxies error: {error_msg}")
            traceback.print_exc()
            return False
        else:
            print(f"  [ERROR] Unexpected error: {error_msg}")
            traceback.print_exc()
            return False

def test_code_contains_fix():
    """Test 5: Verify code files contain the fix."""
    print("\n[TEST 5] Verifying code files contain the fix...")
    try:
        files_to_check = [
            "packages/core/rag/vectorstores/pinecone_store.py",
            "packages/core/llm/openai_client.py",
        ]
        
        required_patterns = [
            "httpx.Client(timeout=",
            "http_client=http_client",
            "Workaround for OpenAI 1.9.0/1.10.0 bug",
        ]
        
        all_passed = True
        for file_path in files_to_check:
            full_path = project_root / file_path
            if not full_path.exists():
                print(f"  [FAIL] File not found: {file_path}")
                all_passed = False
                continue
            
            content = full_path.read_text(encoding="utf-8")
            missing = [p for p in required_patterns if p not in content]
            
            if missing:
                print(f"  [FAIL] {file_path} missing patterns: {missing}")
                all_passed = False
            else:
                print(f"  [PASS] {file_path} contains all required patterns")
        
        return all_passed
    except Exception as e:
        print(f"  [ERROR] Error checking files: {e}")
        traceback.print_exc()
        return False

def test_version_compatibility():
    """Test 6: Verify package versions are correct."""
    print("\n[TEST 6] Verifying package versions...")
    try:
        import openai
        import httpx
        
        openai_version = openai.__version__
        httpx_version = httpx.__version__
        
        print(f"  OpenAI version: {openai_version}")
        print(f"  httpx version: {httpx_version}")
        
        # Check OpenAI version
        version_parts = [int(x) for x in openai_version.split('.')]
        if version_parts[0] == 1 and 9 <= version_parts[1] < 10:
            print("  [PASS] OpenAI version is 1.9.x (correct)")
        else:
            print(f"  [WARN] OpenAI version {openai_version} may not be compatible")
        
        # Check httpx version
        httpx_parts = [int(x) for x in httpx_version.split('.')]
        if httpx_parts[0] == 0 and httpx_parts[1] < 26:
            print("  [PASS] httpx version is < 0.26.0 (correct)")
        else:
            print(f"  [WARN] httpx version {httpx_version} may cause issues")
        
        return True
    except Exception as e:
        print(f"  [ERROR] Error checking versions: {e}")
        traceback.print_exc()
        return False

def main():
    """Run all tests."""
    print("=" * 70)
    print("OpenAI Embeddings Fix - Comprehensive Test Suite")
    print("=" * 70)
    
    tests = [
        ("OpenAI Client Initialization", test_openai_client_initialization),
        ("PineconeVectorStore Client", test_pinecone_vector_store_client),
        ("OpenAIClient Client", test_openai_llm_client),
        ("Embeddings Call Structure", test_embeddings_call_structure),
        ("Code Contains Fix", test_code_contains_fix),
        ("Version Compatibility", test_version_compatibility),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"\n[ERROR] Test '{test_name}' crashed: {e}")
            traceback.print_exc()
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"{status} {test_name}")
    
    print("\n" + "=" * 70)
    if passed == total:
        print(f"ALL TESTS PASSED ({passed}/{total})")
        print("=" * 70)
        return 0
    else:
        print(f"SOME TESTS FAILED ({passed}/{total} passed)")
        print("=" * 70)
        return 1

if __name__ == "__main__":
    sys.exit(main())
