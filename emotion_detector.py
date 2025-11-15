from typing import Optional, Union, List, Dict

import cv2  # noqa: F401
from deepface import DeepFace


def analyze_frame(frame) -> Optional[str]:
    """
    Analyze a BGR image (numpy ndarray) and return dominant emotion string or None.
    Uses enforce_detection=False for robustness with webcam frames.
    """
    try:
        result: Union[Dict, List[Dict]] = DeepFace.analyze(
            frame,
            actions=["emotion"],
            enforce_detection=False,
        )
        if isinstance(result, list):
            if len(result) == 0:
                return None
            result = result[0]
        dominant = result.get("dominant_emotion")
        return str(dominant) if dominant else None
    except Exception:
        return None
