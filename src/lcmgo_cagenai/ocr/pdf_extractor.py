"""
PDF text extractor using pdfplumber.

Extracts text directly from text-based PDFs without OCR.
Detects if a PDF is scanned (image-based) vs text-based.
"""

import logging
from pathlib import Path

import pdfplumber

logger = logging.getLogger(__name__)


def extract_pdf_text(file_path: str | Path) -> tuple[str, int]:
    """
    Extract text from a text-based PDF.

    Uses pdfplumber for accurate text extraction including
    tables and complex layouts.

    Args:
        file_path: Path to the PDF file

    Returns:
        Tuple of (extracted_text, page_count)

    Example:
        text, pages = extract_pdf_text("resume.pdf")
        print(f"Extracted {len(text)} chars from {pages} pages")
    """
    path = Path(file_path)
    logger.info(f"Extracting PDF text: {path.name}")

    text_parts = []
    page_count = 0

    with pdfplumber.open(path) as pdf:
        page_count = len(pdf.pages)

        for i, page in enumerate(pdf.pages):
            # Extract text from page
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)

            # Also extract tables
            tables = page.extract_tables()
            for table in tables:
                table_text = _format_table(table)
                if table_text:
                    text_parts.append(table_text)

            logger.debug(f"Page {i + 1}: extracted {len(page_text or '')} chars")

    full_text = "\n\n".join(text_parts)
    logger.info(
        f"Extracted {len(full_text)} characters from {page_count} pages "
        f"in {path.name}"
    )

    return full_text, page_count


def _format_table(table: list[list[str | None]]) -> str:
    """
    Format a table as text with column separation.

    Args:
        table: 2D list of cell values

    Returns:
        Formatted table as string
    """
    if not table:
        return ""

    rows = []
    for row in table:
        # Replace None with empty string
        cells = [str(cell) if cell else "" for cell in row]
        # Join cells with pipe separator
        rows.append(" | ".join(cells))

    return "\n".join(rows)


def needs_ocr(file_path: str | Path, min_text_length: int = 100) -> bool:
    """
    Check if a PDF needs OCR (is scanned/image-based).

    Analyzes the PDF to determine if it contains extractable text
    or if it's a scanned document requiring OCR.

    Args:
        file_path: Path to the PDF file
        min_text_length: Minimum chars to consider as having text

    Returns:
        True if PDF needs OCR, False if text can be extracted directly

    Example:
        if needs_ocr("document.pdf"):
            # Use triple OCR
            result = await triple_ocr.extract(file_path)
        else:
            # Direct extraction
            text, _ = extract_pdf_text(file_path)
    """
    path = Path(file_path)

    try:
        with pdfplumber.open(path) as pdf:
            total_text = ""

            # Check first few pages
            for page in pdf.pages[:3]:
                text = page.extract_text()
                if text:
                    total_text += text.strip()

                # Early exit if we have enough text
                if len(total_text) >= min_text_length:
                    logger.debug(f"{path.name}: Has extractable text (no OCR needed)")
                    return False

            # Not enough text found
            logger.debug(f"{path.name}: Needs OCR (insufficient text)")
            return True

    except Exception as e:
        logger.warning(f"Error checking PDF: {e}, assuming OCR needed")
        return True


def extract_pdf_with_structure(file_path: str | Path) -> dict:
    """
    Extract text from PDF with structural information.

    Preserves page boundaries and table structures.
    Useful for section parsing and layout analysis.

    Args:
        file_path: Path to the PDF file

    Returns:
        Dictionary with structured content:
        {
            "pages": [
                {
                    "page_number": int,
                    "text": str,
                    "tables": [[[str, ...], ...], ...],
                    "width": float,
                    "height": float
                },
                ...
            ],
            "page_count": int,
            "metadata": dict
        }
    """
    path = Path(file_path)

    result = {"pages": [], "page_count": 0, "metadata": {}}

    with pdfplumber.open(path) as pdf:
        result["page_count"] = len(pdf.pages)
        result["metadata"] = pdf.metadata or {}

        for i, page in enumerate(pdf.pages):
            page_data = {
                "page_number": i + 1,
                "text": page.extract_text() or "",
                "tables": page.extract_tables() or [],
                "width": page.width,
                "height": page.height,
            }
            result["pages"].append(page_data)

    return result


def get_pdf_metadata(file_path: str | Path) -> dict:
    """
    Get PDF metadata.

    Args:
        file_path: Path to the PDF file

    Returns:
        Dictionary with PDF metadata (title, author, creation date, etc.)
    """
    path = Path(file_path)

    with pdfplumber.open(path) as pdf:
        return {
            "page_count": len(pdf.pages),
            "metadata": pdf.metadata or {},
        }
