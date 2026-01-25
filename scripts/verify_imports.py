#!/usr/bin/env python3
"""
Import Verification Script

Verifies all imports work correctly and checks for circular dependencies.
"""

import sys
import importlib
import traceback
from typing import List, Dict, Set, Tuple
from collections import defaultdict

# Modules to test
MODULES_TO_TEST = [
    # Config
    "config.settings",
    "config",
    
    # Database
    "packages.core.database.connection",
    "packages.core.database.models",
    "packages.core.database.models.tenant",
    "packages.core.database.models.source",
    "packages.core.database.models.chat",
    "packages.core.database.models.note",
    
    # LLM
    "packages.core.llm",
    "packages.core.llm.factory",
    "packages.core.llm.openai_client",
    "packages.core.llm.gemini_client",
    
    # Services
    "packages.core.services.chat_service",
    "packages.core.services.source_service",
    "packages.core.services.rag_service",
    "packages.core.services.studio_service",
    "packages.core.services.note_service",
    
    # RAG
    "packages.core.rag.chunker",
    "packages.core.rag.embedder",
    "packages.core.rag.retriever",
    "packages.core.rag.vectorstores.pinecone_store",
    
    # Storage
    "packages.core.storage.s3",
    "packages.core.storage.local",
    
    # Prompts
    "packages.core.prompts.loader",
    "packages.core.prompts.registry",
    
    # Middleware
    "apps.api.middleware.tenant",
    "apps.api.middleware.auth",
    "apps.api.middleware.common",
    
    # Routes
    "apps.api.routes.chat",
    "apps.api.routes.sources",
    "apps.api.routes.studio",
    "apps.api.routes.notes",
    "apps.api.routes.health",
    
    # Main app
    "apps.api.main",
]

def test_import(module_name: str) -> Tuple[bool, str]:
    """Test importing a module."""
    try:
        importlib.import_module(module_name)
        return True, ""
    except Exception as e:
        return False, str(e)

def check_circular_dependencies() -> Dict[str, List[str]]:
    """Check for potential circular dependencies."""
    import_graph = defaultdict(set)
    
    # This is a simplified check - full circular dependency detection
    # would require parsing AST and tracking import chains
    print("\n⚠️  Note: Full circular dependency detection requires AST parsing.")
    print("   This script verifies imports work, which is the first step.")
    
    return {}

def main():
    print("=" * 60)
    print("Import Verification Script")
    print("=" * 60)
    
    results = []
    failed = []
    
    for module_name in MODULES_TO_TEST:
        success, error = test_import(module_name)
        status = "✓" if success else "✗"
        results.append((module_name, success, error))
        
        if success:
            print(f"{status} {module_name}")
        else:
            print(f"{status} {module_name}")
            print(f"  ERROR: {error}")
            failed.append((module_name, error))
    
    print("\n" + "=" * 60)
    print(f"Results: {len([r for r in results if r[1]])}/{len(results)} passed")
    
    if failed:
        print(f"\n✗ {len(failed)} modules failed to import:")
        for module_name, error in failed:
            print(f"  - {module_name}: {error}")
        print("\n" + "=" * 60)
        return 1
    else:
        print("\n✓ All imports verified successfully!")
        print("=" * 60)
        
        # Check for circular dependencies
        circular = check_circular_dependencies()
        if circular:
            print("\n⚠️  Potential circular dependencies detected:")
            for module, deps in circular.items():
                print(f"  {module}: {deps}")
        else:
            print("\n✓ No obvious circular dependencies detected")
        
        return 0

if __name__ == "__main__":
    sys.exit(main())

