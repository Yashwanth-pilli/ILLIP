"""
PDF reader skill — extract text from PDFs in the workspace.
Uses pdfplumber if available, falls back to pypdf.
"""

from pathlib import Path
from app.skills.base_skill import BaseSKill
from app.config import settings


def _extract_pdfplumber(path: Path, max_pages: int) -> str:
    import pdfplumber
    pages = []
    with pdfplumber.open(str(path)) as pdf:
        for i, page in enumerate(pdf.pages[:max_pages]):
            text = page.extract_text() or ""
            if text.strip():
                pages.append(f"[Page {i+1}]\n{text.strip()}")
    return "\n\n".join(pages)


def _extract_pypdf(path: Path, max_pages: int) -> str:
    from pypdf import PdfReader
    reader = PdfReader(str(path))
    pages = []
    for i, page in enumerate(reader.pages[:max_pages]):
        text = page.extract_text() or ""
        if text.strip():
            pages.append(f"[Page {i+1}]\n{text.strip()}")
    return "\n\n".join(pages)


class PDFReaderSkill(BaseSKill):
    name = "read_pdf"
    description = (
        "Extract text from a PDF file in the workspace. "
        "Use to read documents, papers, manuals, or any PDF the user uploaded."
    )
    parameters = {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "PDF file path relative to workspace directory.",
            },
            "max_pages": {
                "type": "integer",
                "description": "Max pages to extract (default 10).",
            },
        },
        "required": ["path"],
    }

    async def execute(self, path: str, max_pages: int = 10, **_) -> str:
        workspace = settings.get_workspaces_path().resolve()
        target = (workspace / path).resolve()

        if not str(target).startswith(str(workspace)):
            return "Error: Access denied — path outside workspace."
        if not target.exists():
            return f"Error: File not found: {path}"
        if target.suffix.lower() != ".pdf":
            return f"Error: Not a PDF file: {path}"

        max_pages = min(int(max_pages), 50)

        try:
            try:
                text = _extract_pdfplumber(target, max_pages)
            except ImportError:
                try:
                    text = _extract_pypdf(target, max_pages)
                except ImportError:
                    return (
                        "Error: No PDF library installed. "
                        "Run: pip install pdfplumber"
                    )

            if not text.strip():
                return "No text extracted — PDF may be scanned (image-based). OCR not yet supported."

            char_limit = 8000
            if len(text) > char_limit:
                text = text[:char_limit] + f"\n\n[... truncated at {char_limit} chars]"
            return text

        except Exception as e:
            return f"Error reading PDF: {e}"
