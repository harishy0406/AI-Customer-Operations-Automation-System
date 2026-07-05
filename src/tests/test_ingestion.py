import pytest
from src.ingestion.chunker import chunk_text
from src.ingestion.extractors import extract_text
import io


def test_chunk_simple_text():
    text = "Hello world. " * 200
    chunks = chunk_text(text, chunk_size=100, overlap=10)
    assert len(chunks) >= 1
    assert all("content" in c for c in chunks)
    assert all("metadata" in c for c in chunks)


def test_chunk_metadata():
    text = "Test content"
    chunks = chunk_text(text, meta={"source": "test"}, chunk_size=50, overlap=5)
    assert len(chunks) == 1
    assert chunks[0]["metadata"]["source"] == "test"
    assert "chunk_index" in chunks[0]["metadata"]


def test_extract_markdown():
    content = b"# Title\n\nSome paragraph text."
    result = extract_text(io.BytesIO(content), "markdown")
    assert "# Title" in result
    assert "Some paragraph text" in result


def test_extract_csv():
    content = b"name,email\nJohn,john@test.com\nJane,jane@test.com"
    result = extract_text(io.BytesIO(content), "csv")
    assert "name | email" in result
    assert "John | john@test.com" in result
