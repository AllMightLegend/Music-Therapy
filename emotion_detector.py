"""
Emotion detection module using Hume AI REST API.

This module provides a simple interface to detect emotions from image frames
using Hume's cloud-based emotion detection API.
"""

import os
import time
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

# Flag to indicate if emotion detection is available
EMOTION_DETECTION_AVAILABLE = bool(HUME_API_KEY)

# Hume REST API endpoints
HUME_BATCH_JOBS_URL = "https://api.hume.ai/v0/batch/jobs"
HUME_POLL_TIMEOUT = 30  # seconds to wait for job completion



def analyze_frame(frame_data) -> Optional[str]:
    """
    Analyze an image frame and return the detected emotion.
    
    This function:
    1. Converts input frames to JPEG format
    2. Submits to Hume's batch processing API
    3. Polls for job completion
    4. Extracts dominant emotion from results
    
    Args:
        frame_data: Either a numpy array in BGR format or raw bytes
        
    Returns:
        The dominant emotion mapped to app mood category (happy, sad, angry, etc.)
        or None if emotion detection is unavailable or detection fails
    """
    if not EMOTION_DETECTION_AVAILABLE:
        return None
    
    try:
        import requests
        
        # Convert input to JPEG bytes
        frame_bytes = _convert_to_jpeg_bytes(frame_data)
        if frame_bytes is None:
            print("[emotion_detector] Failed to convert frame to JPEG")
            return None
        
        # Submit job to Hume API
        job_id = _submit_job(frame_bytes)
        if not job_id:
            print("[emotion_detector] Failed to submit job")
            return None
        
        print(f"[emotion_detector] Submitted job: {job_id}")
        
        # Poll for completion
        predictions = _poll_for_predictions(job_id)
        if not predictions:
            print("[emotion_detector] Failed to get predictions")
            return None
        
        # Extract emotion from predictions
        emotion = _extract_emotion_from_predictions(predictions)
        print(f"[emotion_detector] Final result: {emotion}")
        return emotion
        
    except Exception as e:
        print(f"[emotion_detector] Error in emotion detection: {e}")
        import traceback
        traceback.print_exc()
        return None


def _submit_job(frame_bytes: bytes) -> Optional[str]:
    """
    Submit an image to Hume batch jobs API.
    
    Args:
        frame_bytes: JPEG image bytes
        
    Returns:
        Job ID or None if submission fails
    """
    try:
        import requests
        
        response = requests.post(
            HUME_BATCH_JOBS_URL,
            headers={"X-Hume-Api-Key": HUME_API_KEY},
            files={"file": ("frame.jpg", frame_bytes, "image/jpeg")},
            json={"models": {"face": {}}},
            timeout=10
        )
        
        if response.status_code not in [200, 202]:
            print(f"[emotion_detector] Job submission failed: {response.status_code}")
            return None
        
        data = response.json()
        job_id = data.get("job_id")
        if job_id:
            print(f"[emotion_detector] Job ID: {job_id}")
        return job_id
        
    except Exception as e:
        print(f"[emotion_detector] Error submitting job: {e}")
        return None


def _poll_for_predictions(job_id: str) -> Optional[list]:
    """
    Poll the Hume API until job completes and fetch predictions.
    Jobs typically complete within 100-500ms.
    
    Args:
        job_id: The job ID returned from submission
        
    Returns:
        List of predictions or None if polling fails
    """
    try:
        import requests
        
        headers = {"X-Hume-Api-Key": HUME_API_KEY}
        predictions_url = f"{HUME_BATCH_JOBS_URL}/{job_id}/predictions"
        
        start_time = time.time()
        poll_wait = 0.01  # Start with 10ms
        max_wait = 0.5    # Cap at 500ms
        attempts = 0
        
        while time.time() - start_time < HUME_POLL_TIMEOUT:
            attempts += 1
            try:
                # Get predictions
                response = requests.get(predictions_url, headers=headers, timeout=10)
                
                if response.status_code == 200:
                    # Got predictions successfully
                    print(f"[emotion_detector] Got predictions after {attempts} attempts ({time.time()-start_time:.2f}s)")
                    return response.json()
                elif response.status_code == 202:
                    # Still processing, wait with exponential backoff
                    time.sleep(poll_wait)
                    poll_wait = min(poll_wait * 2.0, max_wait)
                    continue
                else:
                    # Unexpected status code
                    print(f"[emotion_detector] Unexpected status {response.status_code}, retrying...")
                    time.sleep(poll_wait)
                    poll_wait = min(poll_wait * 2.0, max_wait)
                    continue
            except requests.exceptions.Timeout:
                print(f"[emotion_detector] Request timeout on attempt {attempts}, retrying...")
                time.sleep(poll_wait)
                poll_wait = min(poll_wait * 2.0, max_wait)
                continue
        
        print(f"[emotion_detector] Polling timeout after {attempts} attempts")
        return None
        
    except Exception as e:
        print(f"[emotion_detector] Error polling for predictions: {e}")
        import traceback
        traceback.print_exc()
        return None




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
    
    # Angry moods: Anger, Contempt, Envy
    angry_emotions = {
        "anger", "contempt", "envy"
    }
    
    # Fearful moods: Fear, Horror, Panic
    fearful_emotions = {
        "fear", "horror", "dread", "panic"
    }
    
    # Surprised moods: Surprise (positive and negative), Awe, Wonder
    surprised_emotions = {
        "surprise", "surprise (positive)", "surprise (negative)", 
        "awe", "wonder", "amazement"
    }
    
    # Loving/Affectionate moods: Love, Adoration, Admiration, Romance
    loving_emotions = {
        "love", "adoration", "admiration", "affection", "romance", 
        "aesthetic appreciation"
    }
    
    # Energized/Excited moods: Excitement, Interest, Desire, Craving, Determination
    energized_emotions = {
        "excitement", "interest", "desire", "craving", "determination",
        "entrancement"
    }
    
    # Anxious/Worried moods: Anxiety, Doubt, Confusion, Awkwardness
    anxious_emotions = {
        "anxiety", "doubt", "worry", "confusion", "awkwardness", 
        "distress", "concern"
    }
    
    # Calm/Peaceful moods: Calmness, Contemplation, Realization
    calm_emotions = {
        "calmness", "contemplation", "realization", "acceptance",
        "contentment"
    }
    
    # Focused/Concentrated moods: Concentration, Attention, Focus
    focused_emotions = {
        "concentration", "focus", "attention", "diligence"
    }
    
    if emotion_lower in happy_emotions:
        return "happy"
    elif emotion_lower in sad_emotions:
        return "sad"
    elif emotion_lower in angry_emotions:
        return "angry"
    elif emotion_lower in fearful_emotions:
        return "fearful"
    elif emotion_lower in surprised_emotions:
        return "surprised"
    elif emotion_lower in loving_emotions:
        return "loving"
    elif emotion_lower in energized_emotions:
        return "energized"
    elif emotion_lower in anxious_emotions:
        return "anxious"
    elif emotion_lower in focused_emotions:
        return "focused"
    elif emotion_lower in calm_emotions:
        return "calm"
    else:
        # Default to calm for unknown emotions
        return "calm"

