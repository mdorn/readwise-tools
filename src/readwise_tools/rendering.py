import importlib.resources

import jinja2
import markdownify

from readwise_tools.models import Document

_TEMPLATE_PACKAGE = "readwise_tools"
_TEMPLATE_PATHS: dict[str, tuple[str, str]] = {
    "markdown": ("templates", "article.md"),
    "html": ("templates", "article.html"),
}


def render_document(
    document: Document, output_format: str, *, template_source: str | None = None
) -> str:
    if template_source is None:
        template_source = _load_template(output_format)

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


def _html_to_markdown(html: str | None) -> str:
    if not html:
        return ""
    return markdownify.markdownify(html, heading_style="ATX").strip()


def _load_template(output_format: str) -> str:
    resource = importlib.resources.files(_TEMPLATE_PACKAGE)
    for part in _TEMPLATE_PATHS[output_format]:
        resource = resource / part
    return resource.read_text(encoding="utf-8")
