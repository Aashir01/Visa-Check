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
    """OCR one PIL image. Returns (text, mean word confidence 0..1).

    Line structure is reconstructed from Tesseract's block/paragraph/line
    indices rather than joining every word with a space. This matters more
    than it looks: a passport MRZ is *defined* by being two fixed-width lines,
    so flattening the page into one line makes the MRZ — and with it the only
    check-digit-verifiable identity data in the bundle — impossible to find.
    """
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

    lines: dict[tuple[int, int, int, int], list[str]] = {}
    confs: list[float] = []
    n = len(data.get("text", []))

    for i in range(n):
        word = (data["text"][i] or "").strip()
        if not word:
            continue
        key = (
            data.get("page_num", [0] * n)[i],
            data.get("block_num", [0] * n)[i],
            data.get("par_num", [0] * n)[i],
            data.get("line_num", [0] * n)[i],
        )
        lines.setdefault(key, []).append(word)
        try:
            c = float(data.get("conf", [])[i])
        except (TypeError, ValueError, IndexError):
            continue
        if c >= 0:
            confs.append(c)

    text = _clean("\n".join(" ".join(words) for _, words in sorted(lines.items())))
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
    """Greyscale + upscale small images. Cheap wins for Tesseract accuracy.

    Deliberately minimal. Measured against simulated phone photos, CLAHE,
    denoising, sharpening and adaptive thresholding all made recognition
    *worse* — they amplify JPEG noise faster than they recover strokes. Plain
    upscaling to ~1800px was the only transform that helped consistently.
    """
    from PIL import Image

    if img.mode not in ("L", "RGB"):
        img = img.convert("RGB")
    img = img.convert("L")
    w, h = img.size
    if max(w, h) < 1800:
        factor = 1800 / max(w, h)
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


class PaddleOcrProvider:
    """PP-OCR: detection + recognition models, self-hosted, no per-page cost.

    Chosen over Tesseract where accuracy on phone photos matters: PP-OCR
    detects text regions first and recognises each crop, so rotation, skew and
    uneven lighting degrade it far less than Tesseract's page-level pass.
    Models are a fixed download; inference runs on CPU, which keeps the
    marginal cost of a check at zero.

    Line structure is rebuilt from the detected boxes rather than taken from
    the model's output order, because the passport MRZ is only findable as two
    fixed-width lines.
    """

    name = "paddleocr"
    _engine = None  # models are expensive to load; share one per process

    def __init__(self, lang: str | None = None):
        self.lang = lang or "en"

    @classmethod
    def available(cls) -> bool:
        try:
            import paddleocr  # noqa: F401
        except Exception:  # noqa: BLE001
            return False
        return True

    def _get_engine(self):
        if PaddleOcrProvider._engine is None:
            from paddleocr import PaddleOCR

            # Orientation + unwarping are what buy the robustness on photos.
            try:
                PaddleOcrProvider._engine = PaddleOCR(
                    lang=self.lang,
                    use_doc_orientation_classify=True,
                    use_doc_unwarping=True,
                    use_textline_orientation=True,
                )
            except TypeError:
                # PaddleOCR 2.x keyword set.
                PaddleOcrProvider._engine = PaddleOCR(lang=self.lang, use_angle_cls=True)
        return PaddleOcrProvider._engine

    # -- output normalisation ---------------------------------------------

    @staticmethod
    def _lines_from_boxes(items: list[tuple[list, str, float]]) -> tuple[str, float]:
        """Group recognised boxes into visual lines, top-to-bottom."""
        if not items:
            return "", 0.0

        entries = []
        for poly, text, score in items:
            if not text or not str(text).strip():
                continue
            ys = [p[1] for p in poly]
            xs = [p[0] for p in poly]
            entries.append({
                "text": str(text).strip(),
                "score": float(score) if score is not None else 0.0,
                "cy": sum(ys) / len(ys),
                "x": min(xs),
                "h": max(ys) - min(ys),
            })
        if not entries:
            return "", 0.0

        entries.sort(key=lambda e: e["cy"])
        median_h = sorted(e["h"] for e in entries)[len(entries) // 2] or 10.0
        tolerance = max(6.0, median_h * 0.6)

        lines: list[list[dict]] = [[entries[0]]]
        for e in entries[1:]:
            if abs(e["cy"] - lines[-1][-1]["cy"]) <= tolerance:
                lines[-1].append(e)
            else:
                lines.append([e])

        out = []
        for line in lines:
            line.sort(key=lambda e: e["x"])
            out.append(" ".join(e["text"] for e in line))

        scores = [e["score"] for e in entries if e["score"] > 0]
        return _clean("\n".join(out)), (sum(scores) / len(scores)) if scores else 0.0

    def _run(self, path) -> tuple[str, float]:
        engine = self._get_engine()

        # PaddleOCR 3.x
        if hasattr(engine, "predict"):
            pages = engine.predict(str(path))
            items = []
            for page in pages or []:
                texts = page.get("rec_texts") or []
                scores = page.get("rec_scores") or []
                polys = page.get("rec_polys") or page.get("dt_polys") or []
                for i, text in enumerate(texts):
                    poly = polys[i] if i < len(polys) else [[0, i * 10], [0, i * 10]]
                    poly = [[float(pt[0]), float(pt[1])] for pt in poly]
                    score = scores[i] if i < len(scores) else 0.0
                    items.append((poly, text, score))
            return self._lines_from_boxes(items)

        # PaddleOCR 2.x
        result = engine.ocr(str(path), cls=True)
        items = []
        for page in result or []:
            for entry in page or []:
                poly, (text, score) = entry[0], entry[1]
                items.append(([[float(p[0]), float(p[1])] for p in poly], text, score))
        return self._lines_from_boxes(items)

    def extract(self, path, mime: str) -> OcrResult:
        if not self.available():
            log.warning("paddleocr not installed; falling back to tesseract")
            return TesseractProvider().extract(path, mime)

        mime = (mime or "").lower()
        is_pdf = mime in PDF_MIMES or str(path).lower().endswith(".pdf")

        # A born-digital PDF still beats any OCR — check the text layer first.
        if is_pdf:
            layer = _pdf_text_layer(path)
            good = [p for p in layer if len(p.text) >= settings.text_layer_min_chars]
            if layer and len(good) >= max(1, len(layer) // 2):
                return OcrResult(
                    text=_clean("\n\n".join(p.text for p in layer)),
                    pages=layer,
                    engine="pdf_text_layer",
                    confidence=1.0,
                    page_count=len(layer),
                )

        try:
            if is_pdf:
                import tempfile

                images = _render_pdf_pages(path, settings.ocr_raster_dpi)
                pages: list[OcrPage] = []
                for i, img in enumerate(images, start=1):
                    with tempfile.NamedTemporaryFile(suffix=".png", delete=True) as tmp:
                        img.save(tmp.name, format="PNG")
                        text, conf = self._run(tmp.name)
                    pages.append(OcrPage(page=i, text=text, confidence=conf, source="paddleocr"))
                confs = [p.confidence for p in pages if p.confidence is not None]
                return OcrResult(
                    text=_clean("\n\n".join(p.text for p in pages)),
                    pages=pages,
                    engine="paddleocr",
                    confidence=(sum(confs) / len(confs)) if confs else 0.0,
                    page_count=len(pages),
                )

            text, conf = self._run(path)
            return OcrResult(
                text=text,
                pages=[OcrPage(page=1, text=text, confidence=conf, source="paddleocr")],
                engine="paddleocr",
                confidence=conf,
                page_count=1,
            )
        except Exception as exc:  # noqa: BLE001 - never lose a check to an engine fault
            log.warning("paddleocr failed on %s (%s); falling back to tesseract", path, exc)
            return TesseractProvider().extract(path, mime)


_probe_cache: dict[str, object] | None = None


def probe_provider(name: str | None = None, *, force: bool = False) -> dict:
    """Find out which engine will *actually* be used, by running one.

    Importability is not readiness: PaddleOCR imports fine and then fails at
    first use if its models cannot be fetched, silently falling back to
    Tesseract. Only putting an image through the provider reveals that, so the
    result is probed once and cached for the health endpoint to report.
    """
    global _probe_cache
    if _probe_cache is not None and not force:
        return dict(_probe_cache)

    requested = (name or settings.ocr_provider or "tesseract").lower()
    result = {"requested": requested, "actual": None, "ready": False, "error": None}

    if requested == "claude_vision":
        # Probing this would spend tokens; trust the configuration instead.
        result.update(actual=requested, ready=bool(settings.anthropic_api_key))
        _probe_cache = result
        return dict(result)

    import tempfile

    try:
        from PIL import Image, ImageDraw

        img = Image.new("RGB", (640, 160), (255, 255, 255))
        ImageDraw.Draw(img).text((20, 60), "PASSPORT AB1234567", fill=(0, 0, 0))
        with tempfile.NamedTemporaryFile(suffix=".png", delete=True) as tmp:
            img.save(tmp.name, format="PNG")
            outcome = get_provider(requested).extract(tmp.name, "image/png")
        result["actual"] = outcome.engine
        result["ready"] = outcome.engine == requested or requested == "tesseract"
        if not result["ready"]:
            result["error"] = (
                f"requested '{requested}' but the pipeline fell back to "
                f"'{outcome.engine}'"
            )
    except Exception as exc:  # noqa: BLE001 - a probe must never break startup
        result["error"] = str(exc)[:200]

    _probe_cache = result
    return dict(result)


def get_provider(name: str | None = None):
    choice = (name or settings.ocr_provider or "tesseract").lower()
    if choice == "claude_vision":
        return ClaudeVisionProvider()
    if choice in ("paddleocr", "paddle"):
        return PaddleOcrProvider(lang=settings.paddle_lang)
    return TesseractProvider()
