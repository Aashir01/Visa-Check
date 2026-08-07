"""Regression tests for OCR line structure and the provider factory.

Why these exist: `_tesseract_image` originally joined every recognised word
with a space, flattening the page to a single line. The MRZ is *defined* as
two fixed-width lines, so the parser could never find it — which silently
disabled check-digit-verified passport extraction for every image upload,
while PDF text layers (which keep their newlines) still worked. The bug was
invisible in tests built on digital PDFs.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from app.pipeline import ocr as ocr_mod
from app.pipeline.extract import extract_document
from app.pipeline.mrz import parse_mrz

pytest.importorskip("PIL")

FIXTURE_DIR = Path(__file__).parent / "_generated"


def _passport_image(level: str, tmp_path: Path) -> Path:
    """Render the passport fixture, then degrade it like a phone photo."""
    from tests.make_fixtures import bundle_clean
    from tests.make_phone_photo import degrade, render_pdf_page

    bundle_dir = tmp_path / "bundle"
    bundle_clean(bundle_dir)
    img = degrade(render_pdf_page(bundle_dir / "passport.pdf"), level=level, seed=7)
    out = tmp_path / f"passport_{level}.jpg"
    img.save(out, quality=85)
    return out


# --------------------------------------------------------------------------
# line structure
# --------------------------------------------------------------------------


def test_tesseract_output_preserves_line_breaks(tmp_path):
    path = _passport_image("light", tmp_path)
    result = ocr_mod.TesseractProvider().extract(path, "image/jpeg")
    assert result.text.count("\n") >= 5, (
        "OCR output collapsed to too few lines; the MRZ cannot be located "
        "without line structure"
    )


def test_mrz_recovered_from_a_photographed_passport(tmp_path):
    """The end-to-end guarantee: a photo of a passport yields verified fields."""
    path = _passport_image("light", tmp_path)
    text = ocr_mod.TesseractProvider().extract(path, "image/jpeg").text

    mrz = parse_mrz(text)
    assert mrz.document_number == "AB1234567"
    assert mrz.date_of_birth == "1990-04-12"
    assert mrz.valid is True, f"check digits failed: {mrz.checks}"


def test_extraction_populates_passport_fields_from_a_photo(tmp_path):
    path = _passport_image("light", tmp_path)
    text = ocr_mod.TesseractProvider().extract(path, "image/jpeg").text

    fields = extract_document("passport", text).fields
    assert fields.get("passport_number") == "AB1234567"
    assert fields.get("date_of_birth") == "1990-04-12"
    assert fields.get("mrz_valid") is True


def test_expiry_survives_the_photo_path(tmp_path):
    path = _passport_image("light", tmp_path)
    text = ocr_mod.TesseractProvider().extract(path, "image/jpeg").text
    expiry = extract_document("passport", text).fields.get("expiry_date")
    assert expiry is not None
    assert date.fromisoformat(expiry).year == 2030


# --------------------------------------------------------------------------
# provider factory
# --------------------------------------------------------------------------


def test_factory_returns_the_requested_engine():
    assert type(ocr_mod.get_provider("tesseract")).__name__ == "TesseractProvider"
    assert type(ocr_mod.get_provider("paddleocr")).__name__ == "PaddleOcrProvider"
    assert type(ocr_mod.get_provider("paddle")).__name__ == "PaddleOcrProvider"
    assert type(ocr_mod.get_provider("claude_vision")).__name__ == "ClaudeVisionProvider"


def test_unknown_engine_falls_back_to_tesseract():
    assert type(ocr_mod.get_provider("nonsense")).__name__ == "TesseractProvider"


def test_paddle_groups_boxes_into_lines():
    """Two MRZ rows must come back as two lines, not one run-on string."""
    def box(x0, y0, x1, y1):
        return [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]

    items = [
        (box(10, 100, 300, 120), "P<PAKKHAN<<AHMED<RAZA<<<<", 0.95),
        (box(10, 130, 300, 150), "AB12345671PAK9004126M30", 0.93),
        (box(10, 10, 200, 30), "PASSPORT", 0.99),
    ]
    text, confidence = ocr_mod.PaddleOcrProvider._lines_from_boxes(items)
    lines = text.splitlines()

    assert lines[0] == "PASSPORT", "boxes must be ordered top-to-bottom"
    assert len(lines) == 3
    assert lines[1].startswith("P<PAK")
    assert lines[2].startswith("AB123")
    assert 0.9 < confidence < 1.0


def test_paddle_merges_boxes_on_the_same_line():
    def box(x0, y0, x1, y1):
        return [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]

    items = [
        (box(200, 100, 300, 120), "AB1234567", 0.9),
        (box(10, 102, 180, 120), "Passport No:", 0.9),
    ]
    text, _ = ocr_mod.PaddleOcrProvider._lines_from_boxes(items)
    assert text == "Passport No: AB1234567", "same-line boxes must join left-to-right"


def test_paddle_handles_empty_output():
    assert ocr_mod.PaddleOcrProvider._lines_from_boxes([]) == ("", 0.0)
