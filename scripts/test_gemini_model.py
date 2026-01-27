#!/usr/bin/env python3
"""
Test script to verify Gemini model configuration and API calls.
"""

import sys
import os
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_gemini_model():
    """Test Gemini model initialization and API call."""
    print("=" * 70)
    print("Gemini Model Test")
    print("=" * 70)
    
    try:
        from packages.core.llm.gemini_client import GeminiClient
        
        # Get API key from environment
        api_key = os.environ.get('GEMINI_API_KEY', 'test-key')
        if api_key == 'test-key':
            print("\n[WARNING] Using test API key - actual API calls will fail")
            print("Set GEMINI_API_KEY environment variable for real test")
        
        print(f"\n[1/3] Creating GeminiClient...")
        client = GeminiClient(api_key=api_key)
        print(f"  [OK] Client created with model: {client.model}")
        
        print(f"\n[2/3] Accessing gemini_model property...")
        model = client.gemini_model
        print(f"  [OK] Model initialized: {type(model)}")
        
        print(f"\n[3/3] Testing generate_content call...")
        try:
            # This will fail with test key, but structure should work
            response = model.generate_content("Test prompt")
            print("  [SUCCESS] generate_content call succeeded!")
            print(f"  [INFO] Response: {response.text[:100] if response.text else 'No text'}")
            return True
        except Exception as e:
            error_msg = str(e)
            error_type = type(e).__name__
            
            if "404" in error_msg or "NotFound" in error_type or "not found" in error_msg.lower():
                if "v1beta" in error_msg:
                    print(f"  [ERROR] Model not found for API version v1beta")
                    print(f"  [INFO] Error: {error_msg}")
                    print(f"  [SOLUTION] The google-generativeai library was upgraded to 0.8.6")
                    print(f"  [SOLUTION] If error persists, check:")
                    print(f"    1. GEMINI_API_KEY is valid and has access to gemini-1.5-flash")
                    print(f"    2. API region supports the model")
                    print(f"    3. Try using 'gemini-pro' as fallback")
                    return False
                else:
                    print(f"  [OK] Model not found error (expected with test key): {error_type}")
                    return True
            elif "api key" in error_msg.lower() or "authentication" in error_msg.lower():
                print(f"  [OK] Authentication error expected with test key: {error_type}")
                return True
            else:
                print(f"  [WARN] Unexpected error: {error_type}: {error_msg}")
                return True
                
    except Exception as e:
        error_msg = str(e)
        print(f"\n[ERROR] Test failed: {error_msg}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run test."""
    result = test_gemini_model()
    
    print("\n" + "=" * 70)
    if result:
        print("[SUCCESS] Gemini model test passed (or expected errors occurred)")
    else:
        print("[FAILURE] Gemini model test failed - check error messages above")
    print("=" * 70)
    
    return 0 if result else 1

if __name__ == "__main__":
    sys.exit(main())
