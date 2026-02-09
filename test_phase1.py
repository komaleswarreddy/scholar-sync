#!/usr/bin/env python3
"""Quick verification of Phase 1 features."""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

def test_imports():
    """Test that all modules can be imported."""
    try:
        from packages.core.processing.pdf_preprocessor import PDFPreprocessor
        from packages.core.processing.semantic_chunker import SemanticChunker
        from packages.core.processing.context_cache import ContextCache
        from packages.core.rag.chunker import Chunker
        print("✅ All imports successful")
        return True
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False

def test_config():
    """Test configuration."""
    from config.settings import settings
    
    overlap_percent = getattr(settings, 'CHUNK_OVERLAP_PERCENT', None)
    use_semantic = getattr(settings, 'USE_SEMANTIC_CHUNKING', None)
    
    print(f"✅ CHUNK_OVERLAP_PERCENT: {overlap_percent}")
    print(f"✅ USE_SEMANTIC_CHUNKING: {use_semantic}")
    
    if overlap_percent:
        assert 0.10 <= overlap_percent <= 0.15, "Overlap should be 10-15%"
    
    return True

def test_preprocessor():
    """Test PDF preprocessor."""
    from packages.core.processing.pdf_preprocessor import PDFPreprocessor
    
    preprocessor = PDFPreprocessor()
    dirty = "Page 1\nCONFIDENTIAL\nContent (Author 2024).\nReferences\n1. Author (2024)."
    cleaned = preprocessor.clean_text(dirty)
    
    assert len(cleaned) < len(dirty), "Should reduce text length"
    assert "CONFIDENTIAL" not in cleaned, "Should remove watermarks"
    print("✅ PDF preprocessor working")
    return True

def test_chunker():
    """Test chunker."""
    from packages.core.rag.chunker import Chunker
    
    chunker = Chunker(use_semantic=True)
    text = "Sentence one. " * 100
    chunks = chunker.chunk_text(text)
    
    assert len(chunks) > 0, "Should create chunks"
    print(f"✅ Chunker created {len(chunks)} chunks")
    return True

def test_cache():
    """Test cache."""
    from packages.core.processing.context_cache import ContextCache
    
    cache = ContextCache(cache_dir="test_cache")
    test_content = b"test"
    hash_val = cache.get_file_hash(test_content)
    
    assert len(hash_val) == 64, "Hash should be 64 chars (SHA256)"
    print("✅ Cache working")
    return True

if __name__ == "__main__":
    print("Testing Phase 1 Implementation...\n")
    
    tests = [
        test_imports,
        test_config,
        test_preprocessor,
        test_chunker,
        test_cache,
    ]
    
    results = []
    for test in tests:
        try:
            results.append(test())
        except Exception as e:
            print(f"❌ {test.__name__} failed: {e}")
            import traceback
            traceback.print_exc()
            results.append(False)
        print()
    
    if all(results):
        print("🎉 All tests passed! Phase 1 features are implemented.")
    else:
        print("⚠️  Some tests failed. Check the errors above.")
        sys.exit(1)
