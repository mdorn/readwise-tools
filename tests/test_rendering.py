from datetime import UTC, datetime

from readwise_tools.models import Document
from readwise_tools.rendering import render_document


def _doc(**overrides) -> Document:
    fields = {
        "id": "doc-1",
        "title": "Some Article",
        "author": "Jane Doe",
        "location": "new",
        "saved_at": datetime(2026, 9, 10, tzinfo=UTC),
        "url": "https://readwise.io/read/doc-1",
        "source_url": "https://example.com/article",
        "category": "article",
        "published_date": datetime(2026, 8, 1, tzinfo=UTC),
        "html_content": "<h1>Heading</h1><p>Some <strong>bold</strong> text.</p>",
    }
    fields.update(overrides)
    return Document(**fields)


def test_render_document_fills_all_placeholders():
    output = render_document(_doc(), "markdown")

    assert "Some Article" in output
    assert "Jane Doe" in output
    assert "2026-08-01" in output
    assert "https://example.com/article" in output
    assert "bold" in output


def test_render_document_handles_missing_optional_fields_gracefully():
    doc = _doc(
        author=None,
        published_date=None,
        url=None,
        source_url=None,
        html_content=None,
    )

    output = render_document(doc, "markdown")

    assert "None" not in output


def test_render_document_converts_html_to_markdown():
    output = render_document(_doc(), "markdown")

    assert "# Heading" in output
    assert "**bold**" in output


def test_render_document_uses_injected_template_source():
    output = render_document(_doc(), "markdown", template_source="TITLE: {{ title }}")

    assert output == "TITLE: Some Article"


def test_render_document_prefers_source_url_over_reader_url():
    doc = _doc(
        url="https://readwise.io/read/doc-1",
        source_url="https://example.com/article",
    )

    output = render_document(doc, "markdown")

    assert "https://example.com/article" in output
    assert "https://readwise.io/read/doc-1" not in output


def test_render_document_falls_back_to_reader_url_when_source_url_missing():
    doc = _doc(url="https://readwise.io/read/doc-1", source_url=None)

    output = render_document(doc, "markdown")

    assert "https://readwise.io/read/doc-1" in output


def test_render_document_loads_real_packaged_template_regardless_of_cwd(
    monkeypatch, tmp_path
):
    monkeypatch.chdir(tmp_path)

    output = render_document(_doc(), "markdown")

    assert "Some Article" in output
    assert "# Heading" in output


def test_render_document_html_output_uses_html_template():
    output = render_document(_doc(), "html")

    assert "<h2>Some Article</h2>" in output
    assert "<strong>Jane Doe</strong>" in output
    assert "<strong>2026-08-01</strong>" in output
    assert "<strong>https://example.com/article</strong>" in output
    assert "<h1>Heading</h1>" in output
    assert "<strong>bold</strong>" in output
    assert "# Heading" not in output
    assert "**bold**" not in output


def test_render_document_html_output_handles_missing_fields():
    doc = _doc(
        author=None,
        published_date=None,
        url=None,
        source_url=None,
        html_content=None,
    )

    output = render_document(doc, "html")

    assert "None" not in output


def test_render_document_html_output_loads_real_packaged_template_regardless_of_cwd(
    monkeypatch, tmp_path
):
    monkeypatch.chdir(tmp_path)

    output = render_document(_doc(), "html")

    assert "<h2>Some Article</h2>" in output
    assert "<h1>Heading</h1>" in output
