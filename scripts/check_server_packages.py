"""
Check which packages are installed in the server's Python environment.
Run this using the SAME Python that your server uses.
"""

import sys
import os

print("=" * 70)
print("Server Python Environment Check")
print("=" * 70)

print(f"\nPython executable: {sys.executable}")
print(f"Python version: {sys.version.split()[0]}")

# Check if virtual environment
if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
    print(f"Virtual environment: {sys.prefix}")
else:
    print("Using system Python (no virtual environment)")

print("\nPackage versions:")
packages = ['openai', 'httpx', 'fastapi', 'uvicorn']

for pkg in packages:
    try:
        mod = __import__(pkg)
        version = getattr(mod, '__version__', 'unknown')
        print(f"  {pkg:15} {version}")
    except ImportError:
        print(f"  {pkg:15} NOT INSTALLED")

# Try to import the actual modules used
print("\nTesting imports used by the server:")
try:
    from config.settings import settings
    print("  [OK] config.settings imported")
except Exception as e:
    print(f"  [ERROR] config.settings: {e}")

try:
    from packages.core.rag.vectorstores.pinecone_store import PineconeVectorStore
    print("  [OK] PineconeVectorStore imported")
except Exception as e:
    print(f"  [ERROR] PineconeVectorStore: {e}")

try:
    import openai
    # Try to create a client
    try:
        client = openai.AsyncOpenAI(api_key="test-key")
        print("  [OK] openai.AsyncOpenAI can be created")
    except Exception as e:
        print(f"  [ERROR] openai.AsyncOpenAI creation failed: {type(e).__name__}: {e}")
        if "proxies" in str(e).lower():
            print("  *** PROXIES ERROR DETECTED ***")
except Exception as e:
    print(f"  [ERROR] openai import failed: {e}")

print("\n" + "=" * 70)
