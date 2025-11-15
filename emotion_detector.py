import os
from typing import Optional, Union, List, Dict

# Disable OpenGL for headless environments (Streamlit Cloud)
os.environ["OPENCV_IO_ENABLE_OPENEXR"] = "0"
# Prevent OpenCV from trying to load GUI libraries
os.environ["QT_QPA_PLATFORM"] = "offscreen"

try:
    import cv2  # noqa: F401
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False

try:
    from deepface import DeepFace
    DEEPFACE_AVAILABLE = True
except ImportError:
    DEEPFACE_AVAILABLE = False


def analyze_frame(frame) -> Optional[str]:
    """
    Analyze a BGR image (numpy ndarray) and return dominant emotion string or None.
    Uses enforce_detection=False for robustness with webcam frames.
    """
    if not DEEPFACE_AVAILABLE:
        return None
    
    try:
        result: Union[Dict, List[Dict]] = DeepFace.analyze(
            frame,
            actions=["emotion"],
            enforce_detection=False,
            silent=True,  # Suppress verbose output
        )
        if isinstance(result, list):
            if len(result) == 0:
                return None
            result = result[0]
        dominant = result.get("dominant_emotion")
        return str(dominant) if dominant else None
    except Exception:
        return None
