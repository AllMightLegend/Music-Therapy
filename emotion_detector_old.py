"""
Emotion detection module using Hume AI Streaming API.

This module provides a simple interface to detect emotions from image frames
using Hume's WebSocket streaming API for real-time detection.
"""

import os
import time
import base64
from typing import Optional

# Disable OpenGL for headless environments
os.environ["OPENCV_IO_ENABLE_OPENEXR"] = "0"
os.environ["QT_QPA_PLATFORM"] = "offscreen"

# Load API key from environment
HUME_API_KEY = os.getenv("HUME_API_KEY")
if not HUME_API_KEY:
    import warnings
    warnings.warn(
        "HUME_API_KEY not found in environment variables. "
        "Please set HUME_API_KEY to use emotion detection. "
        "You can do this by creating a .env file with: HUME_API_KEY=your_api_key_here"
    )

# Flag to indicate if emotion detection is available (always True now with local fallback)
EMOTION_DETECTION_AVAILABLE = True

# Hume Streaming WebSocket endpoint (optional enhancement)
HUME_STREAMING_URL = "wss://api.hume.ai/v0/stream/models"
HUME_PROB_THRESHOLD = float(os.getenv("HUME_PROB_THRESHOLD", "0.7"))
# Enable debug mode to save predictions JSON to disk for inspection
HUME_DEBUG = os.getenv("HUME_DEBUG", "0").lower() in ("1", "true", "yes")
# Use Hume API (can disable if having issues)
USE_HUME = os.getenv("USE_HUME", "0").lower() in ("1", "true", "yes") and bool(HUME_API_KEY)



def analyze_frame(frame_data) -> Optional[str]:
    """
    Analyze an image frame and return the detected emotion.
    
    Detection priority:
    1. Hume API (if USE_HUME=1) - Most accurate, cloud-based
    2. DeepFace (default) - 7 emotions, ML-based, robust
    3. OpenCV fallback - Basic smile detection
    
    Args:
        frame_data: Either a numpy array in BGR format or raw bytes
        
    Returns:
        The dominant emotion mapped to app mood category (happy, sad, angry, etc.)
        or None if emotion detection fails
    """
    # Priority 1: Try Hume API first if enabled
    if USE_HUME:
        try:
            frame_bytes = _convert_to_jpeg_bytes(frame_data)
            if frame_bytes:
                emotion = _analyze_via_streaming(frame_bytes)
                if emotion:
                    print(f"[emotion_detector] ✓ Hume result: {emotion}")
                    return emotion
        except Exception as e:
            print(f"[emotion_detector] Hume API error: {e}")
    
    # Priority 2: Use DeepFace for robust detection
    deepface_emotion = _deepface_detector(frame_data)
    if deepface_emotion:
        print(f"[emotion_detector] ✓ DeepFace result: {deepface_emotion}")
        return deepface_emotion
    
    # Priority 3: Fallback to simple OpenCV
    opencv_emotion = _opencv_simple_detector(frame_data)
    if opencv_emotion:
        print(f"[emotion_detector] ✓ OpenCV fallback: {opencv_emotion}")
        return opencv_emotion
    
    print("[emotion_detector] ✗ No emotion detected by any method")
    return None


def _analyze_via_streaming(frame_bytes: bytes) -> Optional[str]:
    """
    Analyze frame using Hume's WebSocket streaming API for real-time emotion detection.
    
    Args:
        frame_bytes: JPEG image bytes
        
    Returns:
        Detected emotion string or None
    """
    try:
        import websocket
        import json
        
        # Encode image as base64
        frame_b64 = base64.b64encode(frame_bytes).decode('utf-8')
        
        # Build WebSocket URL with API key
        ws_url = f"{HUME_STREAMING_URL}?apikey={HUME_API_KEY}"
        
        print("[emotion_detector] Connecting to Hume streaming API...")
        ws = websocket.create_connection(ws_url, timeout=10)
        
        try:
            # Send configuration message
            config_msg = {
                "models": {
                    "face": {
                        "fps_pred": 3,
                        "prob_threshold": HUME_PROB_THRESHOLD,
                        "identify_faces": False
                    }
                }
            }
            ws.send(json.dumps(config_msg))
            
            # Send image data
            data_msg = {
                "data": frame_b64,
                "models": {
                    "face": {}
                }
            }
            ws.send(json.dumps(data_msg))
            print("[emotion_detector] Sent frame to Hume, waiting for response...")
            
            # Receive response (with timeout)
            response_text = ws.recv()
            result = json.loads(response_text) if isinstance(response_text, str) else response_text
            
            # Save debug copy if enabled
            if HUME_DEBUG:
                try:
                    _save_debug_predictions("streaming", result)
                except Exception:
                    pass
            
            # Extract emotion from streaming response
            emotion = _extract_emotion_from_streaming(result)
            ws.close()
            
            return emotion
            
        except Exception as e:
            print(f"[emotion_detector] Error during streaming: {e}")
            ws.close()
            return None
            
    except Exception as e:
        print(f"[emotion_detector] Failed to connect to Hume streaming API: {e}")
        return None


def _extract_emotion_from_streaming(result: dict) -> Optional[str]:
    """
    Extract emotion from Hume streaming API response.
    
    Args:
        result: JSON response from streaming API
        
    Returns:
        Emotion string or None
    """
    try:
        if not result or not isinstance(result, dict):
            if HUME_DEBUG:
                print(f"[emotion_detector] Invalid result type: {type(result)}")
            return None
        
        if HUME_DEBUG:
            print(f"[emotion_detector] Response keys: {list(result.keys())}")
        
        # Try multiple response structures (Hume API variations)
        # Structure 1: {"face": {"predictions": [...]}}
        # Structure 2: {"predictions": [{"models": {"face": {...}}}]}
        
        emotions = None
        
        # Try structure 1: direct face key
        if "face" in result:
            face_data = result["face"]
            if "predictions" in face_data and face_data["predictions"]:
                predictions = face_data["predictions"]
                if isinstance(predictions, list) and len(predictions) > 0:
                    first_pred = predictions[0]
                    if "emotions" in first_pred:
                        emotions = first_pred["emotions"]
        
        # Try structure 2: predictions array with models
        if not emotions and "predictions" in result:
            preds = result["predictions"]
            if isinstance(preds, list) and len(preds) > 0:
                for pred in preds:
                    if "models" in pred and "face" in pred["models"]:
                        face_model = pred["models"]["face"]
                        if "grouped_predictions" in face_model:
                            grouped = face_model["grouped_predictions"]
                            if isinstance(grouped, list) and len(grouped) > 0:
                                face_pred = grouped[0].get("predictions", [])
                                if isinstance(face_pred, list) and len(face_pred) > 0:
                                    if "emotions" in face_pred[0]:
                                        emotions = face_pred[0]["emotions"]
                                        break
        
        if not emotions:
            if HUME_DEBUG:
                print(f"[emotion_detector] No emotions found in response structure")
            return None
        
        if not isinstance(emotions, list) or len(emotions) == 0:
            print("[emotion_detector] Empty or invalid emotions list")
            return None
        
        # Find highest scoring emotion
        max_emotion = None
        max_score = -1
        
        for emotion_obj in emotions:
            score = emotion_obj.get("score", -1)
            name = emotion_obj.get("name", "unknown")
            if score > max_score:
                max_score = score
                max_emotion = name
        
        if max_emotion and max_score > 0:
            mapped = _map_hume_emotion_to_mood(max_emotion)
            print(f"[emotion_detector] Hume detected: {max_emotion} ({max_score:.3f}) -> {mapped}")
            return mapped
        
        return None
        
    except Exception as e:
        print(f"[emotion_detector] Error extracting emotion from streaming: {e}")
        import traceback
        traceback.print_exc()
        return None


def _deepface_detector(frame_data) -> Optional[str]:
    """
    DeepFace-based emotion detection using deep learning models.
    
    Detects 7 emotions: angry, disgust, fear, happy, sad, surprise, neutral
    
    Args:
        frame_data: numpy array (BGR) or bytes
        
    Returns:
        Detected emotion or None
    """
    try:
        from deepface import DeepFace
        import numpy as np
        import cv2
        
        # Convert to numpy array if needed
        if isinstance(frame_data, bytes):
            nparr = np.frombuffer(frame_data, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        elif isinstance(frame_data, np.ndarray):
            frame = frame_data
        else:
            return None
        
        if frame is None or frame.size == 0:
            return None
        
        # Convert BGR to RGB for DeepFace
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Run DeepFace emotion analysis
        # Using enforce_detection=False to handle various lighting/angles
        result = DeepFace.analyze(
            frame_rgb,
            actions=['emotion'],
            enforce_detection=False,
            detector_backend='opencv',
            silent=True
        )
        
        # Extract dominant emotion
        if isinstance(result, list):
            result = result[0]
        
        if 'dominant_emotion' in result:
            deepface_emotion = result['dominant_emotion'].lower()
            emotion_scores = result.get('emotion', {})
            
            # Map DeepFace emotions to app moods
            emotion_map = {
                'happy': 'happy',
                'sad': 'sad',
                'angry': 'angry',
                'fear': 'fearful',
                'surprise': 'surprised',
                'disgust': 'angry',  # Map disgust to angry
                'neutral': 'calm'
            }
            
            mapped = emotion_map.get(deepface_emotion, 'calm')
            confidence = emotion_scores.get(deepface_emotion, 0)
            
            print(f"[emotion_detector] DeepFace: {deepface_emotion} ({confidence:.1f}%) -> {mapped}")
            return mapped
        
        return None
        
    except Exception as e:
        # DeepFace might fail on first run (model download) or poor images
        if "No face" not in str(e):
            print(f"[emotion_detector] DeepFace error: {e}")
        return None


def _opencv_simple_detector(frame_data) -> Optional[str]:
    """
    Simple OpenCV-based emotion detection as last resort fallback.
    Only detects happy (smile) vs calm (neutral).
    
    Args:
        frame_data: numpy array (BGR) or bytes
        
    Returns:
        'happy' or 'calm', or None if no face detected
    """
    try:
        import cv2
        import numpy as np
        
        # Convert to numpy array if needed
        if isinstance(frame_data, bytes):
            nparr = np.frombuffer(frame_data, np.uint8)
            frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        elif isinstance(frame_data, np.ndarray):
            frame = frame_data
        else:
            return None
        
        if frame is None or frame.size == 0:
            return None
        
        # Convert to grayscale
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Load cascades
        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        smile_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_smile.xml')
        
        # Detect faces
        faces = face_cascade.detectMultiScale(gray, 1.1, 4, minSize=(50, 50))
        
        if len(faces) == 0:
            return None
        
        # Check for smile in largest face
        largest_face = max(faces, key=lambda f: f[2] * f[3])
        (x, y, w, h) = largest_face
        roi_gray = gray[y:y+h, x:x+w]
        
        smiles = smile_cascade.detectMultiScale(roi_gray, 1.4, 15, minSize=(25, 25))
        
        if len(smiles) > 0:
            print(f"[emotion_detector] OpenCV: Smile detected -> happy")
            return "happy"
        else:
            print(f"[emotion_detector] OpenCV: No smile -> calm")
            return "calm"
        
    except Exception as e:
        print(f"[emotion_detector] OpenCV error: {e}")
        return None


def _save_debug_predictions(job_id: str, preds: object) -> None:
    """
    Save a debug copy of predictions JSON to disk when `HUME_DEBUG` is enabled.
    """
    try:
        import json
        base = os.path.join(os.getcwd(), "hume_debug")
        os.makedirs(base, exist_ok=True)
        path = os.path.join(base, f"predictions_{job_id}.json")
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(preds, fh, indent=2)
        print(f"[emotion_detector] Saved debug predictions to: {path}")
    except Exception as e:
        print(f"[emotion_detector] Failed saving debug predictions: {e}")




def _convert_to_jpeg_bytes(frame_data) -> Optional[bytes]:
    """
    Convert input frame (numpy array or bytes) to JPEG bytes.
    
    Args:
        frame_data: numpy array (BGR) or bytes
        
    Returns:
        JPEG bytes or None if conversion fails
    """
    try:
        import numpy as np
        from PIL import Image
        from io import BytesIO
        
        if isinstance(frame_data, np.ndarray):
            # Validate shape (must be 3D with 3 channels)
            if len(frame_data.shape) != 3 or frame_data.shape[2] != 3:
                return None
            
            # Convert BGR to RGB
            frame_rgb = frame_data[:, :, ::-1]
            image = Image.fromarray(frame_rgb)
            
            # Save to JPEG bytes
            buffer = BytesIO()
            image.save(buffer, format='JPEG', quality=85)
            return buffer.getvalue()
            
        elif isinstance(frame_data, bytes):
            return frame_data
        else:
            return None
            
    except Exception as e:
        print(f"Error converting frame to JPEG: {e}")
        return None


def _extract_emotion_from_predictions(predictions: list) -> Optional[str]:
    """
    Extract dominant emotion from Hume batch predictions response.
    
    Predictions structure:
    [
      {
        "source": {...},
        "results": {
          "predictions": [
            {
              "models": {
                "face": {
                  "grouped_predictions": [
                    {
                      "predictions": [
                        {
                          "emotions": [
                            {"name": "joy", "score": 0.95},
                            ...
                          ]
                        }
                      ]
                    }
                  ]
                }
              }
            }
          ]
        }
      }
    ]
    
    Args:
        predictions: JSON response from /batch/jobs/{job_id}/predictions
        
    Returns:
        Emotion string mapped to app mood category, or None
    """
    try:
        if not predictions or not isinstance(predictions, list):
            print("[emotion_detector] No predictions")
            return None
        
        # Get first prediction source
        first = predictions[0]
        if "results" not in first or "predictions" not in first["results"]:
            print("[emotion_detector] No results in first prediction")
            return None
        
        pred_list = first["results"]["predictions"]
        if not pred_list:
            print("[emotion_detector] Empty predictions list")
            return None
        
        prediction = pred_list[0]
        if "models" not in prediction or "face" not in prediction["models"]:
            print("[emotion_detector] No face model in prediction")
            return None
        
        face_model = prediction["models"]["face"]
        if "grouped_predictions" not in face_model or not face_model["grouped_predictions"]:
            print("[emotion_detector] No faces detected (empty grouped_predictions)")
            return None
        
        # Get first grouped prediction (first detected face)
        grouped = face_model["grouped_predictions"][0]
        if "predictions" not in grouped or not grouped["predictions"]:
            print("[emotion_detector] No predictions in grouped face")
            return None
        
        face_pred = grouped["predictions"][0]
        if "emotions" not in face_pred or not face_pred["emotions"]:
            print("[emotion_detector] No emotions in face prediction")
            return None
        
        # Find emotion with highest score
        emotions = face_pred["emotions"]
        max_emotion = None
        max_score = -1
        
        print(f"[emotion_detector] Found {len(emotions)} emotions")
        for emotion_obj in emotions:
            score = emotion_obj.get("score", -1)
            name = emotion_obj.get("name", "unknown")
            print(f"  - {name}: {score:.4f}")
            if score > max_score:
                max_score = score
                max_emotion = name
        
        if max_emotion:
            mapped = _map_hume_emotion_to_mood(max_emotion)
            print(f"[emotion_detector] Detected: {max_emotion} ({max_score:.4f}) -> mapped to: {mapped}")
            return mapped
        
        return None
        
    except Exception as e:
        print(f"[emotion_detector] Error parsing predictions: {e}")
        import traceback
        traceback.print_exc()
        return None



def _map_hume_emotion_to_mood(hume_emotion: str) -> str:
    """
    Map Hume's 48 emotions to simple mood categories suitable for child ASD therapy.
    
    Hume provides rich emotional granularity (Joy, Amusement, Interest, etc.)
    We map these to 10 simple moods for the app.
    
    Args:
        hume_emotion: Emotion name from Hume API
        
    Returns:
        Corresponding app mood: happy, sad, calm, focused, energized, anxious, angry, surprised, fearful, or loving
    """
    emotion_lower = hume_emotion.lower()
    
    # Happy/Positive moods: Joy, Amusement, Ecstasy, Contentment
    happy_emotions = {
        "joy", "amusement", "ecstasy", "satisfaction", "contentment",
        "relief", "triumph"
    }
    
    # Sad/Negative moods: Sadness, Disappointment, Empathic Pain, Distress
    sad_emotions = {
        "sadness", "empathic pain", "distress", "shame", "guilt", "embarrassment",
        "disappointment", "nostalgia", "pain", "boredom"
    }
    # Angry moods
    angry_emotions = {
        "anger", "irritation", "annoyance", "rage", "frustration", "hostility"
    }

    # Fearful moods
    fearful_emotions = {
        "fear", "terror", "panic", "horror", "apprehension",
        "alarm"
    }

    # Surprised
    surprised_emotions = {"surprise", "amazement", "astonishment"}

    # Loving / Affection
    loving_emotions = {"affection", "love", "fondness", "admiration"}

    # Energized / excited
    energized_emotions = {"excitement", "enthusiasm", "energy", "eagerness"}

    # Anxious / worried
    anxious_emotions = {"anxiety", "worry", "nervousness", "unease"}

    # Focused / interest
    focused_emotions = {"interest", "focus", "concentration", "curiosity"}

    # Calm / relaxed
    calm_emotions = {"calm", "relaxed", "contentment", "serenity"}

    # Map to app moods
    if emotion_lower in happy_emotions:
        return "happy"
    if emotion_lower in sad_emotions:
        return "sad"
    if emotion_lower in angry_emotions:
        return "angry"
    if emotion_lower in fearful_emotions:
        return "fearful"
    if emotion_lower in surprised_emotions:
        return "surprised"
    if emotion_lower in loving_emotions:
        return "loving"
    if emotion_lower in energized_emotions:
        return "energized"
    if emotion_lower in anxious_emotions:
        return "anxious"
    if emotion_lower in focused_emotions:
        return "focused"
    if emotion_lower in calm_emotions:
        return "calm"

    # Fallback heuristics
    if "joy" in emotion_lower or "happy" in emotion_lower or "smile" in emotion_lower:
        return "happy"
    if "sad" in emotion_lower or "cry" in emotion_lower:
        return "sad"
    return "calm"

