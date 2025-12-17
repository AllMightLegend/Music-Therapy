# Hume REST API Emotion Detection Setup

## What Changed

I've replaced DeepFace with **Hume AI's REST API** for high-quality emotion detection:

### Benefits:
- ✅ **48 granular emotions** from Hume (vs 7 from DeepFace)
- ✅ **Higher accuracy** - trained on millions of faces
- ✅ **Better real-world performance** - works in various lighting conditions
- ✅ **Reliable detection** - no more "neutral/calm" for everything
- ✅ **Cleaner dependencies** - removed heavy TensorFlow/DeepFace packages

### Detection Priority:
1. **Hume REST API** (primary) - High accuracy, ~1-2 second delay for processing
2. **OpenCV** (fallback) - Instant results when Hume is slow/unavailable

## Configuration

### Enable Hume API

Set these in your `.env` file:

```env
# Your Hume API key (required)
HUME_API_KEY=your_api_key_here

# Enable Hume (1=enabled, 0=disabled) - default is 1
USE_HUME=1

# Emotion confidence threshold (0.0-1.0) - default is 0.3
HUME_PROB_THRESHOLD=0.3
```

### Get Your API Key

1. Go to https://platform.hume.ai/
2. Sign up or log in
3. Navigate to API Keys section
4. Create a new API key
5. Copy it to your `.env` file

## How It Works

### Hume REST API Process:
1. App captures video frame from webcam
2. Frame is converted to JPEG and sent to Hume API
3. Hume creates a batch job and processes the image
4. App polls for completion (max 5 seconds, checks every 500ms)
5. When complete, Hume returns 48 emotion scores
6. Top 3 emotions are analyzed and mapped to app's mood system
7. Emotion displayed to user and used for music recommendations

### Emotion Mapping:
Hume's 48 emotions → Our 6 core emotions:
- **Happy**: Joy, Amusement, Excitement, Contentment, Satisfaction, etc.
- **Sad**: Sadness, Disappointment, Empathic Pain, Tiredness, etc.
- **Angry**: Anger, Disgust, Contempt, Annoyance, Distress, etc.
- **Fearful**: Fear, Anxiety, Horror, Confusion, Doubt, etc.
- **Surprised**: Surprise (positive/negative), Realization, Awe, etc.
- **Calm**: Calmness, Concentration, Contemplation, etc.

## Testing

Open the app at http://localhost:8501 and:

1. **Login** and navigate to emotion detection page
2. **Allow webcam** access
3. **Try different expressions**:
   - 😊 Smile → should detect "Joy" or "Amusement" → happy
   - 😢 Sad face → should detect "Sadness" → sad
   - 😠 Frown/scowl → should detect "Anger" or "Disgust" → angry
   - 😨 Wide eyes + open mouth → should detect "Fear" or "Horror" → fearful
   - 😮 Eyebrows up, eyes wide → should detect "Surprise" → surprised
   - 😐 Neutral face → should detect "Calmness" → calm

4. **Check terminal output** for debug info:
   ```
   [emotion_detector] Hume top 3:
     1. Joy: 0.812
     2. Amusement: 0.634
     3. Contentment: 0.521
   [emotion_detector] Hume: Joy (0.81) → happy
   ```

## Troubleshooting

### "No emotion detected"
- **Check API key**: Make sure `HUME_API_KEY` is set in `.env`
- **Check internet**: Hume API requires internet connection
- **Lower threshold**: Try `HUME_PROB_THRESHOLD=0.2` in `.env`
- **Fallback works**: OpenCV will still provide basic detection

### "Hume API timeout"
- Hume batch jobs can take 1-5 seconds
- OpenCV fallback will activate automatically
- Consider your internet speed

### "Still detecting calm for everything"
- If using OpenCV fallback, it only detects: happy, sad, surprised, calm
- Make sure Hume is enabled: `USE_HUME=1`
- Check terminal for `[emotion_detector] ✓ Hume detected:` messages

## Performance Notes

- **Hume API delay**: ~1-2 seconds per frame (batch processing)
- **Frame interval**: App analyzes 1 frame per second
- **Majority voting**: Uses last 5 detections to smooth results
- **Fallback**: OpenCV provides instant results if Hume is slow

## Cost Considerations

- Hume API has usage limits based on your plan
- Free tier: Check https://platform.hume.ai/pricing
- Each frame = 1 API call
- With 1 frame/second, that's ~60 calls/minute during active use

## Deployment to Streamlit Cloud

The app will work on Streamlit Cloud with these secrets set:

```toml
# .streamlit/secrets.toml
HUME_API_KEY = "your_api_key_here"
USE_HUME = "1"
HUME_PROB_THRESHOLD = "0.3"
```

Add to your Streamlit Cloud app settings → Secrets.
