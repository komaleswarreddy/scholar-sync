"""
Test script to diagnose OpenAI client initialization issues.
Run this to see detailed error information.
"""

import sys
import os
import traceback

print("=" * 70)
print("OpenAI Client Initialization Diagnostic Test")
print("=" * 70)

# Check imports
print("\n[1] Checking imports...")
try:
    import openai
    print(f"   [OK] openai imported successfully")
    try:
        print(f"   [OK] openai version: {openai.__version__}")
    except:
        print(f"   [WARN] Could not get openai version")
except ImportError as e:
    print(f"   ✗ Failed to import openai: {e}")
    sys.exit(1)

try:
    import httpx
    print(f"   [OK] httpx imported successfully")
    try:
        print(f"   [OK] httpx version: {httpx.__version__}")
    except:
        print(f"   [WARN] Could not get httpx version")
except ImportError as e:
    print(f"   [ERROR] Failed to import httpx: {e}")
    sys.exit(1)

# Check environment variables
print("\n[2] Checking environment variables...")
proxy_vars = ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 'ALL_PROXY', 'all_proxy']
found_proxies = []
for var in proxy_vars:
    if var in os.environ:
        found_proxies.append(f"{var}={os.environ[var]}")
        print(f"   [WARN] Found: {var}={os.environ[var]}")

if not found_proxies:
    print("   [OK] No proxy environment variables found")

# Check API key
print("\n[3] Checking OpenAI API key...")
try:
    from config.settings import settings
    if settings.OPENAI_API_KEY and settings.OPENAI_API_KEY != "your-openai-api-key":
        print(f"   [OK] API key is set (length: {len(settings.OPENAI_API_KEY)})")
        api_key = settings.OPENAI_API_KEY
    else:
        print("   [ERROR] API key not configured")
        print("   [WARN] Using dummy key for testing (will fail on actual API call)")
        api_key = "test-key"
except Exception as e:
    print(f"   [ERROR] Failed to load settings: {e}")
    api_key = "test-key"

# Test httpx.AsyncClient creation
print("\n[4] Testing httpx.AsyncClient creation...")
try:
    # Save proxy vars
    original_proxy_vars = {}
    for var in proxy_vars:
        if var in os.environ:
            original_proxy_vars[var] = os.environ[var]
            del os.environ[var]
    
    try:
        http_client = httpx.AsyncClient(timeout=60.0)
        print("   [OK] httpx.AsyncClient created successfully")
        # Clean up
        try:
            import asyncio
            asyncio.run(http_client.aclose())
        except:
            pass
    except Exception as e:
        print(f"   [ERROR] Failed to create httpx.AsyncClient: {type(e).__name__}: {e}")
        print(f"   Full traceback:")
        traceback.print_exc()
    finally:
        # Restore proxy vars
        for var, value in original_proxy_vars.items():
            os.environ[var] = value
except Exception as e:
    print(f"   [ERROR] Unexpected error: {type(e).__name__}: {e}")
    traceback.print_exc()

# Test OpenAI client creation
print("\n[5] Testing openai.AsyncOpenAI creation...")
try:
    # Save proxy vars again
    original_proxy_vars = {}
    for var in proxy_vars:
        if var in os.environ:
            original_proxy_vars[var] = os.environ[var]
            del os.environ[var]
    
    try:
        print("   Attempting to create openai.AsyncOpenAI...")
        client = openai.AsyncOpenAI(api_key=api_key)
        print("   [OK] openai.AsyncOpenAI created successfully!")
        
        # Try to access a property to see if it triggers initialization
        print("   Testing client properties...")
        _ = client.api_key  # This might trigger internal initialization
        print("   [OK] Client properties accessible")
        
    except TypeError as e:
        error_msg = str(e)
        print(f"   [ERROR] TypeError: {error_msg}")
        if "proxies" in error_msg.lower():
            print("\n   *** PROXIES ERROR DETECTED ***")
            print("   This is the compatibility issue between openai 1.10.0 and httpx 0.28+")
            print("   SOLUTION: pip install --upgrade 'openai>=1.12.0'")
        print("\n   Full traceback:")
        traceback.print_exc()
    except ValueError as e:
        error_msg = str(e)
        print(f"   [ERROR] ValueError: {error_msg}")
        print("\n   Full traceback:")
        traceback.print_exc()
    except Exception as e:
        error_type = type(e).__name__
        error_msg = str(e)
        print(f"   [ERROR] {error_type}: {error_msg}")
        print("\n   Full traceback:")
        traceback.print_exc()
    finally:
        # Restore proxy vars
        for var, value in original_proxy_vars.items():
            os.environ[var] = value
except Exception as e:
    print(f"   [ERROR] Unexpected error: {type(e).__name__}: {e}")
    traceback.print_exc()

print("\n" + "=" * 70)
print("Diagnostic complete!")
print("=" * 70)
