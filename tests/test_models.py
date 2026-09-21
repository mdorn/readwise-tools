from datetime import UTC, datetime

from readwise_tools.models import Document

FULL_DOC = {
    "id": "doc-1",
    "title": "Some Article",
    "author": "Jane Doe",
    "location": "new",
    "saved_at": "2026-09-10T08:00:00.000000Z",
    "url": "https://readwise.io/read/doc-1",
    "source_url": "https://example.com/article",
    "category": "article",
}


def test_from_api_parses_required_fields():
    doc = Document.from_api(FULL_DOC)

    assert doc.id == "doc-1"
    assert doc.title == "Some Article"
    assert doc.author == "Jane Doe"
    assert doc.location == "new"
    assert doc.url == "https://readwise.io/read/doc-1"
    assert doc.source_url == "https://example.com/article"
    assert doc.category == "article"
    assert doc.saved_at == datetime(2026, 9, 10, 8, 0, 0, tzinfo=UTC)


def test_from_api_handles_missing_optional_fields():
    data = {
        "id": "doc-2",
        "title": "Minimal Article",
        "location": "later",
        "saved_at": "2026-09-10T08:00:00Z",
    }

    doc = Document.from_api(data)

    assert doc.author is None
    assert doc.source_url is None
    assert doc.category is None
    assert doc.url is None


def test_from_api_defaults_title_when_blank():
    data = {**FULL_DOC, "title": ""}
    doc = Document.from_api(data)
    assert doc.title == "(untitled)"

    data_missing = dict(FULL_DOC)
    del data_missing["title"]
    doc_missing = Document.from_api(data_missing)
    assert doc_missing.title == "(untitled)"


def test_saved_at_parses_zulu_suffix():
    data = {**FULL_DOC, "saved_at": "2026-09-10T08:00:00Z"}
    doc = Document.from_api(data)

    assert doc.saved_at.tzinfo is not None
    assert doc.saved_at == datetime(2026, 9, 10, 8, 0, 0, tzinfo=UTC)
