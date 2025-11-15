import sys
from pathlib import Path
from typing import List

from deepface import DeepFace

"""
Usage:
  python test_emotion.py path\to\images

The folder should contain front-facing images like:
  happy.jpg, sad.jpg, angry.jpg, fear.jpg, surprise.jpg, disgust.jpg, neutral.jpg

This prints detected dominant emotions for each file.
"""


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: python test_emotion.py <images_folder>")
        return 1

    images_dir = Path(sys.argv[1])
    if not images_dir.exists() or not images_dir.is_dir():
        print(f"Not a valid folder: {images_dir}")
        return 1

    image_paths: List[Path] = [
        p for p in images_dir.iterdir() if p.suffix.lower() in {".jpg", ".jpeg", ".png"}
    ]
    if not image_paths:
        print("No images found (.jpg/.jpeg/.png)")
        return 1

    print(f"Testing {len(image_paths)} images in: {images_dir}")
    for img_path in sorted(image_paths):
        try:
            result = DeepFace.analyze(img_path=str(img_path), actions=["emotion"], enforce_detection=False)
            if isinstance(result, list):
                result = result[0] if result else {}
            dom = result.get("dominant_emotion")
            print(f"{img_path.name}: {dom}")
        except Exception as e:
            print(f"{img_path.name}: ERROR {e}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
