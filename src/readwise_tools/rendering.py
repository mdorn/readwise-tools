import dataclasses
import importlib.resources
from collections.abc import Iterable

import jinja2
import markdownify
from bs4 import BeautifulSoup

from readwise_tools.models import Document

_TEMPLATE_PACKAGE = "readwise_tools"
_TEMPLATE_PATHS: dict[str, tuple[str, str]] = {
    "markdown": ("templates", "article.md"),
    "html": ("templates", "article.html"),
}
_GAZETTE_TEMPLATE_PATH = ("templates", "gazette.html")


def render_document(
    document: Document, output_format: str, *, template_source: str | None = None
) -> str:
    if template_source is None:
        template_source = _read_resource(*_TEMPLATE_PATHS[output_format])

    template = jinja2.Template(template_source)
    return template.render(
        title=document.title,
        author=document.author or "",
        date_published=(
            document.published_date.date().isoformat()
            if document.published_date
            else ""
        ),
        url=document.source_url or document.url or "",
        body=(
            _html_to_markdown(document.html_content)
            if output_format == "markdown"
            else document.html_content or ""
        ),
    )


def render_gazette(
    documents: Iterable[Document], *, template_source: str | None = None
) -> str:
    items_html = "\n<hr />\n".join(
        render_document(_without_images(doc), "html") for doc in documents
    )
    if template_source is None:
        template_source = _read_resource(*_GAZETTE_TEMPLATE_PATH)

    return jinja2.Template(template_source).render(items=items_html)


def _html_to_markdown(html: str | None) -> str:
    if not html:
        return ""
    return markdownify.markdownify(html, heading_style="ATX").strip()


def _without_images(document: Document) -> Document:
    if not document.html_content:
        return document
    return dataclasses.replace(
        document, html_content=_strip_images(document.html_content)
    )


def _strip_images(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for img in soup.find_all("img"):
        alt = (img.get("alt") or "").strip()
        figure = img.find_parent("figure")
        if figure is not None:
            figcaption = figure.find("figcaption")
            caption = figcaption.get_text(strip=True) if figcaption else ""
            text = alt or caption
            figure.replace_with(f"[{text}]" if text else "[image removed]")
        else:
            img.replace_with(f"[{alt}]" if alt else "[image removed]")
    return str(soup)


def _read_resource(*parts: str) -> str:
    resource = importlib.resources.files(_TEMPLATE_PACKAGE)
    for part in parts:
        resource = resource / part
    return resource.read_text(encoding="utf-8")
