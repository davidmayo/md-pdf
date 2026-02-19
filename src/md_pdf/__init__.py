"""md-pdf: Convert Markdown to PDF with GitHub-like rendering."""

import argparse
import logging
import sys
from pathlib import Path

import markdown
from pygments.formatters import HtmlFormatter
from weasyprint import HTML

# ---------------------------------------------------------------------------
# Markdown extensions
# ---------------------------------------------------------------------------

_MARKDOWN_EXTENSIONS = [
    "fenced_code",
    "codehilite",
    "tables",
    "nl2br",
    "sane_lists",
    "attr_list",
    "def_list",
    "footnotes",
    "toc",
    "smarty",
]

_MARKDOWN_EXTENSION_CONFIGS = {
    "codehilite": {
        "css_class": "codehilite",
        "linenums": False,
        "guess_lang": True,
    },
    "toc": {
        "permalink": False,
    },
}

# ---------------------------------------------------------------------------
# CSS — structural (mode-independent)
# ---------------------------------------------------------------------------

GITHUB_CSS_BASE = """
* {
    box-sizing: border-box;
    margin: 0;
    padding: 0;
}

body {
    font-family: -apple-system, "Segoe UI", Helvetica, Arial, sans-serif;
    font-size: 16px;
    line-height: 1.5;
    max-width: 860px;
    margin: 0 auto;
    padding: 40px 32px;
}

h1, h2, h3, h4, h5, h6 {
    margin-top: 24px;
    margin-bottom: 16px;
    font-weight: 600;
    line-height: 1.25;
}

h1 { font-size: 2em; padding-bottom: 0.3em; border-bottom-width: 1px; border-bottom-style: solid; }
h2 { font-size: 1.5em; padding-bottom: 0.3em; border-bottom-width: 1px; border-bottom-style: solid; }
h3 { font-size: 1.25em; }
h4 { font-size: 1em; }
h5 { font-size: 0.875em; }
h6 { font-size: 0.85em; }

p {
    margin-top: 0;
    margin-bottom: 16px;
}

a {
    text-decoration: none;
}

ul, ol {
    margin-top: 0;
    margin-bottom: 16px;
    padding-left: 2em;
}

li {
    margin-top: 4px;
}

ul ul, ul ol, ol ul, ol ol {
    margin-top: 0;
    margin-bottom: 0;
}

blockquote {
    margin: 0 0 16px 0;
    padding: 0 1em;
    border-left-width: 4px;
    border-left-style: solid;
}

blockquote > :first-child { margin-top: 0; }
blockquote > :last-child  { margin-bottom: 0; }

hr {
    height: 4px;
    padding: 0;
    margin: 24px 0;
    border: 0;
}

/* Inline code */
code {
    font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
    font-size: 85%;
    padding: 0.2em 0.4em;
    border-radius: 6px;
}

/* Code blocks */
pre {
    font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
    font-size: 85%;
    line-height: 1.45;
    border-radius: 6px;
    border-width: 1px;
    border-style: solid;
    padding: 16px;
    margin-top: 0;
    margin-bottom: 16px;
    white-space: pre-wrap;
    word-wrap: break-word;
}

pre code {
    display: block;
    font-size: 100%;
    padding: 0;
    margin: 0;
    background-color: transparent;
    border: 0;
    border-radius: 0;
    white-space: pre-wrap;
    word-break: normal;
}

.codehilite {
    margin-bottom: 16px;
    border-radius: 6px;
    border-width: 1px;
    border-style: solid;
    overflow: hidden;
}

.codehilite pre {
    margin: 0;
    border: 0;
    border-radius: 0;
    padding: 16px;
}

/* Tables */
table {
    width: 100%;
    border-collapse: collapse;
    border-spacing: 0;
    margin-top: 0;
    margin-bottom: 16px;
}

tr {
    border-top-width: 1px;
    border-top-style: solid;
}

th, td {
    padding: 6px 13px;
    border-width: 1px;
    border-style: solid;
    text-align: left;
    vertical-align: top;
}

th {
    font-weight: 600;
}

img {
    max-width: 100%;
    height: auto;
}

strong { font-weight: 600; }
em     { font-style: italic; }
del    { text-decoration: line-through; }

dt {
    font-weight: bold;
    margin-top: 8px;
}

dd {
    margin-left: 2em;
    margin-bottom: 4px;
}

.footnote {
    font-size: 85%;
    border-top-width: 1px;
    border-top-style: solid;
    margin-top: 32px;
    padding-top: 16px;
}

/* Page break helpers */
h1, h2, h3          { page-break-after: avoid; }
pre, blockquote, table { page-break-inside: avoid; }
"""

# ---------------------------------------------------------------------------
# CSS — light mode colors (DEFAULT)
# ---------------------------------------------------------------------------

GITHUB_CSS_LIGHT = """
body {
    background-color: #ffffff;
    color: #1f2328;
}

h1, h2, h3, h4, h5, h6 { color: #1f2328; }
h1, h2 { border-bottom-color: #d1d9e0; }
h6 { color: #59636e; }

a { color: #0969da; }

blockquote {
    border-left-color: #d1d9e0;
    color: #59636e;
}

hr { background-color: #d1d9e0; }

code {
    background-color: #f6f8fa;
    color: #1f2328;
}

pre {
    background-color: #f6f8fa;
    border-color: #d1d9e0;
    color: #1f2328;
}

.codehilite { border-color: #d1d9e0; }
.codehilite pre { background-color: #f6f8fa; color: #1f2328; }

tr { background-color: #ffffff; border-top-color: #d1d9e0; }
tr:nth-child(2n) { background-color: #f6f8fa; }
th, td { border-color: #d1d9e0; }
th { background-color: #f6f8fa; }

.footnote { border-top-color: #d1d9e0; }
"""

# ---------------------------------------------------------------------------
# CSS — dark mode colors
# ---------------------------------------------------------------------------

GITHUB_CSS_DARK = """
body {
    background-color: #0d1117;
    color: #e6edf3;
}

h1, h2, h3, h4, h5, h6 { color: #e6edf3; }
h1, h2 { border-bottom-color: #30363d; }
h6 { color: #8b949e; }

a { color: #4493f8; }

blockquote {
    border-left-color: #3d444d;
    color: #8b949e;
}

hr { background-color: #3d444d; }

code {
    background-color: #161b22;
    color: #e6edf3;
}

pre {
    background-color: #0d1117;
    border-color: #30363d;
    color: #e6edf3;
}

.codehilite { border-color: #30363d; }
.codehilite pre { background-color: #0d1117; color: #e6edf3; }

tr { background-color: #0d1117; border-top-color: #30363d; }
tr:nth-child(2n) { background-color: #161b22; }
th, td { border-color: #30363d; }
th { background-color: #161b22; }

.footnote { border-top-color: #30363d; }
"""

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_pygments_css(mode: str) -> str:
    """Generate Pygments CSS for the given mode."""
    style = "default" if mode == "LIGHT" else "github-dark"
    formatter = HtmlFormatter(style=style, cssclass="codehilite")
    return formatter.get_style_defs(".codehilite")


def _build_html(body_html: str, pygments_css: str, mode: str, size: str, margin: float) -> str:
    """Assemble a complete HTML document with all styles inlined."""
    theme_css = GITHUB_CSS_LIGHT if mode == "LIGHT" else GITHUB_CSS_DARK
    page_size = "letter" if size == "LETTER" else "A4"
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<style>@page {{ size: {page_size}; margin: {margin}in; }}</style>
<style>{GITHUB_CSS_BASE}</style>
<style>{theme_css}</style>
<style>{pygments_css}</style>
</head>
<body>
{body_html}
</body>
</html>"""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def convert(
    input_path: str | Path,
    output_path: str | Path,
    *,
    mode: str = "LIGHT",
    size: str = "LETTER",
    margin: float = 0.5,
) -> None:
    """Convert a Markdown file to PDF.

    Args:
        input_path: Path to the source .md file.
        output_path: Path to write the output .pdf file.
        mode: Color mode — "LIGHT" (default) or "DARK".
        size: Page size — "LETTER" (default) or "A4".
        margin: Page margin in inches (default: 0.5).
    """
    input_path = Path(input_path)
    output_path = Path(output_path)

    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")

    md_text = input_path.read_text(encoding="utf-8")

    md = markdown.Markdown(
        extensions=_MARKDOWN_EXTENSIONS,
        extension_configs=_MARKDOWN_EXTENSION_CONFIGS,
    )
    body_html = md.convert(md_text)

    pygments_css = _get_pygments_css(mode)
    full_html = _build_html(body_html, pygments_css, mode, size, margin)

    HTML(
        string=full_html,
        base_url=str(input_path.parent),
    ).write_pdf(str(output_path))


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    logging.getLogger("weasyprint").setLevel(logging.ERROR)

    parser = argparse.ArgumentParser(
        prog="md-pdf",
        description="Convert Markdown to PDF with GitHub-like rendering.",
    )
    parser.add_argument(
        "input",
        metavar="FILE",
        help="Path to the Markdown file to convert",
    )
    parser.add_argument(
        "--output", "-o",
        metavar="OUTPUT",
        default=None,
        help="Output PDF path (default: same name as input with .pdf extension)",
    )
    parser.add_argument(
        "--size",
        choices=["LETTER", "A4"],
        default="LETTER",
        help="Page size (default: LETTER)",
    )
    parser.add_argument(
        "--mode",
        choices=["LIGHT", "DARK"],
        default="LIGHT",
        help="Color mode (default: LIGHT)",
    )
    parser.add_argument(
        "--margin",
        type=float,
        default=0.5,
        metavar="INCHES",
        help="Page margin in inches (default: 0.5)",
    )

    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output) if args.output else input_path.with_suffix(".pdf")

    try:
        convert(input_path, output_path, mode=args.mode, size=args.size, margin=args.margin)
        print(f"PDF written to: {output_path}", file=sys.stderr)
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Conversion failed: {e}", file=sys.stderr)
        sys.exit(1)
