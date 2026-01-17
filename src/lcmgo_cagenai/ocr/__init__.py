"""
Optimized CV Document Extraction Pipeline.

Triple OCR: Claude Vision + Tesseract + AWS Textract
Smart Routing: Direct extraction for DOCX/text PDFs, OCR only when needed.

Usage:
    from lcmgo_cagenai.ocr import extract_cv, DocumentExtractor

    # Simple usage
    result = await extract_cv("resume.pdf")
    print(result.text)
    print(f"Method: {result.method}, Confidence: {result.confidence}")

    # Advanced usage with custom OCR
    from lcmgo_cagenai.ocr import TripleOCRExtractor, DocumentExtractor

    ocr = TripleOCRExtractor(region="eu-north-1")
    extractor = DocumentExtractor(triple_ocr=ocr)
    result = await extractor.extract("scanned_cv.jpg")

Cost Optimization:
    - DOCX: ~$0 (direct extraction)
    - Text PDF: ~$0 (direct extraction)
    - Scanned PDF/Images: ~$0.015/page (triple OCR)
    - Average savings: ~60% compared to OCR-everything
"""

from .docx_extractor import extract_docx, extract_docx_with_structure
from .extractor import (
    DocumentExtractor,
    DocumentType,
    ExtractionMethod,
    ExtractionResult,
    extract_cv,
)
from .pdf_extractor import (
    extract_pdf_text,
    extract_pdf_with_structure,
    get_pdf_metadata,
    needs_ocr,
)
from .triple_ocr import FusionResult, OCRResult, TripleOCRExtractor

__all__ = [
    # Main entry point
    "extract_cv",
    # Extractor classes
    "DocumentExtractor",
    "TripleOCRExtractor",
    # Types and results
    "DocumentType",
    "ExtractionMethod",
    "ExtractionResult",
    "OCRResult",
    "FusionResult",
    # Utility functions
    "extract_docx",
    "extract_docx_with_structure",
    "extract_pdf_text",
    "extract_pdf_with_structure",
    "get_pdf_metadata",
    "needs_ocr",
]
