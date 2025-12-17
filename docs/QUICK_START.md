# Quick Reference - Hume AI Setup

## 1️⃣ Get Your API Key (2 minutes)

```bash
# Step 1: Go to https://platform.hume.ai/settings/keys
# Step 2: Sign up if needed
# Step 3: Create a new API key
# Step 4: Copy it (won't be shown again!)
```

## 2️⃣ Configure Your Project (1 minute)

**Option A: Using setup script (Recommended)**
```bash
# Linux/Mac
bash setup.sh

# Windows
setup.bat
```

**Option B: Manual setup**
```bash
# 1. Copy template
cp .env.example .env

# 2. Edit .env and paste your API key
# HUME_API_KEY=your_actual_key_here

# 3. Create venv (optional but recommended)
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate     # Windows

# 4. Install dependencies
pip install -r requirements.txt
```

## 3️⃣ Run the App (1 minute)

```bash
streamlit run app.py
```

Opens at: `http://localhost:8501`

## 4️⃣ Test Emotion Detection

1. Click **Webcam** mode
2. Click **Capture snapshot**
3. Wait 1-2 seconds for Hume API response
4. See detected emotion displayed

## ✅ If It Works
Great! You're all set. The app will now use Hume AI for emotion detection.

## ❌ If It Doesn't Work

### Issue: "HUME_API_KEY not found"
**Solution**: Make sure `.env` exists with your key:
```bash
cat .env
# Should show: HUME_API_KEY=your_actual_key
```

### Issue: "No module named 'hume'"
**Solution**: Install dependencies:
```bash
pip install -r requirements.txt
```

### Issue: Emotion detection returns None
**Solution**: Check these:
1. Is your API key valid? (Test in Hume dashboard)
2. Is internet working? (ping google.com)
3. Are you within rate limits? (Check Hume settings)

### Issue: "Connection refused"
**Solution**: 
- Check internet connection
- Verify API key is correct
- Check https://status.hume.ai for outages

## 📚 For More Help

- **Full setup guide**: See `HUME_MIGRATION.md`
- **Integration details**: See `INTEGRATION_SUMMARY.md`
- **Troubleshooting**: See `HUME_MIGRATION.md` → Troubleshooting section
- **Hume docs**: https://dev.hume.ai/

## 💡 Pro Tips

1. **Testing without API calls**: Use manual mood input
2. **Faster setup**: Run `setup.sh` or `setup.bat`
3. **Troubleshooting**: Check app console for error messages
4. **Deployment**: See HUME_MIGRATION.md for cloud deployment guides

## 🚀 Ready?

```bash
streamlit run app.py
```

That's it! 🎉

---

**Need an API key?** → https://platform.hume.ai/settings/keys
**Stuck?** → See HUME_MIGRATION.md or https://dev.hume.ai/
