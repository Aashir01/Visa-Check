"""Text extraction from PDFs and images.

Strategy, cheapest-first:

1. **PDF text layer.** Most bank statements, e-tickets and insurance
   certificates are digitally generated. ``pdfplumber`` reads them exactly,
   for free, with none of Tesseract's transcription errors.
2. **Tesseract.** Scans and phone photos get rasterised (``pypdfium2``, no
   system poppler needed) and OCR'd.
3. **Claude vision** (opt-in). Tesseract is genuinely weak on passport MRZ
   bands and skewed phone photos. A corridor whose accuracy matters more than
   its token cost can set ``ocr.provider = "claude_vision"`` in its rule pack.

Every provider returns the same :class:`OcrResult`, so swapping engines is a
config change, not a code change.
"""

from __future__ import annotations

import io
import logging
import re
from dataclasses import dataclass, field

from ..config import settings

log = logging.getLogger(__name__)

IMAGE_MIMES = {"image/jpeg", "image/jpg", "image/png", "image/webp", "image/heic"}
PDF_MIMES = {"application/pdf"}


@dataclass
class OcrPage:
    page: int
    text: str
    confidence: float | None = None
    source: str = "tesseract"


@dataclass
class OcrResult:
    text: str
    pages: list[OcrPage] = field(default_factory=list)
    engine: str = "tesseract"
    confidence: float = 0.0
    page_count: int = 0
    error: str | None = None

    @property
    def has_text(self) -> bool:
        return len(self.text.strip()) >= 20


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------


def _clean(text: str) -> str:
    text = text.replace("\x00", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _pdf_text_layer(path) -> list[OcrPage]:
    """Read an existing text layer. Empty list means the PDF is a scan."""
    import pdfplumber

    pages: list[OcrPage] = []
    try:
        with pdfplumber.open(str(path)) as pdf:
            for i, page in enumerate(pdf.pages, start=1):
                txt = page.extract_text() or ""
                pages.append(
                    OcrPage(page=i, text=_clean(txt), confidence=1.0, source="text_layer")
                )
    except Exception as exc:  # noqa: BLE001 - a broken PDF must not kill the run
        log.warning("pdfplumber failed on %s: %s", path, exc)
        return []
    return pages


def _render_pdf_pages(path, dpi: int) -> list["object"]:
    """Rasterise a PDF to PIL images without a system poppler dependency."""
    import pypdfium2 as pdfium

    scale = dpi / 72.0
    images = []
    doc = pdfium.PdfDocument(str(path))
    try:
        for idx in range(len(doc)):
            page = doc[idx]
            bitmap = page.render(scale=scale)
            images.append(bitmap.to_pil())
    finally:
        doc.close()
    return images


def _tesseract_image(img) -> tuple[str, float]:
    """OCR one PIL image. Returns (text, mean word confidence 0..1)."""
    import pytesseract
    from pytesseract import Output

    try:
        data = pytesseract.image_to_data(
            img,
            lang=settings.tesseract_lang,
            output_type=Output.DICT,
            timeout=settings.tesseract_timeout_s,
        )
    except Exception as exc:  # noqa: BLE001
        log.warning("tesseract failed: %s", exc)
        return "", 0.0

    words, confs = [], []
    for word, conf in zip(data.get("text", []), data.get("conf", []), strict=False):
        if not word or not word.strip():
            continue
        words.append(word)
        try:
            c = float(conf)
        except (TypeError, ValueError):
            continue
        if c >= 0:
            confs.append(c)

    text = _clean(" ".join(words))
    confidence = (sum(confs) / len(confs) / 100.0) if confs else 0.0
    return text, confidence


# --------------------------------------------------------------------------
# providers
# --------------------------------------------------------------------------


class TesseractProvider:
    name = "tesseract"

    def extract(self, path, mime: str) -> OcrResult:
        mime = (mime or "").lower()
        if mime in PDF_MIMES or str(path).lower().endswith(".pdf"):
            return self._pdf(path)
        return self._image(path)

    def _pdf(self, path) -> OcrResult:
        layer = _pdf_text_layer(path)
        good = [p for p in layer if len(p.text) >= settings.text_layer_min_chars]

        # A born-digital PDF: use the text layer verbatim and skip OCR entirely.
        if layer and len(good) >= max(1, len(layer) // 2):
            text = _clean("\n\n".join(p.text for p in layer))
            return OcrResult(
                text=text,
                pages=layer,
                engine="pdf_text_layer",
                confidence=1.0,
                page_count=len(layer),
            )

        # Scanned PDF — rasterise and OCR, keeping any partial text layer.
        try:
            images = _render_pdf_pages(path, settings.ocr_raster_dpi)
        except Exception as exc:  # noqa: BLE001
            log.warning("PDF rasterisation failed for %s: %s", path, exc)
            if layer:
                text = _clean("\n\n".join(p.text for p in layer))
                return OcrResult(
                    text=text,
                    pages=layer,
                    engine="pdf_text_layer",
                    confidence=0.5,
                    page_count=len(layer),
                )
            return OcrResult(text="", engine="tesseract", error=str(exc))

        pages: list[OcrPage] = []
        for i, img in enumerate(images, start=1):
            txt, conf = _tesseract_image(_prepare(img))
            # Prefer the text layer for this page when it beat the OCR.
            existing = next((p for p in layer if p.page == i), None)
            if existing and len(existing.text) > len(txt):
                pages.append(existing)
            else:
                pages.append(OcrPage(page=i, text=txt, confidence=conf))

        confs = [p.confidence for p in pages if p.confidence is not None]
        return OcrResult(
            text=_clean("\n\n".join(p.text for p in pages)),
            pages=pages,
            engine="tesseract",
            confidence=(sum(confs) / len(confs)) if confs else 0.0,
            page_count=len(pages),
        )

    def _image(self, path) -> OcrResult:
        from PIL import Image

        try:
            with Image.open(path) as img:
                txt, conf = _tesseract_image(_prepare(img))
        except Exception as exc:  # noqa: BLE001
            log.warning("image OCR failed for %s: %s", path, exc)
            return OcrResult(text="", engine="tesseract", error=str(exc))

        return OcrResult(
            text=txt,
            pages=[OcrPage(page=1, text=txt, confidence=conf)],
            engine="tesseract",
            confidence=conf,
            page_count=1,
        )


def _prepare(img):
    """Greyscale + upscale small images. Cheap wins for Tesseract accuracy."""
    from PIL import Image

    if img.mode not in ("L", "RGB"):
        img = img.convert("RGB")
    img = img.convert("L")
    w, h = img.size
    if max(w, h) < 1400:
        factor = 1400 / max(w, h)
        img = img.resize((int(w * factor), int(h * factor)), Image.LANCZOS)
    return img


class ClaudeVisionProvider:
    """Transcribe pages with Claude. Accurate on phone photos, costs tokens."""

    name = "claude_vision"
    MAX_PAGES = 6

    def __init__(self, llm=None):
        from .llm import LlmClient

        self.llm = llm or LlmClient()

    def extract(self, path, mime: str) -> OcrResult:
        if not self.llm.available:
            return TesseractProvider().extract(path, mime)

        images = self._as_images(path, mime)
        if not images:
            return TesseractProvider().extract(path, mime)

        pages: list[OcrPage] = []
        for i, img in enumerate(images[: self.MAX_PAGES], start=1):
            text = self.llm.transcribe_image(self._png_bytes(img))
            pages.append(
                OcrPage(page=i, text=_clean(text or ""), confidence=0.9, source="claude")
            )

        joined = _clean("\n\n".join(p.text for p in pages))
        if not joined:
            return TesseractProvider().extract(path, mime)

        return OcrResult(
            text=joined,
            pages=pages,
            engine="claude_vision",
            confidence=0.9,
            page_count=len(pages),
        )

    def _as_images(self, path, mime: str) -> list:
        from PIL import Image

        if (mime or "").lower() in PDF_MIMES or str(path).lower().endswith(".pdf"):
            try:
                return _render_pdf_pages(path, 150)
            except Exception:  # noqa: BLE001
                return []
        try:
            img = Image.open(path)
            img.load()
            return [img]
        except Exception:  # noqa: BLE001
            return []

    @staticmethod
    def _png_bytes(img) -> bytes:
        if img.mode not in ("RGB", "L"):
            img = img.convert("RGB")
        # Keep the long edge at 1568px — Anthropic's no-downscale threshold.
        w, h = img.size
        if max(w, h) > 1568:
            from PIL import Image as _I

            f = 1568 / max(w, h)
            img = img.resize((int(w * f), int(h * f)), _I.LANCZOS)
        buf = io.BytesIO()
        img.save(buf, format="PNG", optimize=True)
        return buf.getvalue()


def get_provider(name: str | None = None):
    choice = (name or settings.ocr_provider or "tesseract").lower()
    if choice == "claude_vision":
        return ClaudeVisionProvider()
    return TesseractProvider()
