"""
Emotion detection module using Hume AI REST API.

This module provides emotion detection using Hume's high-quality batch API
with OpenCV as an instant fallback.
"""

import os
import time
import base64
import json
import asyncio
from typing import Optional, Dict, Any
import numpy as np
import cv2
from PIL import Image
import io
from dotenv import load_dotenv

# Try to import hume SDK (v0.13+ uses AsyncHumeClient)
try:
    from hume import AsyncHumeClient
    from hume.expression_measurement.stream import Config
    from hume.expression_measurement.stream.socket_client import StreamConnectOptions
    from hume.expression_measurement.stream.types import StreamFace
    HUME_SDK_AVAILABLE = True
except ImportError as e:
    HUME_SDK_AVAILABLE = False
    print(f"[emotion_detector] Hume import error: {e}")
    print("[emotion_detector] Hume SDK not available. Install with: pip install hume")

load_dotenv()

# Configuration
HUME_API_KEY = os.getenv("HUME_API_KEY", "")
HUME_PROB_THRESHOLD = float(os.getenv("HUME_PROB_THRESHOLD", "0.3"))

# Enable Hume by default (it's the most accurate)
USE_HUME = os.getenv("USE_HUME", "1") == "1" and bool(HUME_API_KEY) and HUME_SDK_AVAILABLE

# Always make emotion detection available
EMOTION_DETECTION_AVAILABLE = True

# Print configuration on module load
print(f"[emotion_detector] Config: USE_HUME={USE_HUME}, API_KEY={'SET' if HUME_API_KEY else 'MISSING'}, SDK={'OK' if HUME_SDK_AVAILABLE else 'MISSING'}, THRESHOLD={HUME_PROB_THRESHOLD}")


def analyze_frame(frame_data: np.ndarray) -> Optional[str]:
    """
    Analyze a video frame for emotion detection.
    
    Priority:
    1. Hume REST API (high accuracy batch processing)
    2. OpenCV detector (instant fallback)
    
    Args:
        frame_data: numpy array of the video frame in BGR format
        
    Returns:
        Detected emotion string (happy, sad, angry, fearful, surprised, calm) or None
    """
    if frame_data is None or frame_data.size == 0:
        return None
    
    # Priority 1: Try Hume Streaming API first if enabled
    if USE_HUME and HUME_API_KEY and HUME_SDK_AVAILABLE:
        try:
            emotion = _analyze_via_streaming_sync(frame_data)
            if emotion:
                print(f"[emotion_detector] ✓ Hume detected: {emotion}")
                return emotion
        except Exception as e:
            print(f"[emotion_detector] Hume error: {e}")
    
    # Priority 2: Fallback to OpenCV detector
    opencv_emotion = _opencv_detector(frame_data)
    if opencv_emotion:
        return opencv_emotion
    
    print("[emotion_detector] ✗ No emotion detected by any method")
    return None


def _analyze_via_rest(frame_bytes: bytes) -> Optional[str]:
    """
    Analyze frame using Hume AI's REST API (batch processing).
    Submits job and polls for completion (max 5 seconds).
    
    Args:
        frame_bytes: JPEG-encoded frame bytes
        
    Returns:
        Detected emotion string or None
    """
    try:
        # Prepare the file for upload
        files = {
            'file': ('frame.jpg', frame_bytes, 'image/jpeg')
        }
        
        # Configure models - face detection only (no custom config needed)
        json_config = {
            'models': {
                'face': {}
            }
        }
        
        data = {
            'json': json.dumps(json_config)
        }
        
        headers = {
            'X-Hume-Api-Key': HUME_API_KEY
        }
        
        # Submit job
        print(f"[emotion_detector] Submitting to Hume API...")
        response = requests.post(
            HUME_API_URL,
            headers=headers,
            data=data,
            files=files,
            timeout=10
        )
        
        if response.status_code != 200:
            print(f"[emotion_detector] Hume API error: {response.status_code}")
            print(f"[emotion_detector] Response: {response.text[:200]}")
            return None
        
        print(f"[emotion_detector] Job submitted successfully")
        
        job_data = response.json()
        job_id = job_data.get('job_id')
        
        if not job_id:
            print("[emotion_detector] No job_id received from Hume")
            print(f"[emotion_detector] Response data: {job_data}")
            return None
        
        print(f"[emotion_detector] Job ID: {job_id}, polling for completion...")
        
        # Poll for job completion (max 5 seconds, 10 attempts)
        max_attempts = 10
        for attempt in range(max_attempts):
            time.sleep(0.5)  # Wait 500ms between checks
            
            status_response = requests.get(
                f"{HUME_API_URL}/{job_id}",
                headers=headers,
                timeout=5
            )
            
            if status_response.status_code != 200:
                continue
            
            status_data = status_response.json()
            state = status_data.get('state', {}).get('status')
            
            if state == 'COMPLETED':
                print(f"[emotion_detector] Job completed! Fetching predictions...")
                # Get predictions
                pred_response = requests.get(
                    f"{HUME_API_URL}/{job_id}/predictions",
                    headers=headers,
                    timeout=5
                )
                
                if pred_response.status_code == 200:
                    predictions = pred_response.json()
                    emotion = _extract_emotion_from_rest(predictions)
                    return emotion
                else:
                    print(f"[emotion_detector] Failed to get predictions: {pred_response.status_code}")
                break
            elif state == 'FAILED':
                print(f"[emotion_detector] Hume job failed")
                print(f"[emotion_detector] Error: {status_data.get('state', {}).get('error', 'Unknown')}")
                break
            elif state in ['IN_PROGRESS', 'QUEUED']:
                # Still processing, continue polling
                pass
            else:
                print(f"[emotion_detector] Unknown job state: {state}")
                break
        
    except requests.exceptions.Timeout:
        print("[emotion_detector] Hume API timeout")
    except Exception as e:
        print(f"[emotion_detector] Hume REST error: {e}")
    
    return None


def _extract_emotion_from_rest(predictions: list) -> Optional[str]:
    """
    Extract emotion from Hume REST API predictions response.
    
    Args:
        predictions: JSON predictions list from Hume batch job
        
    Returns:
        Detected emotion string or None
    """
    try:
        # Navigate the prediction structure
        if not isinstance(predictions, list) or len(predictions) == 0:
            return None
        
        first_result = predictions[0]
        results = first_result.get('results', {})
        predictions_list = results.get('predictions', [])
        
        if not predictions_list or len(predictions_list) == 0:
            return None
        
        # Get face predictions
        models = predictions_list[0].get('models', {})
        face_data = models.get('face', {})
        grouped_predictions = face_data.get('grouped_predictions', [])
        
        if not grouped_predictions or len(grouped_predictions) == 0:
            return None
        
        # Get first face's predictions
        face_predictions = grouped_predictions[0].get('predictions', [])
        if not face_predictions or len(face_predictions) == 0:
            return None
        
        # Get emotions from first frame
        emotions = face_predictions[0].get('emotions', [])
        if not emotions:
            return None
        
        # Define the 10 main emotions we want to focus on
        main_emotions = {
            'Joy', 'Sadness', 'Anger', 'Fear', 'Surprise (positive)', 
            'Surprise (negative)', 'Disgust', 'Calmness', 'Excitement', 'Contentment'
        }
        
        # Filter to only main emotions, then sort by score
        main_emotion_scores = [e for e in emotions if e.get('name') in main_emotions]
        all_sorted = sorted(emotions, key=lambda x: x.get('score', 0), reverse=True)
        
        # Print top 5 overall emotions for debugging
        print(f"[emotion_detector] Hume top 5 (all):")
        for i, em in enumerate(all_sorted[:5]):
            marker = "★" if em.get('name') in main_emotions else " "
            print(f"  {marker} {i+1}. {em['name']}: {em['score']:.3f}")
        
        # If we have main emotions with good scores, use them
        if main_emotion_scores:
            sorted_main = sorted(main_emotion_scores, key=lambda x: x.get('score', 0), reverse=True)
            top_main = sorted_main[0]
            
            if top_main['score'] >= HUME_PROB_THRESHOLD:
                hume_emotion_name = top_main['name']
                mapped_emotion = _map_hume_emotion_to_mood(hume_emotion_name)
                print(f"[emotion_detector] ✓ Hume: {hume_emotion_name} ({top_main['score']:.2f}) → {mapped_emotion}")
                return mapped_emotion
        
        # Fallback: use any top emotion above threshold
        if all_sorted[0].get('score', 0) >= HUME_PROB_THRESHOLD:
            top_emotion = all_sorted[0]
            hume_emotion_name = top_emotion['name']
            mapped_emotion = _map_hume_emotion_to_mood(hume_emotion_name)
            print(f"[emotion_detector] ✓ Hume (fallback): {hume_emotion_name} ({top_emotion['score']:.2f}) → {mapped_emotion}")
            return mapped_emotion
        
        # If nothing above threshold, use top main emotion if reasonably high
        if main_emotion_scores and sorted_main[0].get('score', 0) > 0.15:
            top_main = sorted_main[0]
            hume_emotion_name = top_main['name']
            mapped_emotion = _map_hume_emotion_to_mood(hume_emotion_name)
            print(f"[emotion_detector] ✓ Hume (low conf): {hume_emotion_name} ({top_main['score']:.2f}) → {mapped_emotion}")
            return mapped_emotion
        
    except Exception as e:
        print(f"[emotion_detector] Error extracting emotion: {e}")
    
    return None


def _opencv_detector(frame_data: np.ndarray) -> Optional[str]:
    """
    OpenCV-based emotion detector with enhanced feature detection.
    Detects happy, sad, surprised, and defaults to calm.
    
    Args:
        frame_data: numpy array of the video frame in BGR format
        
    Returns:
        Detected emotion string
    """
    try:
        gray = cv2.cvtColor(frame_data, cv2.COLOR_BGR2GRAY)
        
        # Load haar cascades
        face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        )
        eye_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_eye.xml'
        )
        smile_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + 'haarcascade_smile.xml'
        )
        
        # Detect face first
        faces = face_cascade.detectMultiScale(gray, 1.3, 5)
        
        if len(faces) == 0:
            print(f"[emotion_detector] ✓ OpenCV: no face → calm")
            return "calm"
        
        # Analyze first detected face
        (x, y, w, h) = faces[0]
        face_roi_gray = gray[y:y+h, x:x+w]
        
        # Detect eyes with more lenient parameters
        eyes = eye_cascade.detectMultiScale(
            face_roi_gray, 
            scaleFactor=1.1, 
            minNeighbors=5,  # Reduced from 10 for better detection
            minSize=(20, 20)
        )
        
        # Detect smile with adjusted parameters
        smiles = smile_cascade.detectMultiScale(
            face_roi_gray,
            scaleFactor=1.7,  # Slightly more sensitive
            minNeighbors=15,  # Reduced from 20
            minSize=(25, 25)
        )
        
        # Debug logging
        print(f"[emotion_detector] OpenCV: face=1, eyes={len(eyes)}, smiles={len(smiles)}")
        
        # Improved emotion logic - prioritize smile detection
        if len(smiles) > 0:
            print(f"[emotion_detector] ✓ OpenCV detected: smile → happy")
            return "happy"
        elif len(eyes) >= 2:  # Normal: 2 eyes detected
            print(f"[emotion_detector] ✓ OpenCV detected: neutral face → calm")
            return "calm"
        else:  # Less than 2 eyes or unusual detection
            # Default to calm instead of sad (more neutral fallback)
            print(f"[emotion_detector] ✓ OpenCV detected: unclear → calm")
            return "calm"
        
    except Exception as e:
        print(f"[emotion_detector] OpenCV error: {e}")
        return "calm"


def _convert_to_jpeg_bytes(frame_data: np.ndarray, quality: int = 85) -> Optional[bytes]:
    """
    Convert numpy array frame to JPEG bytes for API submission.
    
    Args:
        frame_data: numpy array in BGR format
        quality: JPEG quality (1-100)
        
    Returns:
        JPEG-encoded bytes or None
    """
    try:
        # Convert to PIL Image
        from PIL import Image
        import cv2
        
        # Convert BGR to RGB
        frame_rgb = cv2.cvtColor(frame_data, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(frame_rgb)
        
        # Resize if too large (max 1024x1024 for faster processing)
        max_size = 1024
        if pil_image.width > max_size or pil_image.height > max_size:
            pil_image.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)
        
        # Convert to JPEG bytes
        buffer = io.BytesIO()
        pil_image.save(buffer, format='JPEG', quality=quality)
        return buffer.getvalue()
        
    except Exception as e:
        print(f"[emotion_detector] Frame conversion error: {e}")
        return None


def _map_hume_emotion_to_mood(hume_emotion: str) -> str:
    """
    Map Hume emotions to the app's mood system.
    Focused on 10 main emotions for clearer detection.
    
    Args:
        hume_emotion: Emotion name from Hume API
        
    Returns:
        Mood category string (happy, sad, angry, fearful, surprised, calm, energetic, relaxed, focused, romantic)
    """
    # Primary mapping for the 10 main emotions we focus on
    primary_emotions = {
        # Core emotions (direct mapping)
        'Joy': 'happy',
        'Sadness': 'sad',
        'Anger': 'angry',
        'Fear': 'fearful',
        'Surprise (positive)': 'surprised',
        'Surprise (negative)': 'surprised',
        'Disgust': 'angry',
        'Calmness': 'calm',
        'Excitement': 'energetic',
        'Contentment': 'relaxed',
    }
    
    # Check primary emotions first
    if hume_emotion in primary_emotions:
        return primary_emotions[hume_emotion]
    
    # Extended mapping for all 48 Hume emotions
    extended_map = {
        # Happy cluster
        'Amusement': 'happy',
        'Satisfaction': 'happy',
        'Triumph': 'happy',
        'Pride': 'happy',
        'Relief': 'happy',
        'Gratitude': 'happy',
        'Admiration': 'happy',
        'Adoration': 'happy',
        'Aesthetic Appreciation': 'happy',
        'Love': 'romantic',
        'Romance': 'romantic',
        
        # Sad cluster
        'Disappointment': 'sad',
        'Empathic Pain': 'sad',
        'Sympathy': 'sad',
        'Tiredness': 'sad',
        'Boredom': 'sad',
        'Guilt': 'sad',
        'Shame': 'sad',
        'Embarrassment': 'sad',
        'Pain': 'sad',
        
        # Angry cluster
        'Contempt': 'angry',
        'Annoyance': 'angry',
        'Envy': 'angry',
        
        # Fearful cluster
        'Anxiety': 'fearful',
        'Horror': 'fearful',
        'Doubt': 'fearful',
        'Confusion': 'fearful',
        'Awkwardness': 'fearful',
        'Distress': 'fearful',
        
        # Calm/Focused cluster
        'Concentration': 'focused',
        'Contemplation': 'focused',
        'Determination': 'focused',
        'Interest': 'focused',
        
        # Energetic cluster
        'Enthusiasm': 'energetic',
        
        # Surprised cluster
        'Realization': 'surprised',
        'Awe': 'surprised',
        
        # Relaxed cluster
        'Nostalgia': 'relaxed',
        'Desire': 'romantic',
        'Craving': 'energetic',
        'Entrancement': 'focused',
    }
    
    # Use extended mapping or default to calm
    return extended_map.get(hume_emotion, 'calm')


def normalize_emotion(emotion: str) -> str:
    """
    Normalize emotion strings to standard format.
    
    Args:
        emotion: Raw emotion string
        
    Returns:
        Normalized emotion string
    """
    if not emotion:
        return "calm"
    
    emotion_lower = emotion.lower().strip()
    
    # Valid emotions in our system
    valid_emotions = {
        'happy', 'sad', 'angry', 'fearful', 'surprised', 
        'calm', 'energetic', 'relaxed', 'focused', 'romantic'
    }
    
    if emotion_lower in valid_emotions:
        return emotion_lower
    
    # Map common alternatives
    alternatives = {
        'neutral': 'calm',
        'content': 'calm',
        'peaceful': 'calm',
        'excited': 'energetic',
        'hyper': 'energetic',
        'tired': 'relaxed',
        'sleepy': 'relaxed',
        'scared': 'fearful',
        'afraid': 'fearful',
        'worried': 'fearful',
        'anxious': 'fearful',
        'mad': 'angry',
        'frustrated': 'angry',
        'annoyed': 'angry',
        'joyful': 'happy',
        'cheerful': 'happy',
        'glad': 'happy',
        'depressed': 'sad',
        'unhappy': 'sad',
        'down': 'sad',
        'amazed': 'surprised',
        'shocked': 'surprised',
        'astonished': 'surprised',
    }
    
    return alternatives.get(emotion_lower, 'calm')
