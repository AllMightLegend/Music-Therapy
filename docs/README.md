# Music-Therapy

## Music Therapy Recommendation System (Streamlit)

A monolithic Streamlit app that detects mood (Hume AI), generates a therapeutic playlist using the Iso-Principle over Valence–Arousal space, and tracks session history with SQLite. Webcam or manual input supported; dashboard shows progress over time.

## Features
- Login / Select child profile (SQLite)
- Webcam or manual mood detection (Hume AI Expression API + streamlit-webrtc)
- Iso-Principle playlist generation using MuSe dataset (static CSV)
- Spotify embeds via `spotify_id` (no API auth required)
- Feedback capture and session history
- Progress Dashboard (charts + history)

## Quick Start

### Prerequisites
- Python 3.8+
- A [Hume AI API key](https://platform.hume.ai/settings/keys)

### Setup
1. Clone or download this repository
2. (Optional) Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```
3. Copy the example environment file and add your Hume API key:
   ```bash
   cp .env.example .env
   # Edit .env and replace with your actual HUME_API_KEY
   ```
4. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
5. Download the MuSe dataset CSV (e.g., `muse_v3.csv`) into the project root
6. Run the app:
   ```bash
   streamlit run app.py
   ```

The app will be available at `http://localhost:8501`

**Note**: For detailed Hume setup instructions, see [HUME_MIGRATION.md](./HUME_MIGRATION.md).

## Dataset
- Expected file: `muse_v3.csv` in project root
- Required columns: `track`, `artist`, `valence_tags`, `arousal_tags`, `spotify_id`

## Why Hume AI Instead of DeepFace?

Hume AI provides:
- **Better accuracy on diverse faces** including children
- **No heavy model downloads** (all processing via API)
- **Headless/cloud-friendly** deployment
- **Automatic model updates** server-side
- **Robust handling** of various lighting and angles

See [HUME_MIGRATION.md](./HUME_MIGRATION.md) for the full comparison and migration details.

## Advanced Enhancement (Optional)
Inject new music via Spotify Search (Client Credentials Flow) using the artist from a seed MuSe track. This avoids deprecated endpoints (`/recommendations`, `/audio-features`).

## Structure
- `app.py`: Streamlit app entry point
- `database.py`: SQLite utilities
- `music_engine.py`: MuSe loader, caching, V-A filtering
- `emotion_detector.py`: Hume AI wrapper
- `recommendation_logic.py`: Iso-Principle playlist generator
- `requirements.txt`, `.gitignore`
- `HUME_MIGRATION.md`: Detailed setup and troubleshooting guide
- `.env.example`: Template for environment variables

## Troubleshooting

### Emotion detection not working?
- Check that you have a valid `HUME_API_KEY` in your `.env` file
- See [HUME_MIGRATION.md](./HUME_MIGRATION.md) for detailed troubleshooting

### Other issues?
- Webcam needs browser permission; use Chrome/Edge
- If `muse_v3.csv` is missing, app will still launch but playlist generation will be disabled
- Check logs for specific error messages

## Support & Resources
- **Hume AI Setup**: [HUME_MIGRATION.md](./HUME_MIGRATION.md)
- **Hume Documentation**: https://dev.hume.ai/
- **Streamlit Docs**: https://docs.streamlit.io/

