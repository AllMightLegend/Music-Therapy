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
- `streamlit-webrtc` webcam features may have limited functionality on Streamlit Cloud
- The app will fall back to snapshot mode if real-time streaming isn't available
- This is normal and expected

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

**Issue: Webcam doesn't work**
- This is expected on Streamlit Cloud. Use the snapshot feature instead.

**Issue: App is slow**
- DeepFace model loading takes time on first use
- Subsequent uses will be faster due to caching

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

