# Hume AI Integration for Emotion Detection

This document describes the migration from DeepFace to Hume AI for emotion detection in the Music Therapy Recommender system.

## What Changed

### Removed Dependencies
- **DeepFace** - Local facial emotion detection using deep neural networks
- **TensorFlow** and **tf-keras** - Heavy ML dependencies
- These required significant system resources and could fail on headless environments (like Streamlit Cloud)

### New Dependencies
- **Hume SDK** (`hume[microphone]`) - Lightweight API client for Hume's facial expression recognition
- **python-dotenv** - Environment variable management for API keys

### Why Hume AI?

1. **Better Performance on Diverse Faces**: Hume's models are trained on diverse populations and perform well across age groups
2. **No Local Model Downloads**: All processing happens via API (no 4GB+ model files)
3. **Robust Implementation**: Better handles various lighting, angles, and partial faces
4. **Scalability**: Doesn't require GPU/high-spec hardware
5. **Maintenance-Free**: Updates to emotion models happen server-side

## Setup Instructions

### 1. Get a Hume API Key

1. Go to [Hume AI Platform](https://platform.hume.ai/settings/keys)
2. Sign up or log in with your account
3. Navigate to **Settings → API Keys**
4. Create a new API key (copy it immediately, as it won't be shown again)

### 2. Configure Your Environment

Create a `.env` file in the project root:

```bash
cp .env.example .env
```

Then edit `.env` and add your API key:

```env
HUME_API_KEY=your_actual_api_key_here
```

**Important**: Do NOT commit the `.env` file to version control. It's already in `.gitignore`.

### 3. Install Updated Dependencies

```bash
pip install -r requirements.txt
```

This will install:
- The Hume Python SDK
- python-dotenv for configuration
- All existing dependencies (streamlit, opencv, etc.)

### 4. Run the App

```bash
streamlit run app.py
```

The app will automatically load your API key from the `.env` file and use Hume for emotion detection.

## How It Works

### Emotion Detection Flow

1. **User captures image** via webcam or snapshot
2. **Image is converted to JPEG bytes** in memory (no file I/O required)
3. **Bytes sent to Hume API** at `https://api.hume.ai/v0/`
4. **Hume returns emotion predictions** with confidence scores
5. **Emotions mapped** to app mood categories:
   - `joy` → `happy`
   - `sadness` → `sad`
   - `anger` → `angry`
   - `fear` → `fear`
   - `surprise` → `surprise`
   - `disgust` → `disgust`
   - `contempt` → `angry`
   - `neutral` → `neutral`

### Emotion Detection Code

The emotion detection logic is in `emotion_detector.py`:

```python
def analyze_frame(frame_data) -> Optional[str]:
    """
    Synchronous wrapper for Hume API calls.
    - Accepts numpy BGR arrays or raw bytes
    - Converts to JPEG format
    - Calls Hume's expression API
    - Returns dominant emotion or None
    """
```

## Deployment

### Local Deployment
Simply set the `HUME_API_KEY` environment variable before running:

```bash
export HUME_API_KEY=your_key_here  # Linux/Mac
set HUME_API_KEY=your_key_here     # Windows CMD
```

### Streamlit Cloud Deployment

1. Fork/push your project to GitHub (with `.env` in `.gitignore`)
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your GitHub repo
4. In the **Secrets** section, add:
   ```
   HUME_API_KEY = your_actual_api_key
   ```
5. Streamlit will inject this as an environment variable

### Docker Deployment

Add to your Dockerfile or docker-compose:

```dockerfile
ENV HUME_API_KEY=your_key_here
```

Or pass at runtime:

```bash
docker run -e HUME_API_KEY=your_key_here your_app
```

## Troubleshooting

### "HUME_API_KEY not found in environment variables"

**Solution**: Create a `.env` file in the project root with your API key:

```env
HUME_API_KEY=your_actual_key_here
```

### "No module named 'hume'"

**Solution**: Install the Hume SDK:

```bash
pip install 'hume[microphone]>=0.7.0'
```

### "Connection refused" or "API request failed"

**Possible causes**:
- Invalid API key - verify in [Hume Platform](https://platform.hume.ai/settings/keys)
- Network connectivity issue - check your internet connection
- API rate limiting - your account may have usage limits; check your plan

**Solution**: 
1. Verify your API key is correct
2. Check your internet connection
3. Contact Hume support if you've exceeded rate limits

### Emotion detection not working on Streamlit Cloud

**Cause**: You likely forgot to add the secret in Streamlit Cloud's **Settings → Secrets**.

**Solution**:
1. Go to your app's settings on share.streamlit.io
2. Click **Secrets**
3. Add: `HUME_API_KEY = your_key_here`
4. Redeploy

## API Costs

Hume AI offers:
- **Free tier**: Limited requests for testing
- **Pay-as-you-go**: $0.05 per image for expression measurement
- **Pro plans**: Higher quotas and lower per-request costs

For details, see [Hume Pricing](https://www.hume.ai/pricing).

## Performance Comparison

| Aspect | DeepFace | Hume AI |
|--------|----------|---------|
| Accuracy on children | Poor | Excellent |
| Setup complexity | High (models, CUDA) | Low (API key) |
| System requirements | GPU recommended | Internet connection |
| Latency | 200-500ms | 500-1000ms |
| Deployment on Cloud | Difficult | Easy |
| Cost | Free but heavy | Paid API |
| Model updates | Manual | Automatic |

## Reverting to DeepFace

If you need to revert to DeepFace:

1. Restore the original `emotion_detector.py` from git history
2. Update `requirements.txt` to include:
   ```
   deepface>=0.0.79
   tensorflow>=2.13.0
   tf-keras>=2.13.0
   ```
3. Remove the `.env` and related code from `app.py`
4. Reinstall: `pip install -r requirements.txt`

## Support

For issues with:
- **Hume SDK**: See [Hume Documentation](https://dev.hume.ai/)
- **Music Therapy App**: Check the main README.md

---

**Last Updated**: November 2025
