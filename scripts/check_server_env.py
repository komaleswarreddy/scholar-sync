"""
Check which Python environment the server is using.
Run this from the same location where you start your server.
"""

import sys
import os

print("=" * 70)
print("Python Environment Check")
print("=" * 70)

print(f"\nPython executable: {sys.executable}")
print(f"Python version: {sys.version}")
print(f"Python path: {sys.path[:3]}...")  # First 3 entries

print(f"\nCurrent working directory: {os.getcwd()}")

# Check for virtual environment
if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
    print(f"Virtual environment: {sys.prefix}")
else:
    print("No virtual environment detected (using system Python)")

# Check package versions
print("\nPackage versions:")
try:
    import openai
    print(f"  openai: {openai.__version__}")
except ImportError:
    print("  openai: NOT INSTALLED")

try:
    import httpx
    print(f"  httpx: {httpx.__version__}")
except ImportError:
    print("  httpx: NOT INSTALLED")

# Check if we can import the config
try:
    from config.settings import settings
    print(f"  config.settings: OK")
    if settings.OPENAI_API_KEY and settings.OPENAI_API_KEY != "your-openai-api-key":
        print(f"  OPENAI_API_KEY: Set (length: {len(settings.OPENAI_API_KEY)})")
    else:
        print(f"  OPENAI_API_KEY: Not configured")
except Exception as e:
    print(f"  config.settings: ERROR - {e}")

print("\n" + "=" * 70)
