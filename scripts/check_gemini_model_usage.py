#!/usr/bin/env python3
"""
Script to check for any remaining references to gemini-1.5-flash
"""

import os
import sys
from pathlib import Path

def check_env_files():
    """Check .env files for gemini-1.5-flash"""
    print("=" * 70)
    print("Checking .env files for gemini-1.5-flash...")
    print("=" * 70)
    
    env_files = []
    for root, dirs, files in os.walk('.'):
        # Skip venv and node_modules
        if 'venv' in root or 'node_modules' in root or '__pycache__' in root:
            continue
        for file in files:
            if file.startswith('.env'):
                env_files.append(Path(root) / file)
    
    found = False
    for env_file in env_files:
        try:
            with open(env_file, 'r') as f:
                content = f.read()
                if 'gemini-1.5-flash' in content.lower() or '1.5-flash' in content.lower():
                    print(f"\n⚠️  FOUND in: {env_file}")
                    for i, line in enumerate(content.split('\n'), 1):
                        if 'gemini' in line.lower() and '1.5' in line.lower():
                            print(f"   Line {i}: {line.strip()}")
                    found = True
        except Exception as e:
            pass
    
    if not found:
        print("✓ No .env files contain gemini-1.5-flash")
    
    return found

def check_python_files():
    """Check Python files for hardcoded gemini-1.5-flash"""
    print("\n" + "=" * 70)
    print("Checking Python files for hardcoded gemini-1.5-flash...")
    print("=" * 70)
    
    found = False
    for root, dirs, files in os.walk('.'):
        # Skip venv, node_modules, __pycache__
        if any(skip in root for skip in ['venv', 'node_modules', '__pycache__', '.git']):
            continue
        
        for file in files:
            if file.endswith('.py'):
                filepath = Path(root) / file
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                        # Check for direct model string (not in comments)
                        lines = content.split('\n')
                        for i, line in enumerate(lines, 1):
                            if 'gemini-1.5-flash' in line and not line.strip().startswith('#'):
                                # Check if it's in a comment
                                if '#' in line:
                                    comment_start = line.index('#')
                                    if 'gemini-1.5-flash' in line[:comment_start]:
                                        print(f"\n⚠️  FOUND in: {filepath}:{i}")
                                        print(f"   {line.strip()}")
                                        found = True
                                else:
                                    print(f"\n⚠️  FOUND in: {filepath}:{i}")
                                    print(f"   {line.strip()}")
                                    found = True
                except Exception:
                    pass
    
    if not found:
        print("✓ No Python files contain hardcoded gemini-1.5-flash (outside comments)")
    
    return found

if __name__ == "__main__":
    print("\n🔍 Checking for gemini-1.5-flash references...\n")
    
    env_found = check_env_files()
    py_found = check_python_files()
    
    print("\n" + "=" * 70)
    if env_found or py_found:
        print("❌ ISSUES FOUND - Please fix the above references")
        sys.exit(1)
    else:
        print("✅ No issues found - All references have been updated!")
        sys.exit(0)
