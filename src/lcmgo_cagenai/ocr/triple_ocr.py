"""
Triple OCR Engine: Claude Vision + Tesseract + AWS Textract.

Runs three OCR engines in parallel for maximum accuracy on scanned
documents and images. Uses voting and confidence weighting to produce
the final result.

Architecture:
    Document -> [Claude Vision, Tesseract, Textract] -> Fusion Engine -> Result

Fusion Strategy:
    - 3/3 agreement (>90%): High confidence, weighted merge
    - 2/3 agreement (>70%): Medium confidence, majority vote
    - No agreement (<70%): Claude arbitration

Greek language support: ell+eng for Tesseract, Claude handles Greek natively.
"""

import asyncio
import base64
import io
import logging
import time
from dataclasses import dataclass, field
from difflib import SequenceMatcher
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import boto3

logger = logging.getLogger(__name__)


@dataclass
class OCRResult:
    """Result from a single OCR engine."""

    engine: str
    text: str
    confidence: float
    duration_ms: int
    error: str | None = None


@dataclass
class FusionResult:
    """Combined result from triple OCR with fusion."""

    final_text: str
    final_confidence: float
    agreement_rate: float
    arbitration_needed: bool
    source_attribution: dict = field(default_factory=dict)
    individual_results: list[OCRResult] = field(default_factory=list)


class TripleOCRExtractor:
    """
    Extract text using three OCR engines in parallel with fusion.

    Combines Claude Vision (high accuracy, expensive), Tesseract (free, local),
    and AWS Textract (AWS native, good accuracy) for maximum reliability.

    Greek language support is built-in.
    """

    # Bedrock model IDs for EU region
    CLAUDE_MODEL_ID = "eu.anthropic.claude-sonnet-4-5-20250929-v1:0"
    CLAUDE_ARBITRATION_MODEL_ID = "eu.anthropic.claude-haiku-4-5-20251001-v1:0"

    # Tesseract languages
    TESSERACT_LANG = "ell+eng"

    def __init__(
        self,
        bedrock_client: "boto3.client | None" = None,
        textract_client: "boto3.client | None" = None,
        region: str = "eu-north-1",
    ):
        """
        Initialize Triple OCR extractor.

        Args:
            bedrock_client: Optional boto3 Bedrock runtime client
            textract_client: Optional boto3 Textract client
            region: AWS region for clients
        """
        self.region = region
        self._bedrock = bedrock_client
        self._textract = textract_client

    @property
    def bedrock(self):
        """Lazy-load Bedrock client."""
        if self._bedrock is None:
            import boto3

            self._bedrock = boto3.client("bedrock-runtime", region_name=self.region)
        return self._bedrock

    @property
    def textract(self):
        """Lazy-load Textract client."""
        if self._textract is None:
            import boto3

            self._textract = boto3.client("textract", region_name=self.region)
        return self._textract

    async def extract(
        self, file_path: str | Path, correlation_id: str = ""
    ) -> FusionResult:
        """
        Extract text using triple OCR with fusion.

        Runs Claude Vision, Tesseract, and Textract in parallel,
        then fuses results using voting and confidence weighting.

        Args:
            file_path: Path to image or PDF document
            correlation_id: Optional ID for tracing

        Returns:
            FusionResult with fused text and confidence score

        Example:
            extractor = TripleOCRExtractor()
            result = await extractor.extract("scanned_cv.pdf")
            if result.final_confidence >= 0.8:
                process_cv(result.final_text)
        """
        path = Path(file_path)
        logger.info(f"Starting triple OCR for {path.name}, corr_id: {correlation_id}")

        # Run all three OCR engines in parallel
        results = await asyncio.gather(
            self._extract_claude_vision(path),
            self._extract_tesseract(path),
            self._extract_textract(path),
            return_exceptions=True,
        )

        # Process results
        ocr_results = []
        engines = ["claude_vision", "tesseract", "textract"]

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.warning(f"OCR engine {engines[i]} failed: {result}")
                ocr_results.append(
                    OCRResult(
                        engine=engines[i],
                        text="",
                        confidence=0.0,
                        duration_ms=0,
                        error=str(result),
                    )
                )
            else:
                ocr_results.append(result)

        # Fuse results
        fusion_result = await self._fuse_results(ocr_results, correlation_id)

        logger.info(
            f"Triple OCR complete for {path.name}: "
            f"confidence={fusion_result.final_confidence:.2f}, "
            f"agreement={fusion_result.agreement_rate:.2f}, "
            f"arbitration={fusion_result.arbitration_needed}"
        )

        return fusion_result

    async def _extract_claude_vision(self, file_path: Path) -> OCRResult:
        """Extract using Claude Vision (Sonnet 4.5)."""
        import json

        start = time.time()
        logger.debug(f"Starting Claude Vision extraction for {file_path.name}")

        try:
            # Prepare image for Claude Vision
            image_data, media_type = self._prepare_image(file_path)

            # Build request
            request_body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 8000,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": media_type,
                                    "data": image_data,
                                },
                            },
                            {
                                "type": "text",
                                "text": (
                                    "Extract ALL text from this CV/resume document. "
                                    "Preserve the original formatting and structure. "
                                    "Include both Greek (Ελληνικά) and English text. "
                                    "Return only the extracted text, nothing else."
                                ),
                            },
                        ],
                    }
                ],
            }

            # Invoke Bedrock
            response = self.bedrock.invoke_model(
                modelId=self.CLAUDE_MODEL_ID,
                body=json.dumps(request_body),
                contentType="application/json",
                accept="application/json",
            )

            response_body = json.loads(response["body"].read())
            text = response_body["content"][0]["text"]

            duration = int((time.time() - start) * 1000)

            return OCRResult(
                engine="claude_vision",
                text=text,
                confidence=0.95,  # Claude Vision is highly accurate
                duration_ms=duration,
            )

        except Exception as e:
            duration = int((time.time() - start) * 1000)
            logger.error(f"Claude Vision failed: {e}")
            return OCRResult(
                engine="claude_vision",
                text="",
                confidence=0.0,
                duration_ms=duration,
                error=str(e),
            )

    async def _extract_tesseract(self, file_path: Path) -> OCRResult:
        """Extract using Tesseract OCR with Greek support."""
        start = time.time()
        logger.debug(f"Starting Tesseract extraction for {file_path.name}")

        try:
            import pytesseract
            from PIL import Image

            # Handle PDFs vs images
            if file_path.suffix.lower() == ".pdf":
                from pdf2image import convert_from_path

                images = convert_from_path(file_path)
            else:
                images = [Image.open(file_path)]

            texts = []
            confidences = []

            for image in images:
                # Get text with confidence data
                data = pytesseract.image_to_data(
                    image,
                    lang=self.TESSERACT_LANG,
                    config="--psm 6",  # Assume uniform block of text
                    output_type=pytesseract.Output.DICT,
                )

                # Extract text
                page_text = pytesseract.image_to_string(
                    image, lang=self.TESSERACT_LANG, config="--psm 6"
                )
                texts.append(page_text)

                # Calculate average confidence
                confs = [int(c) for c in data["conf"] if int(c) > 0]
                if confs:
                    confidences.append(sum(confs) / len(confs) / 100)

            duration = int((time.time() - start) * 1000)
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.5

            return OCRResult(
                engine="tesseract",
                text="\n".join(texts),
                confidence=avg_confidence,
                duration_ms=duration,
            )

        except Exception as e:
            duration = int((time.time() - start) * 1000)
            logger.error(f"Tesseract failed: {e}")
            return OCRResult(
                engine="tesseract",
                text="",
                confidence=0.0,
                duration_ms=duration,
                error=str(e),
            )

    async def _extract_textract(self, file_path: Path) -> OCRResult:
        """Extract using AWS Textract."""
        start = time.time()
        logger.debug(f"Starting Textract extraction for {file_path.name}")

        try:
            # Read document bytes
            with open(file_path, "rb") as f:
                document_bytes = f.read()

            # Textract has a 5MB limit for synchronous API
            if len(document_bytes) > 5 * 1024 * 1024:
                raise ValueError("Document too large for Textract sync API (>5MB)")

            # Call Textract
            response = self.textract.detect_document_text(
                Document={"Bytes": document_bytes}
            )

            # Extract text blocks
            texts = []
            confidences = []

            for block in response.get("Blocks", []):
                if block["BlockType"] == "LINE":
                    texts.append(block["Text"])
                    confidences.append(block["Confidence"] / 100)

            duration = int((time.time() - start) * 1000)
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0.5

            return OCRResult(
                engine="textract",
                text="\n".join(texts),
                confidence=avg_confidence,
                duration_ms=duration,
            )

        except Exception as e:
            duration = int((time.time() - start) * 1000)
            logger.error(f"Textract failed: {e}")
            return OCRResult(
                engine="textract",
                text="",
                confidence=0.0,
                duration_ms=duration,
                error=str(e),
            )

    async def _fuse_results(
        self, results: list[OCRResult], correlation_id: str
    ) -> FusionResult:
        """Fuse three OCR results using voting and confidence weighting."""
        # Filter out failed results
        valid_results = [r for r in results if r.error is None and r.text]

        if len(valid_results) == 0:
            # All engines failed
            errors = [r.error for r in results if r.error]
            return FusionResult(
                final_text="",
                final_confidence=0.0,
                agreement_rate=0.0,
                arbitration_needed=False,
                source_attribution={},
                individual_results=results,
            )

        if len(valid_results) == 1:
            # Only one succeeded - use it with penalty
            result = valid_results[0]
            return FusionResult(
                final_text=result.text,
                final_confidence=result.confidence * 0.7,  # Penalize single source
                agreement_rate=0.0,
                arbitration_needed=False,
                source_attribution={result.engine: 1.0},
                individual_results=results,
            )

        # Calculate agreement rate
        agreement_rate = self._calculate_agreement(valid_results)

        if agreement_rate >= 0.90:
            # High agreement: use weighted average by confidence
            final_text = self._weighted_merge(valid_results)
            final_confidence = 0.95
            arbitration_needed = False
            source_attribution = self._calculate_attribution(valid_results, final_text)

        elif agreement_rate >= 0.70:
            # Medium agreement: use majority voting
            final_text = self._majority_vote(valid_results)
            final_confidence = 0.80
            arbitration_needed = False
            source_attribution = self._calculate_attribution(valid_results, final_text)

        else:
            # Low agreement: use Claude for arbitration
            final_text = await self._claude_arbitrate(valid_results, correlation_id)
            final_confidence = 0.70
            arbitration_needed = True
            source_attribution = {"claude_arbitration": 1.0}

        return FusionResult(
            final_text=final_text,
            final_confidence=final_confidence,
            agreement_rate=agreement_rate,
            arbitration_needed=arbitration_needed,
            source_attribution=source_attribution,
            individual_results=results,
        )

    def _calculate_agreement(self, results: list[OCRResult]) -> float:
        """Calculate character-level agreement between OCR results."""
        if len(results) < 2:
            return 1.0

        # Compare each pair
        ratios = []
        for i in range(len(results)):
            for j in range(i + 1, len(results)):
                ratio = SequenceMatcher(
                    None, results[i].text.lower(), results[j].text.lower()
                ).ratio()
                ratios.append(ratio)

        return sum(ratios) / len(ratios)

    def _weighted_merge(self, results: list[OCRResult]) -> str:
        """Merge texts weighted by confidence (use highest confidence)."""
        best = max(results, key=lambda r: r.confidence)
        return best.text

    def _majority_vote(self, results: list[OCRResult]) -> str:
        """Use majority voting for conflicting segments."""
        # For simplicity, use the result with highest confidence
        # A full implementation would do line-by-line voting
        return max(results, key=lambda r: r.confidence).text

    def _calculate_attribution(
        self, results: list[OCRResult], final_text: str
    ) -> dict[str, float]:
        """Calculate how much each engine contributed to final result."""
        attribution = {}
        for result in results:
            if result.text:
                similarity = SequenceMatcher(
                    None, result.text.lower(), final_text.lower()
                ).ratio()
                attribution[result.engine] = similarity

        # Normalize to sum to 1
        total = sum(attribution.values())
        if total > 0:
            attribution = {k: v / total for k, v in attribution.items()}

        return attribution

    async def _claude_arbitrate(
        self, results: list[OCRResult], correlation_id: str
    ) -> str:
        """Use Claude to resolve conflicts between OCR results."""
        import json

        logger.info(f"Using Claude arbitration for {correlation_id}")

        # Build arbitration prompt
        prompt = """Three OCR engines produced different results for the same document.
Analyze all three outputs and produce the most accurate combined text.
Focus on:
1. Correcting obvious OCR errors
2. Preserving Greek characters correctly
3. Maintaining document structure

Claude Vision result:
```
{claude_text}
```

Tesseract result:
```
{tesseract_text}
```

AWS Textract result:
```
{textract_text}
```

Produce the most accurate final text. Return ONLY the corrected text, no explanations."""

        claude_text = next(
            (r.text for r in results if r.engine == "claude_vision"), "N/A"
        )
        tesseract_text = next(
            (r.text for r in results if r.engine == "tesseract"), "N/A"
        )
        textract_text = next(
            (r.text for r in results if r.engine == "textract"), "N/A"
        )

        final_prompt = prompt.format(
            claude_text=claude_text[:3000],
            tesseract_text=tesseract_text[:3000],
            textract_text=textract_text[:3000],
        )

        try:
            request_body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 8000,
                "messages": [{"role": "user", "content": final_prompt}],
            }

            response = self.bedrock.invoke_model(
                modelId=self.CLAUDE_ARBITRATION_MODEL_ID,
                body=json.dumps(request_body),
                contentType="application/json",
                accept="application/json",
            )

            response_body = json.loads(response["body"].read())
            return response_body["content"][0]["text"]

        except Exception as e:
            logger.error(f"Claude arbitration failed: {e}")
            # Fall back to highest confidence result
            return max(results, key=lambda r: r.confidence).text

    def _prepare_image(self, file_path: Path) -> tuple[str, str]:
        """
        Prepare image for Claude Vision API.

        Converts PDF first page or image to base64.

        Args:
            file_path: Path to image or PDF

        Returns:
            Tuple of (base64_data, media_type)
        """
        from PIL import Image

        # Handle PDFs
        if file_path.suffix.lower() == ".pdf":
            from pdf2image import convert_from_path

            images = convert_from_path(file_path, first_page=1, last_page=1)
            if not images:
                raise ValueError("Could not convert PDF to image")
            image = images[0]
            media_type = "image/png"
        else:
            image = Image.open(file_path)
            # Determine media type
            format_map = {
                ".jpg": "image/jpeg",
                ".jpeg": "image/jpeg",
                ".png": "image/png",
                ".gif": "image/gif",
                ".bmp": "image/bmp",
            }
            media_type = format_map.get(file_path.suffix.lower(), "image/png")

        # Convert to bytes
        buffer = io.BytesIO()
        image.save(buffer, format="PNG")
        buffer.seek(0)

        # Encode to base64
        image_data = base64.standard_b64encode(buffer.read()).decode("utf-8")

        return image_data, media_type
