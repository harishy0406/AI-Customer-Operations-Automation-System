import tiktoken
from src.api.config import get_settings

settings = get_settings()
_tokenizer = tiktoken.get_encoding("cl100k_base")


def tokenize(text: str) -> list[int]:
    return _tokenizer.encode(text)


def decode_tokens(tokens: list[int]) -> str:
    return _tokenizer.decode(tokens)


def chunk_text(text: str, meta: dict | None = None, chunk_size: int | None = None, overlap: int | None = None) -> list[dict]:
    chunk_size = chunk_size or settings.CHUNK_SIZE
    overlap = overlap or settings.CHUNK_OVERLAP
    tokens = tokenize(text)
    chunks = []
    start = 0

    while start < len(tokens):
        end = min(start + chunk_size, len(tokens))
        chunk_tokens = tokens[start:end]
        chunk_content = decode_tokens(chunk_tokens)
        chunk_meta = dict(meta or {})
        chunk_meta["chunk_index"] = len(chunks)
        chunk_meta["token_count"] = len(chunk_tokens)
        chunks.append({"content": chunk_content, "metadata": chunk_meta})
        if end >= len(tokens):
            break
        start = end - overlap

    return chunks
