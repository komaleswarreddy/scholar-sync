"""
Script to fix OpenAI/httpx proxies compatibility issue.

This script helps diagnose and fix the "proxies" unexpected keyword argument error.
"""

import sys
import os

def check_versions():
    """Check current versions of openai and httpx."""
    try:
        import openai
        import httpx
        print(f"Current versions:")
        print(f"  openai: {openai.__version__}")
        print(f"  httpx: {httpx.__version__}")
        
        # Check if versions are compatible
        openai_version = tuple(map(int, openai.__version__.split('.')[:2]))
        httpx_version = tuple(map(int, httpx.__version__.split('.')[:2]))
        
        if openai_version < (1, 12) and httpx_version >= (0, 28):
            print("\n⚠️  WARNING: Incompatible versions detected!")
            print("   openai < 1.12.0 with httpx >= 0.28.0 causes 'proxies' error")
            print("   Solution: Upgrade openai to >= 1.12.0")
            return False
        else:
            print("\n✅ Versions appear compatible")
            return True
    except ImportError as e:
        print(f"❌ Error importing packages: {e}")
        return False

def check_proxy_env():
    """Check for proxy environment variables."""
    proxy_vars = ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 'ALL_PROXY', 'all_proxy']
    found = []
    for var in proxy_vars:
        if var in os.environ:
            found.append(f"{var}={os.environ[var]}")
    
    if found:
        print("\n⚠️  Proxy environment variables found:")
        for var in found:
            print(f"   {var}")
        print("   These may cause issues with httpx 0.28+")
    else:
        print("\n✅ No proxy environment variables found")
    
    return found

def main():
    print("=" * 60)
    print("OpenAI/httpx Proxies Compatibility Checker")
    print("=" * 60)
    
    versions_ok = check_versions()
    proxy_vars = check_proxy_env()
    
    print("\n" + "=" * 60)
    print("Recommendations:")
    print("=" * 60)
    
    if not versions_ok:
        print("1. Upgrade openai:")
        print("   pip install --upgrade 'openai>=1.12.0'")
    
    if proxy_vars:
        print("2. If you don't need proxies, unset these environment variables")
        print("   or ensure they're not set in your .env file")
    
    print("\n3. After upgrading, restart your application")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    main()
