#!/usr/bin/env python3
"""
Test script to demonstrate the new chunking functionality.
"""

from chunker import create_chunks_for_document, smart_chunk_text

def test_chunking():
    print("=== Testing Smart Chunking ===\n")

    # Test 1: Short text (should not be chunked)
    short_text = "This is a short issue description. It has only a few sentences."
    print("Test 1: Short text")
    print(f"Input: {short_text}")
    chunks = smart_chunk_text(short_text, max_tokens=100)
    print(f"Output: {len(chunks)} chunk(s)")
    for i, chunk in enumerate(chunks, 1):
        print(f"  Chunk {i}: {chunk}")
    print()

    # Test 2: Long text (should be chunked)
    long_text = """
    This is a very long issue description that should be split into multiple chunks.

    ## Problem Description
    The application crashes when processing large datasets. This happens consistently
    with files over 100MB. The error occurs in the data processing module, specifically
    in the transform_data function. We've seen this issue reported by multiple users.

    ## Steps to Reproduce
    1. Load a dataset larger than 100MB
    2. Call the transform_data function
    3. Observe the crash

    ## Expected Behavior
    The function should process large datasets without crashing. It should handle
    memory efficiently and provide progress updates.

    ## Actual Behavior
    The application throws an OutOfMemoryError and terminates unexpectedly.

    ## Environment
    - Python 3.9
    - pandas 1.5.0
    - numpy 1.21.0

    ## Additional Context
    This issue started appearing after the recent update to version 2.1. Previous
    versions handled large datasets without problems. We suspect it might be related
    to the new caching mechanism introduced in this version.
    """

    print("Test 2: Long text")
    print(f"Input length: {len(long_text)} characters")
    chunks = smart_chunk_text(long_text, max_tokens=150, overlap_tokens=30)
    print(f"Output: {len(chunks)} chunk(s)")
    for i, chunk in enumerate(chunks, 1):
        print(f"  Chunk {i} ({len(chunk)} chars): {chunk[:100]}...")
    print()

    # Test 3: Document chunking with title
    print("Test 3: Document chunking with title")
    title = "Memory leak in data processing module"
    doc_chunks = create_chunks_for_document(title, long_text, max_tokens=150)
    print(f"Output: {len(doc_chunks)} chunk(s)")
    for i, (chunk_title, chunk_body) in enumerate(doc_chunks, 1):
        print(f"  Chunk {i} Title: {chunk_title}")
        print(f"  Chunk {i} Body: {chunk_body[:100]}...")
        print()

if __name__ == "__main__":
    test_chunking()
