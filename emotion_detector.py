import os
from typing import Optional, Union, List, Dict

# Disable OpenGL for headless environments (Streamlit Cloud)
os.environ["OPENCV_IO_ENABLE_OPENEXR"] = "0"
# Prevent OpenCV from trying to load GUI libraries
os.environ["QT_QPA_PLATFORM"] = "offscreen"

try:
    import cv2  # noqa: F401
    CV2_AVAILABLE = True
except (ImportError, OSError):
    # OSError catches missing system libraries like libGL.so.1
    CV2_AVAILABLE = False

try:
    from deepface import DeepFace
    DEEPFACE_AVAILABLE = True
except (ImportError, OSError, Exception):
    # OSError catches missing system libraries that DeepFace depends on
    # Exception catches any other initialization errors
    DEEPFACE_AVAILABLE = False


def analyze_frame(frame) -> Optional[str]:
    """
    Analyze a BGR image (numpy ndarray) and return dominant emotion string or None.
    Uses enforce_detection=False for robustness with webcam frames.
    """
    if not DEEPFACE_AVAILABLE:
        return None
    
    try:
        # Ensure frame is a numpy array
        import numpy as np
        if not isinstance(frame, np.ndarray):
            return None
        
        # Ensure frame has 3 dimensions (height, width, channels)
        if len(frame.shape) != 3 or frame.shape[2] != 3:
            return None
        
        # DeepFace expects RGB format, but we're passing BGR from OpenCV
        # Convert BGR to RGB for DeepFace
        frame_rgb = frame[:, :, ::-1]  # BGR to RGB
        
        result: Union[Dict, List[Dict]] = DeepFace.analyze(
            frame_rgb,
            actions=["emotion"],
            enforce_detection=False,
            silent=True,  # Suppress verbose output
            detector_backend="opencv",  # Use OpenCV backend for better compatibility
        )
        if isinstance(result, list):
            if len(result) == 0:
                return None
            result = result[0]
        dominant = result.get("dominant_emotion")
        return str(dominant) if dominant else None
    except (OSError, RuntimeError, Exception) as e:
        # OSError: Missing system libraries (libGL.so.1, etc.)
        # RuntimeError: DeepFace model loading failures
        # Exception: Any other errors during analysis
        # Suppress errors in production to avoid cluttering logs
        return None
