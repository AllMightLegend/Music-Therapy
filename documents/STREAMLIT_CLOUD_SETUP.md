# Streamlit Cloud Deployment Guide - Emotion Detection Setup

## Problem: Emotion Detection Not Working on Streamlit Cloud

Your app is deployed, but emotion detection shows "❌ Emotion detection is NOT available"

**Root Cause:** Streamlit Cloud doesn't automatically load `.env` files. You must configure secrets through the Cloud dashboard.

---

## Solution: Add Face++ Credentials via Streamlit Cloud Secrets

### Step 1: Go to Streamlit Cloud Dashboard
1. Open https://share.streamlit.io/
2. Find your **Music-Therapy** app in the list
3. Look for the **three dots** (...) menu in the top right, OR the **Settings** gear icon (⚙️)

### Step 2: Open App Settings
- Click the **Settings** option (you may need to expand the menu)
- A new window should open showing your app configuration

### Step 3: Access Secrets Manager
- Click **"Secrets"** in the left sidebar (should show a 🔑 icon)
- A text editor will appear for TOML configuration

### Step 4: Add Your Face++ Credentials
Copy and paste this into the Secrets editor:

```toml
FACEPP_API_KEY = "YOUR_FACEPP_API_KEY"
FACEPP_API_SECRET = "YOUR_FACEPP_API_SECRET"
```

Replace `YOUR_FACEPP_API_KEY` and `YOUR_FACEPP_API_SECRET` with your actual Face++ API credentials.

**Where to get Face++ credentials:**
1. Go to https://www.faceplusplus.com/
2. Sign up or log in to your account
3. Navigate to API Management
4. Find your API Key and API Secret
5. Copy them

### Step 5: Save & Deploy
1. Click **"Save"** in the Secrets panel
2. Streamlit will automatically redeploy your app with the new credentials
3. Wait 30 seconds for deployment to complete
4. Refresh your app in the browser

### Step 6: Verify
- Open your app
- Click the **"🔧 System Status"** expander
- You should see: **"✅ Emotion detection is AVAILABLE"**
- Select "Webcam" mode and test emotion detection!

---

## Troubleshooting

### Issue: Still showing "❌ Emotion detection is NOT available"

**Check 1: Verify Secrets Saved**
- Go back to Settings → Secrets
- Make sure your credentials are there and saved
- If empty, you need to add them again

**Check 2: App Redeployed**
- Give it 60 seconds after saving secrets
- Force refresh your browser (Ctrl+Shift+R or Cmd+Shift+R)
- Check the console logs (F12 → Console tab) for error messages

**Check 3: Credentials Format**
- Make sure you have BOTH API_KEY and API_SECRET
- No quotes needed in Streamlit secrets (TOML format)
- ✓ Correct: `FACEPP_API_KEY = "abc123"`
- ✗ Wrong: `FACEPP_API_KEY="abc123"` (extra quotes)

**Check 4: See Detailed Errors**
- Open the System Status expander
- Look for "Failed imports" section
- Copy any error messages and debug

---

## Alternative: Use Hume API (Optional)

If Face++ isn't working, you can use Hume API instead:

```toml
HUME_API_KEY = "YOUR_HUME_API_KEY"
USE_HUME = "1"
```

Get Hume API key from: https://www.hume.ai/

---

## Local Development (Windows)

If testing locally on your machine:
1. Your `.env` file is already loaded automatically
2. No need to use Streamlit Secrets
3. Emotion detection should work with your Face++ credentials from `.env`

---

## Support

If you're still having issues:
1. Check Streamlit Cloud app logs (Settings → Logs)
2. Open browser console (F12 → Console) for error messages
3. Make sure credentials are valid by testing them directly with Face++ API
4. Try the Manual Input mode as a fallback (no AI required)

