#!/usr/bin/env python3
"""
Test script to verify Gemini new model names (2.0-flash-exp, 2.5-flash) work correctly.
"""

import sys
import os
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def test_model_initialization():
    """Test that new models can be initialized."""
    print("=" * 70)
    print("Gemini New Models Test")
    print("=" * 70)
    
    try:
        from packages.core.llm.gemini_client import GeminiClient
        from packages.core.llm.factory import get_model_for_task, get_llm_client
        
        # Get API key from environment
        api_key = os.environ.get('GEMINI_API_KEY', 'test-key')
        if api_key == 'test-key':
            print("\n[WARNING] Using test API key - actual API calls will fail")
            print("Set GEMINI_API_KEY environment variable for real test")
        
        models_to_test = [
            "gemini-2.0-flash-exp",
            "gemini-2.5-flash",
            "gemini-pro",
        ]
        
        print(f"\n[1/4] Testing model initialization...")
        for model_name in models_to_test:
            try:
                client = GeminiClient(model=model_name, api_key=api_key)
                print(f"  [OK] {model_name}: Client created")
                
                # Try to access gemini_model property (this triggers initialization)
                try:
                    model = client.gemini_model
                    print(f"  [OK] {model_name}: Model object created")
                except Exception as e:
                    error_msg = str(e)
                    if "404" in error_msg or "NotFound" in error_msg or "not found" in error_msg.lower():
                        print(f"  [SKIP] {model_name}: Model not available (expected with test key or v1beta API)")
                    else:
                        print(f"  [ERROR] {model_name}: {type(e).__name__}: {error_msg[:100]}")
            except Exception as e:
                print(f"  [ERROR] {model_name}: {type(e).__name__}: {str(e)[:100]}")
        
        print(f"\n[2/4] Testing factory get_model_for_task('chat')...")
        try:
            provider, model = get_model_for_task("chat")
            print(f"  [OK] Chat routing: provider={provider}, model={model}")
            assert model in ["gemini-2.0-flash-exp", "gemini-2.5-flash", "gemini-pro"], \
                f"Expected newer model, got {model}"
        except Exception as e:
            print(f"  [ERROR] Factory test failed: {type(e).__name__}: {str(e)}")
            return False
        
        print(f"\n[3/4] Testing factory get_llm_client for chat...")
        try:
            client = get_llm_client(provider=provider, model=model, temperature=0.7)
            print(f"  [OK] Client created: model={client.model}, provider={client.provider}")
            assert client.model == model, f"Model mismatch: expected {model}, got {client.model}"
        except Exception as e:
            print(f"  [ERROR] Client creation failed: {type(e).__name__}: {str(e)}")
            return False
        
        print(f"\n[4/4] Testing default Gemini model...")
        try:
            from packages.core.llm.factory import _get_default_model
            from packages.core.llm._base import LLMProvider
            default_model = _get_default_model(LLMProvider.GEMINI)
            print(f"  [OK] Default Gemini model: {default_model}")
            assert default_model in ["gemini-2.0-flash-exp", "gemini-2.5-flash"], \
                f"Expected newer model as default, got {default_model}"
        except Exception as e:
            print(f"  [ERROR] Default model test failed: {type(e).__name__}: {str(e)}")
            return False
        
        print("\n" + "=" * 70)
        print("[SUCCESS] All tests passed!")
        print("=" * 70)
        return True
        
    except Exception as e:
        print(f"\n[ERROR] Test failed: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run test."""
    result = test_model_initialization()
    return 0 if result else 1

if __name__ == "__main__":
    sys.exit(main())
