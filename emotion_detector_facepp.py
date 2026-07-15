"""
Lightweight Face++ (Face Plus Plus) emotion detector adapter.

Usage: set `FACEPP_API_KEY` and `FACEPP_API_SECRET` in env or Streamlit Secrets.

This module sends the uploaded frame to Face++ Detect API and returns a normalized
emotion label compatible with the app.

Works on Streamlit Cloud - only requires requests, not heavy ML libraries.
"""
import os
import io
import requests
from typing import Optional

# Optional imports for local face detection fallback
cv2 = None
np = None
try:
    import cv2 as _cv2
    import numpy as _np
    cv2 = _cv2
    np = _np
except (ImportError, OSError):
    pass

_LAST_ERROR: Optional[str] = None

# Try to read from Streamlit Secrets first, then fall back to environment variables
try:
    import streamlit as st
    FACEPP_API_KEY = st.secrets.get("FACEPP_API_KEY", "") or os.getenv("FACEPP_API_KEY", "")
    FACEPP_API_SECRET = st.secrets.get("FACEPP_API_SECRET", "") or os.getenv("FACEPP_API_SECRET", "")
except:
    FACEPP_API_KEY = os.getenv("FACEPP_API_KEY", "")
    FACEPP_API_SECRET = os.getenv("FACEPP_API_SECRET", "")

FACEPP_ENDPOINT = os.getenv("FACEPP_ENDPOINT", "https://api-us.faceplusplus.com/facepp/v3/detect")

def get_last_detection_error() -> Optional[str]:
    return _LAST_ERROR

def _set_error(msg: str):
    global _LAST_ERROR
    _LAST_ERROR = msg

def _map_facepp_emotion(facepp_emotion: dict) -> str:
    # facepp_emotion keys: anger, disgust, fear, happiness, neutral, sadness, surprise
    # Choose the highest scoring emotion and map to our normalized set
    if not facepp_emotion:
        return "calm"
    best = max(facepp_emotion.items(), key=lambda x: x[1])
    label = best[0]
    mapping = {
        'happiness': 'happy',
        'neutral': 'calm',
        'sadness': 'sad',
        'anger': 'angry',
        'fear': 'fearful',
        'surprise': 'surprised',
        'disgust': 'focused',
    }
    return mapping.get(label, 'calm')

def analyze_frame(frame_bgr) -> Optional[str]:
    """
    Send the frame to Face++ and return a normalized emotion label.
    
    Args:
        frame_bgr: numpy array (BGR) or PIL Image or bytes
        
    Returns:
        Normalized emotion label or None on failure
    """
    global _LAST_ERROR
    _LAST_ERROR = None

    if not FACEPP_API_KEY or not FACEPP_API_SECRET:
        _set_error("Face++ API credentials missing")
        return None

    try:
        def _call_facepp(img_data):
            """Send image to Face++ API."""
            # Handle different input formats
            if isinstance(img_data, bytes):
                image_bytes = img_data
            elif cv2 is not None:
                # numpy array in BGR
                _, buf = cv2.imencode('.jpg', img_data)
                image_bytes = buf.tobytes()
            else:
                # Can't convert without cv2
                raise RuntimeError("cv2 not available and input is not bytes")
            
            files = {'image_file': ('frame.jpg', io.BytesIO(image_bytes), 'image/jpeg')}
            data = {
                'api_key': FACEPP_API_KEY,
                'api_secret': FACEPP_API_SECRET,
                'return_attributes': 'emotion'
            }
            resp = requests.post(FACEPP_ENDPOINT, data=data, files=files, timeout=10)
            if resp.status_code != 200:
                raise RuntimeError(f"Face++ HTTP {resp.status_code}: {resp.text}")
            return resp.json()

        # First attempt: send full image
        j = _call_facepp(frame_bgr)
        faces = j.get('faces', [])

        # If no faces detected and cv2 available, try a local face-crop fallback
        if not faces and cv2 is not None:
            try:
                cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
                gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
                dets = cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
                if len(dets) > 0:
                    # pick largest detected box and crop with padding
                    x, y, w, h = max(dets, key=lambda r: r[2] * r[3])
                    pad = int(0.25 * max(w, h))
                    x0 = max(0, x - pad)
                    y0 = max(0, y - pad)
                    x1 = min(frame_bgr.shape[1], x + w + pad)
                    y1 = min(frame_bgr.shape[0], y + h + pad)
                    cropped = frame_bgr[y0:y1, x0:x1]
                    j = _call_facepp(cropped)
                    faces = j.get('faces', [])
            except Exception as e:
                print(f"[emotion_detector_facepp] Cascade fallback failed: {e}")

        if not faces:
            _set_error('Face++: no face detected')
            return None

        # Use largest face by bounding box area if multiple
        best_face = max(faces, key=lambda f: (f.get('face_rectangle', {}).get('width', 0) * f.get('face_rectangle', {}).get('height', 0)))
        emotions = best_face.get('attributes', {}).get('emotion', {})
        if not emotions:
            _set_error('Face++: no emotion attributes')
            return None
        mapped = _map_facepp_emotion(emotions)
        return mapped

    except Exception as e:
        _set_error(str(e))
        return None


if __name__ == '__main__':
    print('Run inside Streamlit; this module provides `analyze_frame(frame_bgr)`')
