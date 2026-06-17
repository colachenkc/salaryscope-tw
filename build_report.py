"""
Renders `report.md` into `r14944026.pdf`.

Pipeline: markdown -> HTML (+ light CSS) -> PDF via xhtml2pdf.

xhtml2pdf is pure-Python so we can produce the PDF on macOS without
WeasyPrint's GTK+/Pango native-library dependency. The trade-off is a
slightly weaker CSS subset, which the embedded stylesheet stays inside.
"""

from __future__ import annotations

import re
from pathlib import Path

import markdown
from xhtml2pdf import pisa

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "report.md"
DEST = ROOT / "r14944026.pdf"


CSS = """
@page {
    size: A4;
    margin: 2.2cm 2.0cm 2.2cm 2.0cm;
    @frame footer {
        -pdf-frame-content: footerContent;
        bottom: 1.0cm;
        margin-left: 2cm;
        margin-right: 2cm;
        height: 1cm;
    }
}
body {
    font-family: "Helvetica", "Arial", sans-serif;
    font-size: 10pt;
    line-height: 1.45;
    color: #1a1a1a;
}
h1 {
    font-size: 18pt;
    color: #0b2a5b;
    border-bottom: 2px solid #0b2a5b;
    padding-bottom: 4px;
    margin-top: 14pt;
    margin-bottom: 8pt;
}
h2 {
    font-size: 13.5pt;
    color: #0b2a5b;
    margin-top: 16pt;
    margin-bottom: 6pt;
}
h3 {
    font-size: 11.5pt;
    color: #1f3b73;
    margin-top: 12pt;
    margin-bottom: 4pt;
}
h4 {
    font-size: 10.5pt;
    color: #1f3b73;
    margin-top: 10pt;
    margin-bottom: 3pt;
}
p {
    margin: 5pt 0;
    text-align: left;
}
ul, ol { margin: 4pt 0 6pt 16pt; }
li { margin: 2pt 0; }

code {
    font-family: "Menlo", "Courier New", monospace;
    font-size: 9pt;
    background-color: #f1f3f8;
    color: #222;
    padding: 1px 3px;
    border-radius: 2px;
}
pre {
    font-family: "Menlo", "Courier New", monospace;
    font-size: 8.7pt;
    background-color: #f5f7fb;
    border: 1px solid #d7dceb;
    border-radius: 3px;
    padding: 8px 10px;
    white-space: pre-wrap;
}
table {
    border-collapse: collapse;
    width: 100%;
    margin: 6pt 0 8pt 0;
    font-size: 9pt;
}
th, td {
    border: 1px solid #c1c8d8;
    padding: 4px 6px;
    text-align: left;
    vertical-align: top;
}
th {
    background-color: #e6edfa;
    color: #0b2a5b;
}
blockquote {
    border-left: 3px solid #b6c4dc;
    margin: 6pt 0 6pt 0;
    padding: 2pt 8pt;
    color: #324562;
    font-style: italic;
}
img {
    max-width: 100%;
    margin: 8pt 0;
}
hr {
    border: none;
    border-top: 1px solid #c1c8d8;
    margin: 10pt 0;
}
.cover {
    margin-bottom: 14pt;
    padding: 8pt 0 8pt 0;
}
.cover .links {
    font-size: 9.5pt;
    color: #1f3b73;
}
.label {
    display: inline-block;
    font-weight: bold;
    color: #0b2a5b;
    margin-right: 4pt;
}
"""


FOOTER = (
    '<div id="footerContent" style="text-align:center;font-size:8pt;color:#7a8395;">'
    'SalaryScope TW &middot; r14944026 &middot; '
    'Big Data Systems Final Project &middot; <pdf:pagenumber/></div>'
)


def _md_to_html(md_text: str) -> str:
    md = markdown.Markdown(extensions=[
        "extra",       # tables, fenced code, footnotes, attr_list
        "sane_lists",
        "toc",
    ])
    body = md.convert(md_text)
    # xhtml2pdf is picky about self-closing tags inside <img>; ensure XHTML.
    body = re.sub(r"<img([^>]*?)\s*/?>", r"<img\1 />", body)
    return body


def build() -> Path:
    md_text = SRC.read_text(encoding="utf-8")
    body = _md_to_html(md_text)
    html = (
        "<!DOCTYPE html>\n"
        "<html><head><meta charset='UTF-8'>"
        "<style>" + CSS + "</style>"
        "</head><body>" + FOOTER + body + "</body></html>"
    )
    with DEST.open("wb") as fh:
        # xhtml2pdf resolves relative paths via link_callback's `base`
        # argument when we pass `path` instead of strings, so we change
        # cwd to the repo root.
        import os
        prev = os.getcwd()
        os.chdir(ROOT)
        try:
            result = pisa.CreatePDF(html, dest=fh)
        finally:
            os.chdir(prev)
    if result.err:
        raise SystemExit(f"PDF generation failed with {result.err} errors")
    return DEST


if __name__ == "__main__":
    out = build()
    print(f"wrote {out} ({out.stat().st_size // 1024} KB)")
