"""Face detection, used to tell a portrait from a landscape and to pick a shot size.

Entirely optional: with no OpenCV and no model on disk the rest of the pipeline
runs unchanged, it simply stops scoring faces. Two backends are supported, best
first:

  YuNet  - a small ONNX detector (232 KB) fetched once by ``stillharvest setup``.
           Handles profiles and small faces far better than a cascade.
  Haar   - the classic frontal cascade, used when OpenCV still ships the XML
           (OpenCV <= 4.x) or when one is dropped into the model cache.
"""

from __future__ import annotations

import functools
import hashlib
import os
import urllib.request
from pathlib import Path

import numpy as np

# Quiet OpenCV's backend chatter before it loads; it prints to stderr otherwise.
os.environ.setdefault("OPENCV_LOG_LEVEL", "ERROR")

try:  # pragma: no cover - environment dependent
    import cv2  # type: ignore
except Exception:  # pragma: no cover
    cv2 = None  # type: ignore

YUNET_FILENAME = "face_detection_yunet_2023mar.onnx"
YUNET_SHA256 = "8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4"
YUNET_URLS = (
    "https://media.githubusercontent.com/media/opencv/opencv_zoo/main/"
    "models/face_detection_yunet/" + YUNET_FILENAME,
    "https://raw.githubusercontent.com/opencv/opencv_zoo/main/"
    "models/face_detection_yunet/" + YUNET_FILENAME,
)
HAAR_FILENAME = "haarcascade_frontalface_default.xml"

Box = tuple[int, int, int, int]


def cache_dir() -> Path:
    root = os.environ.get("STILLHARVEST_CACHE")
    base = Path(root) if root else Path.home() / ".cache" / "stillharvest"
    return base / "models"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def model_path() -> Path:
    return cache_dir() / YUNET_FILENAME


def model_ready() -> bool:
    path = model_path()
    return path.is_file() and path.stat().st_size > 100_000


def download_model(*, force: bool = False) -> Path:
    """Fetch the YuNet model into the cache. Returns its path."""
    target = model_path()
    if target.is_file() and not force and _sha256(target) == YUNET_SHA256:
        return target
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_suffix(".part")
    last_error: Exception | None = None
    for url in YUNET_URLS:
        try:
            with urllib.request.urlopen(url, timeout=120) as response:
                data = response.read()
            if len(data) < 100_000:       # an LFS pointer, not the weights
                raise ValueError(f"{url} returned {len(data)} bytes, not a model")
            tmp.write_bytes(data)
            digest = _sha256(tmp)
            if digest != YUNET_SHA256:
                raise ValueError(f"checksum mismatch for {url}: {digest}")
            tmp.replace(target)
            return target
        except Exception as exc:  # try the next mirror
            last_error = exc
            tmp.unlink(missing_ok=True)
    raise RuntimeError(f"Could not download the face model: {last_error}")


def _haar_candidates() -> list[Path]:
    paths = [cache_dir() / HAAR_FILENAME]
    if cv2 is not None:
        try:
            paths.append(Path(cv2.data.haarcascades) / HAAR_FILENAME)  # type: ignore[attr-defined]
        except Exception:
            pass
    return paths


@functools.lru_cache(maxsize=1)
def _backend():
    """(name, detector) for the best available backend, or ('none', None)."""
    if cv2 is None:
        return "none", None
    if model_ready() and hasattr(cv2, "FaceDetectorYN"):
        try:
            detector = cv2.FaceDetectorYN.create(
                str(model_path()), "", (320, 320),
                0.6,    # score threshold
                0.3,    # NMS threshold
                5000,   # top-k
            )
            return "yunet", detector
        except Exception:
            pass
    if hasattr(cv2, "CascadeClassifier"):
        for path in _haar_candidates():
            if path.is_file():
                try:
                    cascade = cv2.CascadeClassifier(str(path))
                    if not cascade.empty():
                        return "haar", cascade
                except Exception:
                    continue
    return "none", None


def backend_name() -> str:
    return _backend()[0]


def available() -> bool:
    return _backend()[1] is not None


def status() -> str:
    """One line explaining what face detection will and will not do."""
    name = backend_name()
    if name == "yunet":
        return "faces: YuNet (ONNX) - full accuracy"
    if name == "haar":
        return "faces: Haar cascade - frontal faces only"
    if cv2 is None:
        return "faces: OFF (no OpenCV; `pip install opencv-python-headless`)"
    return "faces: OFF (no model; run `stillharvest setup` to fetch it)"


def detect(rgb: np.ndarray) -> list[Box]:
    """Face boxes (x, y, w, h) in pixels. Empty when detection is unavailable."""
    name, detector = _backend()
    if detector is None:
        return []
    height, width = rgb.shape[:2]
    if height < 32 or width < 32:
        return []
    try:
        if name == "yunet":
            bgr = np.ascontiguousarray(rgb[:, :, ::-1])
            detector.setInputSize((width, height))
            _, found = detector.detect(bgr)
            if found is None:
                return []
            return [
                (int(row[0]), int(row[1]), int(row[2]), int(row[3]))
                for row in found
                if row[2] > 0 and row[3] > 0
            ]
        gray = np.ascontiguousarray(
            (0.299 * rgb[:, :, 0] + 0.587 * rgb[:, :, 1] + 0.114 * rgb[:, :, 2]).astype(np.uint8)
        )
        minimum = max(16, height // 24)
        found = detector.detectMultiScale(
            gray, scaleFactor=1.15, minNeighbors=5, minSize=(minimum, minimum)
        )
        return [(int(x), int(y), int(w), int(h)) for x, y, w, h in found]
    except Exception:
        return []
