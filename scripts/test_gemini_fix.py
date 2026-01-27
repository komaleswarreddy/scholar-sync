#!/usr/bin/env python3
"""
Test script to verify gemini-1.5-flash is properly intercepted
"""

import sys
import os
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_model_interception():
    """Test that gemini-1.5-flash is intercepted at all levels."""
    print("=" * 70)
    print("Testing Gemini Model Interception")
    print("=" * 70)
    
    try:
        from packages.core.llm.gemini_client import GeminiClient
        from packages.core.llm.factory import get_llm_client
        
        api_key = os.environ.get('GEMINI_API_KEY', 'test-key')
        
        print("\n[1/3] Testing direct GeminiClient with gemini-1.5-flash...")
        try:
            client = GeminiClient(model="gemini-1.5-flash", api_key=api_key)
            print(f"  ✓ Client created. Final model: {client.model}")
            assert "1.5-flash" not in client.model.lower() or "pro" in client.model.lower(), \
                f"Model should be upgraded, but got: {client.model}"
            assert client.model in ["gemini-2.0-flash-exp", "gemini-2.5-flash"], \
                f"Expected upgraded model, got: {client.model}"
        except Exception as e:
            print(f"  ✗ Failed: {e}")
            return False
        
        print("\n[2/3] Testing factory with gemini-1.5-flash...")
        try:
            client = get_llm_client(model="gemini-1.5-flash")
            print(f"  ✓ Client created. Final model: {client.model}")
            assert "1.5-flash" not in client.model.lower() or "pro" in client.model.lower(), \
                f"Model should be upgraded, but got: {client.model}"
        except Exception as e:
            print(f"  ✗ Failed: {e}")
            return False
        
        print("\n[3/3] Testing model property access...")
        try:
            client = GeminiClient(model="gemini-1.5-flash", api_key=api_key)
            # Access the model property - this should trigger interception
            _ = client.gemini_model
            print(f"  ✓ Model property accessed. Final model: {client.model}")
            assert "1.5-flash" not in client.model.lower() or "pro" in client.model.lower(), \
                f"Model should be upgraded, but got: {client.model}"
        except Exception as e:
            print(f"  ✗ Failed: {e}")
            return False
        
        print("\n" + "=" * 70)
        print("✅ All tests passed! gemini-1.5-flash is properly intercepted.")
        print("=" * 70)
        return True
        
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_model_interception()
    sys.exit(0 if success else 1)
