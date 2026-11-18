"""Document and PDF reader/extractor for JARVIS (2.5, 7.2, 7.3)."""

import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path

TEXT_EXTENSIONS = {
    ".txt", ".md", ".markdown", ".py", ".js", ".ts", ".jsx", ".tsx",
    ".json", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".conf", ".env",
    ".csv", ".tsv", ".html", ".htm", ".css", ".xml", ".sql", ".log",
    ".sh", ".bash", ".ps1", ".bat", ".c", ".cpp", ".h", ".hpp",
    ".java", ".go", ".rs", ".rb", ".php", ".swift", ".kt", ".r",
}

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp"}


def read_pdf_text(file_path: str, max_pages: int = 60) -> tuple[str, int]:
    """Extract text from a PDF file using PySide6's native QPdfDocument."""
    from PySide6.QtPdf import QPdfDocument

    doc = QPdfDocument(None)
    status = doc.load(str(file_path))
    if status != QPdfDocument.Error.None_:
        raise RuntimeError(f"Could not open PDF file (error: {status}).")

    page_count = doc.pageCount()
    pages_to_read = min(page_count, max_pages)
    chunks = []
    for idx in range(pages_to_read):
        page_text = doc.getAllText(idx).text().strip()
        if page_text:
            chunks.append(f"--- Page {idx + 1} ---\n{page_text}")

    doc.close()
    text = "\n\n".join(chunks)
    if page_count > max_pages:
        text += f"\n\n[Truncated after {max_pages} of {page_count} pages]"
    return text, page_count


def read_docx_text(file_path: str) -> str:
    """Extract paragraph text from a .docx file using only Python stdlib."""
    with zipfile.ZipFile(file_path, "r") as zf:
        xml_bytes = zf.read("word/document.xml")
    root = ET.fromstring(xml_bytes)
    paragraphs = []
    for para in root.iter():
        if para.tag.endswith("}p"):
            texts = [node.text for node in para.iter() if node.tag.endswith("}t") and node.text]
            if texts:
                paragraphs.append("".join(texts))
    return "\n".join(paragraphs)


def extract_document_text(file_path: str, max_chars: int = 24000) -> dict:
    """Read supported document formats (.pdf, .docx, text/code/csv/json/log) and return metadata + text."""
    path = Path(file_path)
    if not path.is_file():
        raise FileNotFoundError(f"File not found: {file_path}")

    ext = path.suffix.lower()
    meta = {
        "name": path.name,
        "path": str(path),
        "extension": ext,
        "size_bytes": path.stat().st_size,
        "pages": None,
        "truncated": False,
    }

    if ext == ".pdf":
        text, pages = read_pdf_text(str(path))
        meta["pages"] = pages
    elif ext == ".docx":
        text = read_docx_text(str(path))
    elif ext in TEXT_EXTENSIONS or meta["size_bytes"] < 512_000:
        text = path.read_text(encoding="utf-8", errors="replace")
    else:
        raise ValueError(f"Unsupported binary file format: {ext}")

    if len(text) > max_chars:
        text = text[:max_chars] + "\n\n[...Document content truncated for AI context window...]"
        meta["truncated"] = True

    meta["text"] = text
    meta["char_count"] = len(text)
    meta["word_count"] = len(text.split())
    return meta

