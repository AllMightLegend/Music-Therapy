import sys
from pathlib import Path
from typing import List, Optional

import cv2

from face_detector import MediaPipeFaceDetector
from va_model import load_va_model, predict_va

"""
Usage:
  python test_emotion.py path\to\images [optional_weights_path]

The folder should contain front-facing images.
This script prints Valence and Arousal estimates per image using:
  MediaPipe Face Detection -> face crop -> EfficientNet-B2 VA ([-1, 1]).

If you provide weights (recommended), place a fine-tuned AffectNet VA model at
  models/efficientnet_b2_va.h5
or pass a path as the second argument.
"""


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python test_emotion.py <images_folder> [weights_path]")
        return 1

    images_dir = Path(sys.argv[1])
    if not images_dir.exists() or not images_dir.is_dir():
        print(f"Not a valid folder: {images_dir}")
        return 1

    weights_path: Optional[str] = None
    if len(sys.argv) >= 3:
        weights_path = sys.argv[2]
    else:
        default_weights = Path("models/efficientnet_b2_va.h5")
        if default_weights.exists():
            weights_path = str(default_weights)

    print(f"Loading VA model (weights={weights_path or 'None'})...")
    model = load_va_model(weights_path=weights_path)
    detector = MediaPipeFaceDetector()

    image_paths: List[Path] = [
        p for p in images_dir.iterdir() if p.suffix.lower() in {".jpg", ".jpeg", ".png"}
    ]
    if not image_paths:
        print("No images found (.jpg/.jpeg/.png)")
        return 1

    print(f"Testing {len(image_paths)} images in: {images_dir}")
    for img_path in sorted(image_paths):
        try:
            bgr = cv2.imread(str(img_path))
            if bgr is None:
                print(f"{img_path.name}: ERROR could not read image")
                continue
            face = detector.detect_and_crop(bgr)
            if face is None:
                print(f"{img_path.name}: NO_FACE")
                continue
            va = predict_va(model, face)
            if va is None:
                print(f"{img_path.name}: PREDICT_FAIL")
                continue
            v, a = va
            print(f"{img_path.name}: V={v:.3f}, A={a:.3f}")
        except Exception as e:
            print(f"{img_path.name}: ERROR {e}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
