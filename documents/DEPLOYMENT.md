# Deployment Guide for Music Therapy App

## Streamlit Cloud Deployment (Recommended)

Streamlit Cloud is the easiest way to deploy your Streamlit app. Follow these steps:

### Prerequisites
1. Your code must be in a GitHub repository (✅ Already done!)
2. You need a [Streamlit Cloud account](https://share.streamlit.io/) (free)

### Step-by-Step Deployment

1. **Go to Streamlit Cloud**
   - Visit: https://share.streamlit.io/
   - Sign in with your GitHub account

2. **Deploy Your App**
   - Click "New app"
   - Select your repository: `AllMightLegend/Music-Therapy`
   - Set the main file path: `app.py`
   - Choose branch: `main`
   - Click "Deploy"

3. **Wait for Deployment**
   - Streamlit Cloud will install dependencies from `requirements.txt`
   - First deployment may take 5-10 minutes (especially with TensorFlow/DeepFace)
   - You'll see build logs in real-time

### Important Notes

⚠️ **Heavy Dependencies Warning:**
- DeepFace and TensorFlow are very large (~1-2GB download)
- First deployment may timeout - if it does, try again
- Consider using a `.streamlit/config.toml` to increase timeout (see below)

⚠️ **Webcam Functionality:**
- `streamlit-webrtc` webcam features **will NOT work** on Streamlit Cloud
- OpenCV requires system libraries (libGL.so.1) that aren't available in Streamlit Cloud's container
- **Emotion detection via webcam/snapshot will fail** - this is a known limitation
- **Solution**: Use **Manual Input** mode instead - it works perfectly and provides the same functionality

✅ **What Works:**
- Manual mood input ✅
- Snapshot-based mood detection ✅
- Playlist generation ✅
- Database functionality ✅
- Dashboard and charts ✅

### Optional: Create Config File

Create `.streamlit/config.toml` for better performance:

```toml
[server]
maxUploadSize = 200
maxMessageSize = 200

[browser]
gatherUsageStats = false
```

### Troubleshooting

**Issue: Build fails or times out**
- Solution: Try deploying again. TensorFlow installation can be slow.
- Alternative: Consider using lighter ML models if DeepFace is too heavy.

**Issue: `libGL.so.1: cannot open shared object file`**
- This is **expected** on Streamlit Cloud. OpenCV requires system libraries that aren't available.
- The app is designed to handle this gracefully - use **Manual Input** mode instead.
- Webcam/snapshot emotion detection won't work on Streamlit Cloud due to these limitations.

**Issue: Emotion detection model failed to load**
- This is related to the OpenCV/system library issue above.
- **Solution**: Use the **Manual Input** button - it provides the same playlist recommendations without requiring emotion detection.

**Issue: Webcam doesn't work**
- This is expected on Streamlit Cloud. The app will show clear error messages.
- **Use Manual Input mode** - it's fully functional and provides the same experience.

**Issue: App is slow**
- DeepFace model loading takes time on first use (if it loads at all)
- Manual input mode is instant and doesn't require ML models

## Alternative Deployment Options

### 1. Heroku
- More control but requires more setup
- Need `Procfile` and `runtime.txt`
- Better for production apps

### 2. AWS/Azure/GCP
- Full control and scalability
- Requires cloud account and more configuration
- Best for production with high traffic

### 3. Docker + Any Cloud Provider
- Package app in Docker container
- Deploy to any container platform
- Most flexible option

## Post-Deployment

After successful deployment:
1. Test all features (especially manual mood input)
2. Share your app URL with users
3. Monitor usage and performance
4. Update your README with the live app URL

