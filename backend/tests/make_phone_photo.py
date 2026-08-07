#!/usr/bin/env python3
"""Degrade a clean document into something like a phone photo of it.

Applicants do not upload clean PDFs. They photograph a document lying on a
table: slightly rotated, in perspective, unevenly lit, then compressed by
WhatsApp. This script reproduces that so OCR engines can be compared on the
input they will actually receive rather than on synthetic clean text.

    python tests/make_phone_photo.py --pdf passport.pdf --out photo.jpg --level medium
"""

from __future__ import annotations

import argparse
import io
import math
from pathlib import Path

import numpy as np
from PIL import Image, ImageEnhance, ImageFilter

LEVELS = {
    # rotation°, perspective, blur, shadow, jpeg quality, downscale, noise
    "light":  dict(rotate=1.5, warp=0.010, blur=0.5, shadow=0.15, jpeg=80, scale=0.85, noise=3),
    "medium": dict(rotate=4.0, warp=0.030, blur=1.1, shadow=0.35, jpeg=55, scale=0.60, noise=7),
    "harsh":  dict(rotate=8.0, warp=0.055, blur=1.9, shadow=0.55, jpeg=35, scale=0.45, noise=12),
}


def _perspective_coeffs(src, dst):
    matrix = []
    for s, d in zip(src, dst):
        matrix.append([d[0], d[1], 1, 0, 0, 0, -s[0] * d[0], -s[0] * d[1]])
        matrix.append([0, 0, 0, d[0], d[1], 1, -s[1] * d[0], -s[1] * d[1]])
    A = np.array(matrix, dtype=float)
    B = np.array(src, dtype=float).reshape(8)
    return np.linalg.solve(A, B).reshape(8)


def _warp(img: Image.Image, amount: float) -> Image.Image:
    w, h = img.size
    dx, dy = w * amount, h * amount
    src = [(0, 0), (w, 0), (w, h), (0, h)]
    dst = [(dx, dy * 0.6), (w - dx * 0.4, 0), (w - dx * 0.2, h - dy), (dx * 0.7, h - dy * 0.3)]
    return img.transform(
        (w, h), Image.PERSPECTIVE, _perspective_coeffs(src, dst),
        resample=Image.BICUBIC, fillcolor=(235, 233, 228),
    )


def _shadow(img: Image.Image, strength: float) -> Image.Image:
    """A soft diagonal gradient, like a hand or window casting across the page."""
    w, h = img.size
    yy, xx = np.mgrid[0:h, 0:w]
    grad = (xx / w) * 0.6 + (yy / h) * 0.4
    mask = 1.0 - strength * np.clip((grad - 0.25) / 0.75, 0, 1) ** 1.3
    arr = np.array(img).astype(np.float32)
    arr *= mask[:, :, None]
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))


def degrade(img: Image.Image, level: str = "medium", seed: int = 7) -> Image.Image:
    rng = np.random.default_rng(seed)
    cfg = LEVELS[level]

    img = img.convert("RGB")
    # Paper is never pure white under room light.
    arr = np.array(img).astype(np.float32)
    arr = arr * 0.94 + np.array([12, 10, 6], dtype=np.float32)
    img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))

    img = _warp(img, cfg["warp"])
    img = img.rotate(
        rng.uniform(-cfg["rotate"], cfg["rotate"]),
        resample=Image.BICUBIC, expand=True, fillcolor=(232, 230, 225),
    )
    img = _shadow(img, cfg["shadow"])

    w, h = img.size
    img = img.resize((int(w * cfg["scale"]), int(h * cfg["scale"])), Image.LANCZOS)
    img = img.filter(ImageFilter.GaussianBlur(cfg["blur"]))
    img = ImageEnhance.Contrast(img).enhance(0.88)

    arr = np.array(img).astype(np.float32)
    arr += rng.normal(0, cfg["noise"], arr.shape)
    img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))

    # Round-trip through JPEG, the way a messaging app would.
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=cfg["jpeg"])
    buf.seek(0)
    return Image.open(buf).convert("RGB")


def render_pdf_page(pdf: Path, page: int = 0, dpi: int = 200) -> Image.Image:
    import pypdfium2 as pdfium

    doc = pdfium.PdfDocument(str(pdf))
    try:
        return doc[page].render(scale=dpi / 72).to_pil()
    finally:
        doc.close()


def main() -> None:
    ap = argparse.ArgumentParser(description="Simulate a phone photo of a document.")
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--level", default="medium", choices=sorted(LEVELS))
    ap.add_argument("--page", type=int, default=0)
    ap.add_argument("--seed", type=int, default=7)
    args = ap.parse_args()

    img = degrade(render_pdf_page(Path(args.pdf), args.page), args.level, args.seed)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    img.save(args.out, quality=LEVELS[args.level]["jpeg"])
    print(f"{args.out}  {img.size[0]}x{img.size[1]}  level={args.level}")


if __name__ == "__main__":
    main()
