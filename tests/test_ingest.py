from pathlib import Path

import institutional_memory.ingest as ingest
import scripts.ingest_corpus as ingest_corpus


class FakeCollection:
    def __init__(self):
        self.add_calls = []
        self.delete_calls = []

    def add(self, **kwargs):
        self.add_calls.append(kwargs)

    def delete(self, **kwargs):
        self.delete_calls.append(kwargs)


def test_changed_file_replaces_existing_source_before_add(tmp_path, monkeypatch):
    company_corpus = tmp_path / "company" / "corpus"
    company_corpus.mkdir(parents=True)
    doc = company_corpus / "source.txt"
    doc.write_text(" ".join(f"word{i}" for i in range(20)), encoding="utf-8")
    registry = tmp_path / "ingested_files.json"
    registry.write_text('{"company/corpus/source.txt": "old"}', encoding="utf-8")
    collection = FakeCollection()

    monkeypatch.setattr(ingest, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(ingest, "INGESTED_REGISTRY", registry)
    monkeypatch.setattr(ingest, "get_chroma_collection", lambda: collection)
    monkeypatch.setattr(ingest, "embed_text", lambda text: [0.1, 0.2, 0.3])

    result = ingest.ingest_folder(company_corpus)

    assert result == {"files": 1, "chunks": 1}
    assert collection.delete_calls == [{"where": {"source": "company/corpus/source.txt"}}]
    assert len(collection.add_calls) == 1


def test_nested_corpus_files_are_ingested(tmp_path, monkeypatch):
    company_corpus = tmp_path / "company" / "corpus"
    nested = company_corpus / "mock_data" / "postmortems"
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

    result = ingest.ingest_folder(company_corpus)

    assert result == {"files": 1, "chunks": 1}
    assert collection.add_calls[0]["metadatas"][0]["source"] == (
        "company/corpus/mock_data/postmortems/source.md"
    )


def test_company_parent_corpus_files_are_ingested(tmp_path, monkeypatch):
    company_corpus = tmp_path / "company" / "corpus"
    company_corpus.mkdir(parents=True)
    doc = company_corpus / "vendor_terms.md"
    doc.write_text(" ".join(f"word{i}" for i in range(20)), encoding="utf-8")
    registry = tmp_path / "ingested_files.json"
    collection = FakeCollection()

    monkeypatch.setattr(ingest, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(ingest, "INGESTED_REGISTRY", registry)
    monkeypatch.setattr(ingest, "get_chroma_collection", lambda: collection)
    monkeypatch.setattr(ingest, "embed_text", lambda text: [0.1, 0.2, 0.3])

    result = ingest.ingest_folder(company_corpus)

    assert result == {"files": 1, "chunks": 1}
    assert collection.add_calls[0]["metadatas"][0]["source"] == (
        "company/corpus/vendor_terms.md"
    )


def test_ingest_corpus_uses_company_parent_corpus(monkeypatch, tmp_path):
    company_corpus = tmp_path / "company" / "corpus"
    calls = []

    monkeypatch.setattr(ingest_corpus, "COMPANY_CORPUS_PATH", company_corpus)

    def fake_ingest_folder(path, force=False):
        calls.append((path, force))
        return {"files": 2, "chunks": 4}

    monkeypatch.setattr(ingest_corpus, "ingest_folder", fake_ingest_folder)

    result = ingest_corpus.ingest_corpus_roots(force=True)

    assert result == {"files": 2, "chunks": 4}
    assert calls == [(company_corpus, True)]
