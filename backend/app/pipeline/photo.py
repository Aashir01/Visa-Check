"""Photograph compliance metrics (blueprint §3.7).

Everything here is deterministic OpenCV/Pillow work — no tokens spent. The
rule pack supplies the thresholds; this module only measures.

Measured: pixel size, DPI, aspect ratio, face count, face height as a fraction
of image height, head-centre offset, background uniformity and lightness,
sharpness, and whether the image is effectively greyscale.
"""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass

log = logging.getLogger(__name__)

_MM_PER_INCH = 25.4


@dataclass
class PhotoMetrics:
    width_px: int = 0
    height_px: int = 0
    dpi: int | None = None
    width_mm: float | None = None
    height_mm: float | None = None
    aspect_ratio: float | None = None          # width / height
    faces: int = 0
    face_height_ratio: float | None = None     # face box height / image height
    face_area_pct: float | None = None
    face_centre_offset: float | None = None    # 0 = centred, 1 = at the edge
    background_uniformity: float | None = None  # 1 = perfectly plain
    background_lightness: float | None = None  # 0 dark .. 1 white
    sharpness: float | None = None             # Laplacian variance
    is_greyscale: bool | None = None
    error: str | None = None

    def as_dict(self) -> dict:
        return {k: v for k, v in asdict(self).items() if v is not None}


def _face_cascade():
    import cv2

    path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    cascade = cv2.CascadeClassifier(path)
    return None if cascade.empty() else cascade


def analyse(path) -> PhotoMetrics:
    import cv2
    import numpy as np
    from PIL import Image

    m = PhotoMetrics()
    try:
        with Image.open(path) as pil:
            pil.load()
            m.width_px, m.height_px = pil.size
            dpi = pil.info.get("dpi")
            if dpi and isinstance(dpi, (tuple, list)) and dpi[0]:
                try:
                    m.dpi = int(round(float(dpi[0])))
                except (TypeError, ValueError):
                    m.dpi = None
            rgb = pil.convert("RGB")
            arr = np.array(rgb)
    except Exception as exc:  # noqa: BLE001
        return PhotoMetrics(error=f"unreadable image: {exc}")

    if m.height_px:
        m.aspect_ratio = round(m.width_px / m.height_px, 4)
    if m.dpi:
        m.width_mm = round(m.width_px / m.dpi * _MM_PER_INCH, 1)
        m.height_mm = round(m.height_px / m.dpi * _MM_PER_INCH, 1)

    bgr = cv2.cvtColor(arr, cv2.COLOR_RGB2BGR)
    grey = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)

    m.sharpness = round(float(cv2.Laplacian(grey, cv2.CV_64F).var()), 2)

    # "Greyscale" here means the colour channels barely differ — a scanned
    # black-and-white photo, which most embassies reject.
    chan_spread = float(np.mean(np.max(arr, axis=2).astype(np.int16)
                                - np.min(arr, axis=2).astype(np.int16)))
    m.is_greyscale = chan_spread < 8.0

    cascade = _face_cascade()
    if cascade is not None:
        equalised = cv2.equalizeHist(grey)
        faces = cascade.detectMultiScale(
            equalised, scaleFactor=1.1, minNeighbors=5,
            minSize=(max(30, m.width_px // 12), max(30, m.height_px // 12)),
        )
        m.faces = int(len(faces))
        if m.faces:
            # Largest detection is the subject; extras are background people.
            fx, fy, fw, fh = max(faces, key=lambda f: f[2] * f[3])
            m.face_height_ratio = round(float(fh) / m.height_px, 4)
            m.face_area_pct = round(100.0 * (fw * fh) / (m.width_px * m.height_px), 2)
            face_cx = (fx + fw / 2) / m.width_px
            m.face_centre_offset = round(abs(face_cx - 0.5) * 2, 4)

    m.background_uniformity, m.background_lightness = _background(arr)
    return m


def _background(arr) -> tuple[float, float]:
    """Sample the border ring, which for a portrait is nearly all background."""
    import numpy as np

    h, w = arr.shape[:2]
    bw = max(1, int(min(h, w) * 0.08))
    strips = [
        arr[0:bw, :, :].reshape(-1, 3),
        arr[h - bw : h, :, :].reshape(-1, 3),
        arr[:, 0:bw, :].reshape(-1, 3),
        arr[:, w - bw : w, :].reshape(-1, 3),
    ]
    border = np.concatenate(strips, axis=0).astype(np.float32)
    if border.size == 0:
        return 0.0, 0.0

    lightness = float(border.mean()) / 255.0
    # Standard deviation across the ring: a plain wall is near-constant, a
    # patterned curtain or an outdoor shot is not.
    spread = float(border.std(axis=0).mean())
    uniformity = max(0.0, min(1.0, 1.0 - spread / 40.0))
    return round(uniformity, 3), round(lightness, 3)
