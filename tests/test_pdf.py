from pathlib import Path
from unittest.mock import patch

from readwise_tools.pdf import render_pdf


@patch("readwise_tools.pdf.weasyprint.HTML")
def test_render_pdf_writes_output_via_weasyprint(mock_html_cls):
    output_path = Path("/tmp/gazette.pdf")

    render_pdf("<html><body>hi</body></html>", output_path)

    mock_html_cls.assert_called_once_with(string="<html><body>hi</body></html>")
    mock_html_cls.return_value.write_pdf.assert_called_once_with(str(output_path))
