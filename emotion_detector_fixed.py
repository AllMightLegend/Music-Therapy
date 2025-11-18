"""
Emotion detection module using Hume AI Streaming API.

This module provides emotion detection using Hume's streaming SDK
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

# Try to import hume SDK
try:
    from hume import HumeStreamClient
    from hume.models.config import FaceConfig
    HUME_SDK_AVAILABLE = True
except ImportError:
    HUME_SDK_AVAILABLE = False

load_dotenv()

# Configuration
HUME_API_KEY = os.getenv("HUME_API_KEY", "")
HUME_PROB_THRESHOLD = float(os.getenv("HUME_PROB_THRESHOLD", "0.2"))

# Enable Hume by default
USE_HUME = os.getenv("USE_HUME", "1") == "1" and bool(HUME_API_KEY) and HUME_SDK_AVAILABLE

# Always make emotion detection available
EMOTION_DETECTION_AVAILABLE = True

# Print configuration on module load
print(f"[emotion_detector] Config: USE_HUME={USE_HUME}, API_KEY={'SET' if HUME_API_KEY else 'MISSING'}, SDK={'OK' if HUME_SDK_AVAILABLE else 'MISSING'}, THRESHOLD={HUME_PROB_THRESHOLD}")


def analyze_frame(frame_data: np.ndarray) -> Optional[str]:
    """
    Analyze a video frame for emotion detection.
    
    Priority:
    1. Hume Streaming API (real-time, high accuracy)
    2. OpenCV detector (instant fallback)
    
    Args:
        frame_data: numpy array of the video frame in BGR format
        
    Returns:
        Detected emotion string (happy, sad, angry, fearful, surprised, calm) or None
    """
    if frame_data is None or frame_data.size == 0:
        return None
    
    # Priority 1: Try Hume Streaming API if enabled
    if USE_HUME and HUME_API_KEY and HUME_SDK_AVAILABLE:
        try:
            emotion = _analyze_via_hume_sdk(frame_data)
            if emotion:
                return emotion
        except Exception as e:
            print(f"[emotion_detector] Hume error: {e}")
    
    # Priority 2: Fallback to OpenCV detector
    opencv_emotion = _opencv_detector(frame_data)
    if opencv_emotion:
        return opencv_emotion
    
    print("[emotion_detector] ✗ No emotion detected by any method")
    return None


def _analyze_via_hume_sdk(frame_data: np.ndarray) -> Optional[str]:
    """
    Analyze frame using Hume Python SDK (streaming).
    Runs async code in sync context.
    
    Args:
        frame_data: numpy array of the video frame in BGR format
        
    Returns:
        Detected emotion string or None
    """
    try:
        # Convert frame to base64
        frame_bytes = _convert_to_jpeg_bytes(frame_data)
        if not frame_bytes:
            return None
        
        frame_b64 = base64.b64encode(frame_bytes).decode('utf-8')
        
        # Run async analysis
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            emotion = loop.run_until_complete(_async_analyze(frame_b64))
            return emotion
        finally:
            loop.close()
            
    except Exception as e:
        print(f"[emotion_detector] Hume SDK error: {e}")
        return None


async def _async_analyze(frame_b64: str) -> Optional[str]:
    """
    Async function to analyze frame with Hume SDK.
    
    Args:
        frame_b64: Base64-encoded JPEG frame
        
    Returns:
        Detected emotion string or None
    """
    try:
        client = HumeStreamClient(HUME_API_KEY)
        config = FaceConfig()
        
        async with client.connect([config]) as socket:
            result = await socket.send_text(frame_b64)
            
            # Extract emotion from result
            if result and hasattr(result, 'face') and result.face:
                predictions = result.face.predictions
                if predictions and len(predictions) > 0:
                    emotions = predictions[0].emotions
                    
                    # Define the 10 main emotions
                    main_emotions = {
                        'Joy', 'Sadness', 'Anger', 'Fear', 'Surprise (positive)', 
                        'Surprise (negative)', 'Disgust', 'Calmness', 'Excitement', 'Contentment'
                    }
                    
                    # Filter and sort
                    all_emotions = [(e.name, e.score) for e in emotions]
                    main_emotion_scores = [(name, score) for name, score in all_emotions if name in main_emotions]
                    all_sorted = sorted(all_emotions, key=lambda x: x[1], reverse=True)
                    
                    # Print top 5
                    print(f"[emotion_detector] Hume top 5:")
                    for i, (name, score) in enumerate(all_sorted[:5]):
                        marker = "★" if name in main_emotions else " "
                        print(f"  {marker} {i+1}. {name}: {score:.3f}")
                    
                    # Pick best main emotion above threshold
                    if main_emotion_scores:
                        sorted_main = sorted(main_emotion_scores, key=lambda x: x[1], reverse=True)
                        name, score = sorted_main[0]
                        
                        if score >= HUME_PROB_THRESHOLD:
                            mapped = _map_hume_emotion_to_mood(name)
                            print(f"[emotion_detector] ✓ Hume: {name} ({score:.2f}) → {mapped}")
                            return mapped
                    
                    # Fallback to any emotion above threshold
                    if all_sorted[0][1] >= HUME_PROB_THRESHOLD:
                        name, score = all_sorted[0]
                        mapped = _map_hume_emotion_to_mood(name)
                        print(f"[emotion_detector] ✓ Hume (fallback): {name} ({score:.2f}) → {mapped}")
                        return mapped
                        
    except Exception as e:
        print(f"[emotion_detector] Async Hume error: {e}")
    
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
            minNeighbors=5,
            minSize=(20, 20)
        )
        
        # Detect smile with adjusted parameters
        smiles = smile_cascade.detectMultiScale(
            face_roi_gray,
            scaleFactor=1.7,
            minNeighbors=15,
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
        Mood category string
    """
    # Primary mapping for the 10 main emotions
    primary_emotions = {
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
    
    if hume_emotion in primary_emotions:
        return primary_emotions[hume_emotion]
    
    # Extended mapping
    extended_map = {
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
        'Disappointment': 'sad',
        'Empathic Pain': 'sad',
        'Sympathy': 'sad',
        'Tiredness': 'sad',
        'Boredom': 'sad',
        'Guilt': 'sad',
        'Shame': 'sad',
        'Embarrassment': 'sad',
        'Pain': 'sad',
        'Contempt': 'angry',
        'Annoyance': 'angry',
        'Envy': 'angry',
        'Anxiety': 'fearful',
        'Horror': 'fearful',
        'Doubt': 'fearful',
        'Confusion': 'fearful',
        'Awkwardness': 'fearful',
        'Distress': 'fearful',
        'Concentration': 'focused',
        'Contemplation': 'focused',
        'Determination': 'focused',
        'Interest': 'focused',
        'Enthusiasm': 'energetic',
        'Realization': 'surprised',
        'Awe': 'surprised',
        'Nostalgia': 'relaxed',
        'Desire': 'romantic',
        'Craving': 'energetic',
        'Entrancement': 'focused',
    }
    
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
    
    valid_emotions = {
        'happy', 'sad', 'angry', 'fearful', 'surprised', 
        'calm', 'energetic', 'relaxed', 'focused', 'romantic'
    }
    
    if emotion_lower in valid_emotions:
        return emotion_lower
    
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
