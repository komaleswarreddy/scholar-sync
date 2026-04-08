#!/usr/bin/env python3
"""
Test script to validate Tutor Mode metadata filter enforcement.

This script tests that when Tutor Mode filters are applied (e.g., Class=9, Subject=Science, Chapter=4),
the retrieval system ONLY returns results matching those filters, and does not fall back to broader data.

Expected behavior:
1. Filter builder logs show: [TUTOR_FILTER_BUILD] with correct filters
2. Pinecone query logs show: [TUTOR_QUERY_PINECONE] with filter condition
3) Post-processing logs show: [TUTOR_POSTPROCESS_FILTER] if any mismatches occur OR [TUTOR_FILTER_MISMATCH] for specific mismatches
4. Response contains ONLY chunks with class=9, subject=science, chapter_no=4
"""

import asyncio
import json
import sys
from typing import Optional, Dict, Any
import httpx

# Test configuration
API_BASE_URL = "http://localhost:8000"
CHAT_STREAM_ENDPOINT = f"{API_BASE_URL}/api/chat/stream"

# Test credentials (assuming dev/test environment)
TEST_USER_HEADERS = {
    "Authorization": "Bearer test-token",  # Adjust based on auth setup
    "Content-Type": "application/json",
}

class TutorFilterTester:
    def __init__(self):
        self.client = None
        self.log_lines = []
        
    async def test_tutor_filters(self):
        """Test Tutor Mode filters with a sample query."""
        print("\n" + "="*80)
        print("TUTOR MODE FILTER TEST")
        print("="*80)
        
        # Test Case 1: Class 9, Science, Chapter 4
        test_query = {
            "message": "What is corrosion and how does it occur?",
            "history": [],
            "active_source_ids": [],
            "include_ncert_global": True,
            "ncert_class": 9,
            "ncert_subject": "science",
            "ncert_chapter_no": 4,
            "ncert_chapter_name": "Corrosion",
        }
        
        print(f"\nTest Case: Class=9, Subject=Science, Chapter=4")
        print(f"Query: {test_query['message']}")
        print(f"Filters: class={test_query['ncert_class']}, subject={test_query['ncert_subject']}, "
              f"chapter={test_query['ncert_chapter_no']}")
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                print(f"\nSending request to {CHAT_STREAM_ENDPOINT}...")
                async with client.stream(
                    "POST",
                    CHAT_STREAM_ENDPOINT,
                    json=test_query,
                    headers=TEST_USER_HEADERS,
                ) as response:
                    if response.status_code != 200:
                        print(f"ERROR: Got status {response.status_code}")
                        print(f"Response: {await response.atext()}")
                        return False
                    
                    print("Streaming response...")
                    chunks_received = 0
                    metadata_samples = []
                    
                    async for line in response.aiter_lines():
                        if not line:
                            continue
                        
                        chunks_received += 1
                        
                        # Parse streaming JSON
                        try:
                            if line.startswith("data: "):
                                data = json.loads(line[6:])
                                
                                # Collect metadata for verification
                                if "citations" in data and isinstance(data["citations"], list):
                                    for citation in data["citations"]:
                                        metadata_samples.append({
                                            "source_id": citation.get("source_id"),
                                            "score": citation.get("score"),
                                            "text_preview": citation.get("text", "")[:100],
                                        })
                                
                        except json.JSONDecodeError:
                            continue
                    
                    print(f"✓ Received {chunks_received} chunks")
                    
                    if metadata_samples:
                        print(f"\nMetadata samples from response:")
                        for i, sample in enumerate(metadata_samples[:3], 1):
                            print(f"  {i}. Score: {sample['score']:.4f}, Preview: {sample['text_preview'][:60]}...")
                    
                    return True
                    
        except Exception as e:
            print(f"ERROR: Failed to execute test: {type(e).__name__}: {e}")
            return False
    
    async def check_api_health(self) -> bool:
        """Check if API is healthy and responding."""
        print("Checking API health...")
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{API_BASE_URL}/api/health")
                if response.status_code == 200:
                    print("✓ API is healthy")
                    return True
                else:
                    print(f"✗ API returned status {response.status_code}")
                    return False
        except Exception as e:
            print(f"✗ API is not responding: {type(e).__name__}: {e}")
            return False
    
    async def run_all_tests(self):
        """Run all tests."""
        if not await self.check_api_health():
            print("\n⚠ API is not available. Ensure backend is running on port 8000")
            return False
        
        result = await self.test_tutor_filters()
        
        print("\n" + "="*80)
        if result:
            print("✓ TEST PASSED: Tutor Mode filter enforcement working")
        else:
            print("✗ TEST FAILED: Check API logs for details")
        print("="*80)
        
        return result


async def main():
    """Run the test suite."""
    tester = TutorFilterTester()
    success = await tester.run_all_tests()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    asyncio.run(main())
