"""
Test script to verify Tutor Mode metadata filtering in NCERT retrieval.

This script tests:
1. Filter construction with exact values
2. Pinecone query results metadata
3. Post-processing filter validation
4. Rejection of chunks from other classes/chapters
"""

import asyncio
import sys
from typing import Optional

# Setup path to import app modules
sys.path.insert(0, str(__import__('pathlib').Path(__file__).parent))

from packages.core.rag.retriever import Retriever
from config.settings import settings


async def test_tutor_mode_filtering():
    """Test filtering with specific Tutor Mode parameters."""
    
    print("=" * 90)
    print("TUTOR MODE FILTERING TEST")
    print("=" * 90)
    print()
    
    # Initialize retriever
    retriever = Retriever(
        user_id="test_user_for_filtering_validation",
        tenant_id="default",
    )
    
    # Test Case 1: Class 10, Science, Chapter 3
    print("TEST CASE 1: Class 10, Science, Chapter 3")
    print("-" * 90)
    query = "What is corrosion?"
    
    results = await retriever._retrieve_ncert_global_matches(
        query=query,
        ncert_class=10,
        ncert_subject="Science",
        ncert_chapter_no=3,
        ncert_chapter_name="Metals and Non-metals",
    )
    
    print(f"\nFinal Results: {len(results)} matches")
    print("-" * 90)
    if results:
        for idx, result in enumerate(results[:5], 1):
            meta = result.get("metadata", {})
            print(f"\n[Result {idx}]")
            print(f"  Class: {meta.get('class')}")
            print(f"  Subject: {meta.get('subject')}")
            print(f"  Chapter No: {meta.get('chapter_no')}")
            print(f"  Chapter Name: {meta.get('chapter_name')}")
            print(f"  Score: {result.get('score', 0):.4f}")
            print(f"  Display Source: {meta.get('display_source', 'N/A')}")
    else:
        print("⚠️  No results found!")
    
    print("\n" + "=" * 90)
    
    # Test Case 2: Different chapter (should get DIFFERENT results or NONE)
    print("\nTEST CASE 2: Class 10, Science, Chapter 1")
    print("-" * 90)
    query2 = "What is matter?"
    
    results2 = await retriever._retrieve_ncert_global_matches(
        query=query2,
        ncert_class=10,
        ncert_subject="Science",
        ncert_chapter_no=1,
        ncert_chapter_name="Chemical Reactions and Equations",
    )
    
    print(f"\nFinal Results: {len(results2)} matches")
    print("-" * 90)
    if results2:
        for idx, result in enumerate(results2[:3], 1):
            meta = result.get("metadata", {})
            print(f"\n[Result {idx}]")
            print(f"  Class: {meta.get('class')}")
            print(f"  Subject: {meta.get('subject')}")
            print(f"  Chapter No: {meta.get('chapter_no')}")
            print(f"  Chapter Name: {meta.get('chapter_name')}")
            print(f"  Score: {result.get('score', 0):.4f}")
    else:
        print("⚠️  No results found!")
    
    print("\n" + "=" * 90)
    print("\n🔍 VALIDATION")
    print("-" * 90)
    
    # Validate Test Case 1
    print("\n✓ Test Case 1 Validation (Class 10, Science, Chapter 3):")
    case1_valid = True
    if not results:
        print("  ❌ FAIL: No results found")
        case1_valid = False
    else:
        for result in results:
            meta = result.get("metadata", {})
            class_val = meta.get('class')
            subject_val = meta.get('subject')
            chapter_no = meta.get('chapter_no')
            
            if class_val != 10:
                print(f"  ❌ FAIL: Got class {class_val}, expected 10")
                case1_valid = False
            if subject_val != "science":
                print(f"  ❌ FAIL: Got subject '{subject_val}', expected 'science'")
                case1_valid = False
            if chapter_no != 3:
                print(f"  ❌ FAIL: Got chapter_no {chapter_no}, expected 3")
                case1_valid = False
        
        if case1_valid:
            print(f"  ✅ PASS: All {len(results)} results match Class 10, Science, Chapter 3")
    
    # Validate Test Case 2
    print("\n✓ Test Case 2 Validation (Class 10, Science, Chapter 1):")
    if not results2:
        print("  ✅ PASS: No results found (or from Chapter 1 only)")
    else:
        case2_valid = True
        for result in results2:
            meta = result.get("metadata", {})
            class_val = meta.get('class')
            chapter_no = meta.get('chapter_no')
            
            if class_val != 10 or chapter_no != 1:
                print(f"  ❌ FAIL: Got class {class_val}, chapter {chapter_no}, expected class 10, chapter 1")
                case2_valid = False
                break
        
        if case2_valid:
            print(f"  ✅ PASS: All {len(results2)} results match Class 10, Chapter 1")
    
    print("\n" + "=" * 90)


if __name__ == "__main__":
    asyncio.run(test_tutor_mode_filtering())
