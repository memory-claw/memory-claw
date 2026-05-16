import institutional_memory.ingest as ingest


def test_chunk_overlap_present(monkeypatch):
    monkeypatch.setattr(ingest, "CHUNK_SIZE", 20)
    monkeypatch.setattr(ingest, "CHUNK_OVERLAP", 5)
    text = " ".join(f"word{i}" for i in range(45))
    chunks = ingest.chunk_text(text, "corpus/source.txt")
    assert chunks[0]["text"].split()[-5:] == chunks[1]["text"].split()[:5]


def test_tiny_trailing_chunks_are_skipped(monkeypatch):
    monkeypatch.setattr(ingest, "CHUNK_SIZE", 20)
    monkeypatch.setattr(ingest, "CHUNK_OVERLAP", 5)
    text = " ".join(f"word{i}" for i in range(24))
    chunks = ingest.chunk_text(text, "corpus/source.txt")
    assert len(chunks) == 1


def test_chunk_ids_include_source_and_offset(monkeypatch):
    monkeypatch.setattr(ingest, "CHUNK_SIZE", 20)
    monkeypatch.setattr(ingest, "CHUNK_OVERLAP", 5)
    chunks = ingest.chunk_text(" ".join(f"word{i}" for i in range(30)), "corpus/source.txt")
    assert chunks[0]["id"].startswith("corpus/source.txt:0:")
