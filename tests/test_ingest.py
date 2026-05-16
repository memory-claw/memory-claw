from pathlib import Path

import institutional_memory.ingest as ingest


class FakeCollection:
    def __init__(self):
        self.add_calls = []
        self.delete_calls = []

    def add(self, **kwargs):
        self.add_calls.append(kwargs)

    def delete(self, **kwargs):
        self.delete_calls.append(kwargs)


def test_changed_file_replaces_existing_source_before_add(tmp_path, monkeypatch):
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    doc = corpus / "source.txt"
    doc.write_text(" ".join(f"word{i}" for i in range(20)), encoding="utf-8")
    registry = tmp_path / "ingested_files.json"
    registry.write_text('{"corpus/source.txt": "old"}', encoding="utf-8")
    collection = FakeCollection()

    monkeypatch.setattr(ingest, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(ingest, "INGESTED_REGISTRY", registry)
    monkeypatch.setattr(ingest, "get_chroma_collection", lambda: collection)
    monkeypatch.setattr(ingest, "embed_text", lambda text: [0.1, 0.2, 0.3])

    result = ingest.ingest_folder(corpus)

    assert result == {"files": 1, "chunks": 1}
    assert collection.delete_calls == [{"where": {"source": "corpus/source.txt"}}]
    assert len(collection.add_calls) == 1


def test_nested_corpus_files_are_ingested(tmp_path, monkeypatch):
    corpus = tmp_path / "corpus"
    nested = corpus / "mock_data" / "postmortems"
    nested.mkdir(parents=True)
    doc = nested / "source.md"
    doc.write_text(" ".join(f"word{i}" for i in range(20)), encoding="utf-8")
    (nested / ".DS_Store").write_text("noise", encoding="utf-8")
    registry = tmp_path / "ingested_files.json"
    collection = FakeCollection()

    monkeypatch.setattr(ingest, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(ingest, "INGESTED_REGISTRY", registry)
    monkeypatch.setattr(ingest, "get_chroma_collection", lambda: collection)
    monkeypatch.setattr(ingest, "embed_text", lambda text: [0.1, 0.2, 0.3])

    result = ingest.ingest_folder(corpus)

    assert result == {"files": 1, "chunks": 1}
    assert collection.add_calls[0]["metadatas"][0]["source"] == (
        "corpus/mock_data/postmortems/source.md"
    )
