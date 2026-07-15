"""
Emotion detection module with Face++ support and multiple fallbacks.

Priority:
1. Face++ API (cloud-compatible, no local ML models needed)
2. DeepFace (local, high accuracy)
3. Local emotion model (lightweight)
4. OpenCV cascade (basic fallback)

Face++ is ideal for Streamlit Cloud since it's just HTTP API calls.
"""

import os
from typing import Optional, Dict, List, Tuple

# Optional imports - don't fail if these are missing, just disable features
cv2 = None
np = None
try:
    import cv2 as _cv2
    import numpy as _np
    cv2 = _cv2
    np = _np
except (ImportError, OSError) as e:
    print(f"[emotion_detector] OpenCV/NumPy import failed (disabling local face detection): {e}")

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

try:
    from PIL import Image
except ImportError:
    Image = None

try:
    from transformers import AutoImageProcessor, AutoModelForImageClassification
    TRANSFORMERS_AVAILABLE = True
except Exception:
    TRANSFORMERS_AVAILABLE = False

# PRIORITY 1: Try to import Face++ API detector (cloud-compatible)
# This should ALWAYS be attempted first and doesn't require cv2/numpy
FACEPP_AVAILABLE = False
FACEPP_ERROR = None
try:
    from emotion_detector_facepp import analyze_frame as facepp_analyze_frame
    FACEPP_AVAILABLE = True
    print("[emotion_detector] ✓ Face++ API detector available")
except ImportError as e:
    FACEPP_ERROR = str(e)
    print(f"[emotion_detector] Face++ detector unavailable: {e}")

# Read configuration values
EMOTION_CONFIDENCE_THRESHOLD = float(os.getenv("EMOTION_CONFIDENCE_THRESHOLD", "0.35"))
SECONDARY_EMOTION_THRESHOLD = float(os.getenv("EMOTION_SECONDARY_THRESHOLD", "0.22"))
LOCAL_MODEL_CONFIDENCE_THRESHOLD = float(os.getenv("LOCAL_EMOTION_CONFIDENCE_THRESHOLD", "0.40"))
MAX_IMAGE_EDGE = int(os.getenv("EMOTION_MAX_IMAGE_EDGE", "480"))
FACE_MODEL_SIZE = int(os.getenv("EMOTION_FACE_MODEL_SIZE", "160"))
USE_HUGGINGFACE_MODEL = os.getenv("USE_HUGGINGFACE_EMOTION_MODEL", "1") != "0"

# Try to import DeepFace - most robust emotion detection
DEEPFACE_AVAILABLE = False
DEEPFACE_ERROR = None
try:
    from deepface import DeepFace
    DEEPFACE_AVAILABLE = True
    print("[emotion_detector] DeepFace loaded successfully [OK]")
except ImportError as e:
    DEEPFACE_ERROR = str(e)
    print(f"[emotion_detector] DeepFace import error (install with: pip install deepface): {e}")

# Fallback: local emotion model
LOCAL_MODEL_AVAILABLE = False
try:
    from emotion_behavior.core import detect_emotion_from_bgr
    LOCAL_MODEL_AVAILABLE = True
    print("[emotion_detector] Local emotion model available [OK]")
except Exception as e:
    print(f"[emotion_detector] Local emotion model error: {e}")

# Stronger pretrained model for facial emotion recognition
PRETRAINED_MODEL_AVAILABLE = False
_PRETRAINED_PROCESSOR = None
_PRETRAINED_MODEL = None
_PRETRAINED_MODEL_NAME = os.getenv("EMOTION_MODEL_NAME", "dima806/facial_emotions_image_detection")

if USE_HUGGINGFACE_MODEL and TRANSFORMERS_AVAILABLE:
    try:
        _PRETRAINED_PROCESSOR = AutoImageProcessor.from_pretrained(_PRETRAINED_MODEL_NAME)
        _PRETRAINED_MODEL = AutoModelForImageClassification.from_pretrained(_PRETRAINED_MODEL_NAME)
        _PRETRAINED_MODEL.eval()
        PRETRAINED_MODEL_AVAILABLE = True
        print(f"[emotion_detector] Pretrained emotion model loaded: {_PRETRAINED_MODEL_NAME}")
    except Exception as e:
        print(f"[emotion_detector] Pretrained model load failed: {e}")
else:
    if USE_HUGGINGFACE_MODEL:
        print("[emotion_detector] Hugging Face transformers available, but pretrained emotion model failed to load or is disabled.")
    else:
        print("[emotion_detector] Hugging Face emotion model disabled by default. Set USE_HUGGINGFACE_EMOTION_MODEL=1 to enable.")

# Global error tracking
_LAST_ERROR: Optional[str] = None

# Emotion normalization for music therapy
EMOTION_NORMALIZATION = {
    # Normalize to therapy-friendly emotions
    "neutral": "calm",
    "surprise": "focused",
    "disgust": "focused",
    "fear": "focused",
    # These map directly
    "happy": "happy",
    "sad": "sad",
    "angry": "angry",
}

# Emotion classes from DeepFace
DEEPFACE_EMOTIONS = [
    "angry",      # High arousal, negative
    "disgust",    # Medium arousal, negative
    "fear",       # High arousal, negative
    "happy",      # High arousal, positive
    "sad",        # Low arousal, negative
    "surprise",   # Medium arousal, neutral/positive
    "neutral",    # Low arousal, neutral
]


def get_last_detection_error() -> Optional[str]:
    """Return the most recent detection error for UI display."""
    return _LAST_ERROR


def _set_error(message: str) -> None:
    """Set the error message for UI display."""
    global _LAST_ERROR
    _LAST_ERROR = message
    print(f"[emotion_detector] Error: {message}")


def normalize_emotion(emotion: str) -> str:
    """
    Normalize raw emotion labels to therapy-friendly emotions.
    
    Maps: neutral→calm, surprise/disgust/fear→focused, others unchanged
    """
    return EMOTION_NORMALIZATION.get(emotion, emotion)


def _detect_face_region(frame_bgr: np.ndarray) -> Optional[Tuple[int, int, int, int]]:
    """Locate the largest face in the frame."""
    try:
        gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
        face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        )
        if face_cascade.empty():
            return None
        faces = face_cascade.detectMultiScale(gray, 1.3, 5)
        if len(faces) == 0:
            return None
        return max(faces, key=lambda box: box[2] * box[3])
    except Exception:
        return None


def _prepare_frame_for_inference(frame_bgr: np.ndarray) -> np.ndarray:
    """Downscale large images to keep inference fast."""
    height, width = frame_bgr.shape[:2]
    if max(height, width) > MAX_IMAGE_EDGE:
        scale = MAX_IMAGE_EDGE / float(max(height, width))
        frame_bgr = cv2.resize(frame_bgr, (int(width * scale), int(height * scale)))
    return frame_bgr


def _extract_face_image(frame_bgr: np.ndarray) -> Optional[np.ndarray]:
    """Crop the largest face and resize it for inference."""
    face_box = _detect_face_region(frame_bgr)
    if face_box is None:
        return None
    x, y, w, h = face_box
    face_roi = frame_bgr[y : y + h, x : x + w]
    if face_roi.size == 0:
        return None
    resized = cv2.resize(face_roi, (FACE_MODEL_SIZE, FACE_MODEL_SIZE))
    return resized


def _detect_smile(frame_bgr: np.ndarray) -> bool:
    """Validate a happy prediction by checking for a smile."""
    try:
        gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
        face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        )
        smile_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_smile.xml'
        )
        if face_cascade.empty() or smile_cascade.empty():
            return False

        faces = face_cascade.detectMultiScale(gray, 1.3, 5)
        if len(faces) == 0:
            return False

        x, y, w, h = faces[0]
        roi_gray = gray[y : y + h, x : x + w]
        smiles = smile_cascade.detectMultiScale(
            roi_gray,
            scaleFactor=1.7,
            minNeighbors=15,
            minSize=(25, 25),
        )
        return len(smiles) > 0
    except Exception:
        return False


def _analyze_pretrained_model(
    frame_bgr: np.ndarray,
    min_confidence: float = 0.35,
    require_face: bool = False,
    allowed_labels: Optional[set] = None,
) -> Optional[str]:
    """Run a stronger Hugging Face pretrained classifier on a cropped face or full frame."""
    global _PRETRAINED_PROCESSOR, _PRETRAINED_MODEL
    if not PRETRAINED_MODEL_AVAILABLE or _PRETRAINED_PROCESSOR is None or _PRETRAINED_MODEL is None:
        return None

    face_image = _extract_face_image(frame_bgr)
    image_array = face_image if face_image is not None else frame_bgr
    if require_face and face_image is None:
        return None

    try:
        image = Image.fromarray(cv2.cvtColor(image_array, cv2.COLOR_BGR2RGB))
        inputs = _PRETRAINED_PROCESSOR(images=image, return_tensors="pt")
        with np.errstate(all='ignore'):
            outputs = _PRETRAINED_MODEL(**inputs)
        probs = outputs.logits.softmax(dim=-1).detach().cpu().numpy()[0]
        predicted_index = int(np.argmax(probs))
        predicted_label = _PRETRAINED_MODEL.config.id2label.get(predicted_index, "")
        confidence = float(probs[predicted_index])
        print(f"[emotion_detector] Pretrained model: {predicted_label} ({confidence:.1%})")
        if confidence < min_confidence:
            return None
        label = predicted_label.lower()
        if allowed_labels and label not in allowed_labels:
            return None
        if label == 'happy' and not _detect_smile(frame_bgr):
            return None
        return normalize_emotion(label)
    except Exception as e:
        print(f"[emotion_detector] Pretrained model error: {e}")
        return None


def analyze_frame(frame_bgr: np.ndarray) -> Optional[str]:
    """
    Analyze a video frame for facial emotion.
    
    Args:
        frame_bgr: numpy array in BGR format (from OpenCV)
    
    Returns:
        str: Normalized emotion label (calm, happy, sad, angry, focused)
        None: If no face detected or error occurred
    
    Priority:
        1. Face++ API (cloud-compatible, works on Streamlit Cloud)
        2. Pretrained Hugging Face model (high-confidence only)
        3. DeepFace (recommended, real-time capable)
        4. Local emotion model (fallback)
        5. OpenCV cascade (last resort)
    """
    global _LAST_ERROR
    _LAST_ERROR = None

    if frame_bgr is None or frame_bgr.size == 0:
        _set_error("Empty image frame provided")
        return None

    frame_bgr = _prepare_frame_for_inference(frame_bgr)

    # PRIORITY 1: Try Face++ API first (cloud-compatible, works on Streamlit Cloud)
    if FACEPP_AVAILABLE:
        try:
            emotion = facepp_analyze_frame(frame_bgr)
            if emotion:
                return emotion
        except Exception as e:
            print(f"[emotion_detector] Face++ analysis failed: {e}")

    # PRIORITY 2: Use the stronger pretrained Hugging Face model if available.
    if PRETRAINED_MODEL_AVAILABLE:
        # Use the Hugging Face model only for high-confidence face emotions.
        # This keeps pretrained inference as a boost, while letting DeepFace handle
        # the harder open-set cases and low-confidence predictions.
        emotion = _analyze_pretrained_model(
            frame_bgr,
            min_confidence=0.85,
            allowed_labels={'happy', 'neutral', 'angry', 'sad'},
        )
        if emotion:
            return emotion

    # PRIORITY 3: Then use DeepFace for real-time capable detection.
    if DEEPFACE_AVAILABLE:
        emotion = _analyze_deepface(frame_bgr)
        if emotion:
            return emotion

    # PRIORITY 4: Fallback to local model
    if LOCAL_MODEL_AVAILABLE:
        emotion = _analyze_local_model(frame_bgr)
        if emotion:
            return emotion
    
    # PRIORITY 5: Last resort: OpenCV
    emotion = _analyze_opencv(frame_bgr)
    return emotion


def _analyze_deepface(frame_bgr: np.ndarray) -> Optional[str]:
    """
    Analyze emotion using DeepFace with a preferred backend list.
    
    Args:
        frame_bgr: numpy array in BGR format
    
    Returns:
        str: Normalized emotion label or None if no face detected
    """
    frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
    backends = ['retinaface', 'yolov8m', 'opencv']
    results = []
    last_error = None

    for backend in backends:
        try:
            print(f"[emotion_detector] DeepFace attempting backend: {backend}")
            result = DeepFace.analyze(
                img_path=frame_rgb,
                actions=['emotion'],
                enforce_detection=False,
                detector_backend=backend,
                silent=True,
            )

            if not result or len(result) == 0:
                print(f"[emotion_detector] DeepFace: No face detected using {backend}")
                continue

            emotion_scores = result[0].get('emotion', {})
            if not emotion_scores:
                print(f"[emotion_detector] DeepFace: No emotion scores returned using {backend}")
                continue

            sorted_scores = sorted(emotion_scores.items(), key=lambda x: x[1], reverse=True)
            dominant_emotion, top_score = sorted_scores[0]
            confidence = top_score / 100.0
            print(f"[emotion_detector] DeepFace ({backend}): {dominant_emotion} ({confidence:.1%})")

            if confidence < EMOTION_CONFIDENCE_THRESHOLD:
                last_error = (
                    f"DeepFace low confidence: {dominant_emotion} ({confidence:.1%})"
                )
                print(f"[emotion_detector] {last_error}")
                continue

            smile_validated = True
            if dominant_emotion == 'happy':
                smile_validated = _detect_smile(frame_bgr)
                if not smile_validated:
                    print(
                        "[emotion_detector] DeepFace happy validation failed: no smile detected"
                    )
                    alternate = None
                    for label, score in sorted_scores[1:]:
                        if score / top_score >= 0.75 and score / 100.0 >= SECONDARY_EMOTION_THRESHOLD:
                            alternate = label
                            break
                    if alternate:
                        print(
                            f"[emotion_detector] DeepFace happy fallback to alternate emotion: {alternate}"
                        )
                        dominant_emotion = alternate
                    else:
                        print(
                            "[emotion_detector] DeepFace happy fallback no alternate, keeping happy for later consensus"
                        )

            results.append((dominant_emotion, confidence, backend, smile_validated))

        except Exception as e:
            error_msg = str(e)
            last_error = error_msg
            print(f"[emotion_detector] DeepFace backend {backend} failed: {error_msg}")
            if "Yolo is an optional detector" in error_msg or "ultralytics" in error_msg.lower():
                continue
            if "No face" in error_msg:
                _set_error(f"DeepFace: No face detected using {backend}")
                return None
            if "CUDA" in error_msg or "GPU" in error_msg:
                _set_error("DeepFace: GPU error (will retry on CPU)")
                return None
            continue

    if not results:
        _set_error(f"DeepFace error: {last_error}")
        return None

    from collections import Counter
    emotion_counts = Counter([emotion for emotion, _, _, _ in results])
    most_common, count = emotion_counts.most_common(1)[0]

    # If all happy predictions lack smile validation, choose calm before majority.
    happy_results = [(emotion, _, _, smile) for emotion, _, _, smile in results if emotion == 'happy']
    if len(happy_results) >= 2 and all(not smile for _, _, _, smile in happy_results):
        print("[emotion_detector] DeepFace multiple happy predictions without smiles; using calm")
        return normalize_emotion('neutral')

    if count >= 2:
        print(f"[emotion_detector] DeepFace majority vote: {most_common} ({count}/{len(results)})")
        return normalize_emotion(most_common)

    # No clear majority; choose the backend result with the highest confidence.
    best_result = max(results, key=lambda item: item[1])
    print(
        f"[emotion_detector] DeepFace best single backend result: {best_result[0]} ({best_result[1]:.1%}) from {best_result[2]}"
    )
    return normalize_emotion(best_result[0])


def _analyze_local_model(frame_bgr: np.ndarray) -> Optional[str]:
    """
    Fallback: Analyze emotion using local trained model (emotion_behavior module).
    
    Args:
        frame_bgr: numpy array in BGR format
    
    Returns:
        str: Normalized emotion label or None if detection fails
    """
    try:
        prediction = detect_emotion_from_bgr(frame_bgr)
        
        if not prediction:
            return None
        
        print(f"[emotion_detector] Local model: {prediction.label} ({prediction.confidence:.1%})")
        if prediction.confidence < LOCAL_MODEL_CONFIDENCE_THRESHOLD:
            print(
                f"[emotion_detector] Local model low confidence: {prediction.label} ({prediction.confidence:.1%})"
            )
            return None
        
        normalized = normalize_emotion(prediction.label)
        _LAST_ERROR = None
        return normalized
        
    except Exception as e:
        print(f"[emotion_detector] Local model error: {e}")
        return None


def _analyze_opencv(frame_bgr: np.ndarray) -> Optional[str]:
    """
    Fallback: Simple emotion detection using OpenCV Haar cascade.
    
    Very basic - only detects happy vs calm based on face features.
    Used when better models unavailable.
    
    Args:
        frame_bgr: numpy array in BGR format
    
    Returns:
        str: Simple emotion ('calm' or 'happy') or None
    """
    try:
        cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        face_cascade = cv2.CascadeClassifier(cascade_path)
        
        gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.3, 5)
        
        if len(faces) == 0:
            _set_error("OpenCV: No face detected")
            return None
        
        # Very basic heuristic: if face is detected, assume calm
        # (Better models always preferred)
        print("[emotion_detector] OpenCV fallback: default to 'calm'")
        _set_error("Using OpenCV fallback (limited accuracy). Install DeepFace for better results.")
        return "calm"
        
    except Exception as e:
        _set_error(f"OpenCV error: {e}")
        return None


def analyze_video_batch(
    video_path: str,
    sample_rate: int = 2,
    max_frames: int = None
) -> Dict:
    """
    Batch analyze emotions across video frames for efficiency.
    
    Args:
        video_path: Path to video file
        sample_rate: Process every Nth frame (2 = every 2nd frame)
        max_frames: Maximum frames to process (None = all)
    
    Returns:
        dict: {
            'emotions': [list of detected emotions by frame],
            'dominant_emotion': most common emotion,
            'frame_count': total frames processed,
            'success': whether processing completed successfully
        }
    """
    emotions = []
    frame_count = 0
    
    try:
        cap = cv2.VideoCapture(video_path)
        
        if not cap.isOpened():
            _set_error(f"Cannot open video: {video_path}")
            return {'emotions': [], 'dominant_emotion': None, 'frame_count': 0, 'success': False}
        
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        
        while True:
            ret, frame = cap.read()
            
            if not ret:
                break
            
            frame_count += 1
            
            # Skip frames based on sample_rate
            if frame_count % sample_rate != 0:
                continue
            
            # Check max_frames limit
            if max_frames and len(emotions) >= max_frames:
                break
            
            # Detect emotion in this frame
            emotion = analyze_frame(frame)
            
            if emotion:
                emotions.append(emotion)
                timestamp = frame_count / fps
                print(f"[emotion_detector] Frame {frame_count} ({timestamp:.1f}s): {emotion}")
        
        cap.release()
        
        # Find dominant emotion
        if emotions:
            emotion_counts = {}
            for e in emotions:
                emotion_counts[e] = emotion_counts.get(e, 0) + 1
            dominant_emotion = max(emotion_counts, key=emotion_counts.get)
        else:
            dominant_emotion = None
        
        return {
            'emotions': emotions,
            'dominant_emotion': dominant_emotion,
            'frame_count': frame_count,
            'frames_analyzed': len(emotions),
            'success': True
        }
        
    except Exception as e:
        _set_error(f"Video analysis error: {e}")
        return {
            'emotions': emotions,
            'dominant_emotion': None,
            'frame_count': frame_count,
            'frames_analyzed': len(emotions),
            'success': False
        }


def setup_deepface():
    """
    Pre-download DeepFace models for faster first-time use.
    
    This downloads the emotion detection model (~100MB) to local cache.
    Called on app startup to avoid delays during first emotion detection.
    """
    if not DEEPFACE_AVAILABLE:
        print("[emotion_detector] DeepFace not available, skipping setup")
        return False
    
    try:
        print("[emotion_detector] Pre-loading DeepFace emotion model...")
        
        # Create a dummy frame to trigger model download
        dummy_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        dummy_frame[100:200, 100:200] = 255  # Add some contrast
        
        # This will download models if not already cached
        DeepFace.analyze(
            img_path=dummy_frame,
            actions=['emotion'],
            enforce_detection=False,  # Don't fail on dummy frame
            detector_backend='yolov8m',
            silent=True
        )
        
        print("[emotion_detector] DeepFace models loaded [OK]")
        return True
        
    except Exception as e:
        print(f"[emotion_detector] DeepFace pre-loading error (non-fatal): {e}")
        # Model will still be downloaded on first real use
        return False


# Module initialization
if DEEPFACE_AVAILABLE:
    print("[emotion_detector] [OK] Ready: DeepFace emotion detection active")
elif LOCAL_MODEL_AVAILABLE:
    print("[emotion_detector] [OK] Ready: Local model emotion detection active")
else:
    print("[emotion_detector] [WARNING] Warning: Only OpenCV fallback available (limited accuracy)")
    print("[emotion_detector]    Install DeepFace: pip install deepface")
