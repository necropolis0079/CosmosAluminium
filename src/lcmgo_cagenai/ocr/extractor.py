"""
Smart CV Document Extractor with optimized routing.

Routes documents to the appropriate extraction method:
- DOCX: Direct extraction (no OCR)
- Text-based PDF: Direct extraction (no OCR)
- Scanned PDF: Triple OCR (Claude Vision + Tesseract + Textract)
- Images (JPG/PNG): Triple OCR

Cost optimization: ~60% reduction for text-based documents.
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .triple_ocr import TripleOCRExtractor

logger = logging.getLogger(__name__)


class DocumentType(Enum):
    """Supported document types."""

    DOCX = "docx"
    PDF_TEXT = "pdf_text"
    PDF_SCANNED = "pdf_scanned"
    IMAGE = "image"
    UNSUPPORTED = "unsupported"


class ExtractionMethod(Enum):
    """Extraction method used."""

    DIRECT_DOCX = "direct_docx"
    DIRECT_PDF = "direct_pdf"
    TRIPLE_OCR = "triple_ocr"
    FAILED = "failed"


@dataclass
class ExtractionResult:
    """Result of document extraction."""

    text: str
    method: ExtractionMethod
    document_type: DocumentType
    confidence: float
    page_count: int = 1
    has_images: bool = False
    ocr_details: dict = field(default_factory=dict)
    error: str | None = None


class DocumentExtractor:
    """
    Smart document extractor with optimized routing.

    Automatically detects document type and routes to the most
    efficient extraction method.
    """

    # File extension mappings
    IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".tif"}
    DOCX_EXTENSIONS = {".docx"}
    PDF_EXTENSIONS = {".pdf"}
    TEXT_EXTENSIONS = {".txt", ".rtf"}

    # Minimum text length to consider PDF as text-based
    MIN_TEXT_LENGTH = 100

    def __init__(self, triple_ocr: "TripleOCRExtractor | None" = None):
        """
        Initialize extractor.

        Args:
            triple_ocr: Optional TripleOCRExtractor instance for OCR processing.
                       If not provided, will be created when needed.
        """
        self._triple_ocr = triple_ocr

    def detect_document_type(self, file_path: str | Path) -> DocumentType:
        """
        Detect the type of document and whether OCR is needed.

        Args:
            file_path: Path to the document file

        Returns:
            DocumentType indicating the document type
        """
        path = Path(file_path)
        ext = path.suffix.lower()

        if ext in self.IMAGE_EXTENSIONS:
            return DocumentType.IMAGE

        if ext in self.DOCX_EXTENSIONS:
            return DocumentType.DOCX

        if ext in self.PDF_EXTENSIONS:
            # Check if PDF has extractable text
            if self._pdf_has_text(path):
                return DocumentType.PDF_TEXT
            return DocumentType.PDF_SCANNED

        if ext in self.TEXT_EXTENSIONS:
            return DocumentType.PDF_TEXT  # Treat as text-based

        return DocumentType.UNSUPPORTED

    def _pdf_has_text(self, file_path: Path) -> bool:
        """
        Check if PDF has extractable text (not scanned).

        Args:
            file_path: Path to PDF file

        Returns:
            True if PDF has extractable text, False if scanned
        """
        try:
            import pdfplumber

            with pdfplumber.open(file_path) as pdf:
                total_text = ""
                # Check first 3 pages (or all if fewer)
                for page in pdf.pages[:3]:
                    text = page.extract_text()
                    if text:
                        total_text += text.strip()
                    # Early exit if we have enough text
                    if len(total_text) >= self.MIN_TEXT_LENGTH:
                        return True

                return len(total_text) >= self.MIN_TEXT_LENGTH

        except Exception as e:
            logger.warning(f"Error checking PDF text: {e}")
            return False

    async def extract(
        self, file_path: str | Path, correlation_id: str | None = None
    ) -> ExtractionResult:
        """
        Extract text from document using optimal method.

        Args:
            file_path: Path to the document file
            correlation_id: Optional ID for tracing

        Returns:
            ExtractionResult with extracted text and metadata
        """
        path = Path(file_path)
        doc_type = self.detect_document_type(path)

        logger.info(
            f"Extracting document: {path.name}, type: {doc_type.value}, "
            f"correlation_id: {correlation_id}"
        )

        try:
            if doc_type == DocumentType.DOCX:
                return await self._extract_docx(path)

            elif doc_type == DocumentType.PDF_TEXT:
                return await self._extract_pdf_text(path)

            elif doc_type in (DocumentType.PDF_SCANNED, DocumentType.IMAGE):
                return await self._extract_with_ocr(path, doc_type, correlation_id)

            else:
                return ExtractionResult(
                    text="",
                    method=ExtractionMethod.FAILED,
                    document_type=doc_type,
                    confidence=0.0,
                    error=f"Unsupported file type: {path.suffix}",
                )

        except Exception as e:
            logger.exception(f"Extraction failed for {path.name}")
            return ExtractionResult(
                text="",
                method=ExtractionMethod.FAILED,
                document_type=doc_type,
                confidence=0.0,
                error=str(e),
            )

    async def _extract_docx(self, file_path: Path) -> ExtractionResult:
        """Extract text from DOCX using python-docx."""
        from .docx_extractor import extract_docx

        text, has_images = extract_docx(file_path)

        return ExtractionResult(
            text=text,
            method=ExtractionMethod.DIRECT_DOCX,
            document_type=DocumentType.DOCX,
            confidence=1.0,  # Direct extraction is 100% accurate
            has_images=has_images,
        )

    async def _extract_pdf_text(self, file_path: Path) -> ExtractionResult:
        """Extract text from text-based PDF using pdfplumber."""
        from .pdf_extractor import extract_pdf_text

        text, page_count = extract_pdf_text(file_path)

        return ExtractionResult(
            text=text,
            method=ExtractionMethod.DIRECT_PDF,
            document_type=DocumentType.PDF_TEXT,
            confidence=1.0,  # Direct extraction is 100% accurate
            page_count=page_count,
        )

    async def _extract_with_ocr(
        self, file_path: Path, doc_type: DocumentType, correlation_id: str | None
    ) -> ExtractionResult:
        """Extract text using triple OCR pipeline."""
        if self._triple_ocr is None:
            from .triple_ocr import TripleOCRExtractor

            self._triple_ocr = TripleOCRExtractor()

        result = await self._triple_ocr.extract(
            file_path=file_path, correlation_id=correlation_id or ""
        )

        # Determine page count for PDFs
        page_count = 1
        if doc_type == DocumentType.PDF_SCANNED:
            try:
                import pdfplumber

                with pdfplumber.open(file_path) as pdf:
                    page_count = len(pdf.pages)
            except Exception:
                pass

        return ExtractionResult(
            text=result.final_text,
            method=ExtractionMethod.TRIPLE_OCR,
            document_type=doc_type,
            confidence=result.final_confidence,
            page_count=page_count,
            ocr_details={
                "agreement_rate": result.agreement_rate,
                "arbitration_needed": result.arbitration_needed,
                "source_attribution": result.source_attribution,
                "individual_results": [
                    {
                        "engine": r.engine,
                        "confidence": r.confidence,
                        "duration_ms": r.duration_ms,
                        "error": r.error,
                    }
                    for r in result.individual_results
                ],
            },
        )


# Convenience function for simple usage
async def extract_cv(
    file_path: str | Path, correlation_id: str | None = None
) -> ExtractionResult:
    """
    Extract text from a CV document.

    This is the main entry point for CV extraction. It automatically
    detects the document type and uses the optimal extraction method.

    Args:
        file_path: Path to the CV document
        correlation_id: Optional ID for tracing

    Returns:
        ExtractionResult with extracted text and metadata

    Example:
        result = await extract_cv("/path/to/cv.pdf")
        if result.confidence >= 0.8:
            process_cv(result.text)
    """
    extractor = DocumentExtractor()
    return await extractor.extract(file_path, correlation_id)
