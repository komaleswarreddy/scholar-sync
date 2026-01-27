#!/usr/bin/env python3
"""
Verification script to check if OpenAI httpx fix is present in codebase.

This script verifies that the custom httpx client workaround is present
in both files that use OpenAI client initialization.
"""

import sys
from pathlib import Path

REQUIRED_FILES = [
    "packages/core/rag/vectorstores/pinecone_store.py",
    "packages/core/llm/openai_client.py",
]

REQUIRED_PATTERNS = [
    "httpx.Client(timeout=",
    "http_client=http_client",
    "Workaround for OpenAI 1.9.0/1.10.0 bug",
]

def check_file(file_path: Path) -> tuple[bool, list[str]]:
    """Check if file contains required fix patterns."""
    if not file_path.exists():
        return False, [f"File not found: {file_path}"]
    
    content = file_path.read_text(encoding="utf-8")
    missing = []
    
    for pattern in REQUIRED_PATTERNS:
        if pattern not in content:
            missing.append(f"Missing pattern: {pattern}")
    
    return len(missing) == 0, missing

def main():
    """Main verification function."""
    repo_root = Path(__file__).parent.parent
    all_passed = True
    issues = []
    
    print("Verifying OpenAI httpx fix...")
    print("=" * 60)
    
    for rel_path in REQUIRED_FILES:
        file_path = repo_root / rel_path
        passed, missing = check_file(file_path)
        
        status = "[PASS]" if passed else "[FAIL]"
        print(f"\n{status}: {rel_path}")
        
        if not passed:
            all_passed = False
            for issue in missing:
                print(f"   WARNING: {issue}")
                issues.append(f"{rel_path}: {issue}")
    
    print("\n" + "=" * 60)
    if all_passed:
        print("[SUCCESS] All files contain the OpenAI httpx fix!")
        return 0
    else:
        print("[ERROR] Some files are missing the fix!")
        print("\nTo fix, restore the workaround code:")
        print("1. Create custom httpx.Client(timeout=60.0)")
        print("2. Pass it as http_client parameter to openai.OpenAI()")
        print("3. Include try/except fallback logic")
        return 1

if __name__ == "__main__":
    sys.exit(main())
