from pathlib import Path

import weasyprint


def render_pdf(html: str, output_path: Path) -> None:
    weasyprint.HTML(string=html).write_pdf(str(output_path))
