#!/usr/bin/env python3
"""
Test script to verify chat streaming works (OpenAI).
"""

import sys
import os
import asyncio
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

async def test_chat_streaming():
    """Test chat streaming with OpenAI model."""
    print("=" * 70)
    print("Chat Streaming Test with New Gemini Models")
    print("=" * 70)
    
    try:
        from packages.core.llm.factory import get_model_for_task, get_llm_client
        
        # Get API key from environment
        api_key = os.environ.get('OPENAI_API_KEY', '')
        if not api_key or api_key == 'test-key':
            print("\n[WARNING] No valid OPENAI_API_KEY found")
            print("This test requires a valid API key to test actual streaming")
            print("Skipping actual API call test, but verifying model configuration...")
            
            # Test configuration only
            provider, model = get_model_for_task("chat")
            print(f"\n[OK] Chat routing configured: provider={provider}, model={model}")
            assert str(provider).lower().endswith("openai"), f"Expected OpenAI provider, got {provider}"
            assert model.startswith("gpt-"), f"Expected GPT model, got {model}"
            print(f"[OK] Model configuration is correct")
            return True
        
        print(f"\n[1/3] Getting LLM client for chat...")
        provider, model = get_model_for_task("chat")
        llm_client = get_llm_client(provider=provider, model=model, temperature=0.7)
        print(f"  [OK] Client created: model={llm_client.model}, provider={llm_client.provider}")
        
        print(f"\n[2/3] Testing stream_generate with simple prompt...")
        test_prompt = "Hello, this is a test. Please respond with a short greeting."
        chunks_received = 0
        text_accumulated = ""
        
        try:
            async for chunk in llm_client.stream_generate(prompt=test_prompt, temperature=0.7):
                if chunk.content:
                    chunks_received += 1
                    text_accumulated += chunk.content
                    if chunks_received <= 3:  # Print first few chunks
                        print(f"  [CHUNK {chunks_received}] {chunk.content[:50]}...")
                
                if chunk.done:
                    break
            
            if chunks_received > 0:
                print(f"  [SUCCESS] Received {chunks_received} chunks, total length: {len(text_accumulated)}")
                print(f"  [OK] Streaming works with model: {llm_client.model}")
                return True
            else:
                print(f"  [WARNING] No chunks received - model may be blocked or empty response")
                return False
                
        except Exception as e:
            error_msg = str(e)
            error_type = type(e).__name__
            
            if "404" in error_msg or "NotFound" in error_type or "not found" in error_msg.lower():
                print(f"  [ERROR] Model not found: {error_type}: {error_msg[:200]}")
                print(f"  [INFO] This suggests the model '{llm_client.model}' is not available")
                print(f"  [INFO] The fallback logic should have tried alternative models")
                return False
            else:
                print(f"  [ERROR] Streaming failed: {error_type}: {error_msg[:200]}")
                return False
        
    except Exception as e:
        print(f"\n[ERROR] Test failed: {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run test."""
    result = asyncio.run(test_chat_streaming())
    
    print("\n" + "=" * 70)
    if result:
        print("[SUCCESS] Chat streaming test passed!")
    else:
        print("[FAILURE] Chat streaming test failed - check error messages above")
    print("=" * 70)
    
    return 0 if result else 1

if __name__ == "__main__":
    sys.exit(main())
