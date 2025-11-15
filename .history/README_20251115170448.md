# Music-Therapy

## Music Therapy Recommendation System (Streamlit)

A monolithic Streamlit app that detects mood (DeepFace), generates a therapeutic playlist using the Iso-Principle over Valence–Arousal space, and tracks session history with SQLite. Webcam or manual input supported; dashboard shows progress over time.

## Features
- Login / Select child profile (SQLite)
- Webcam or manual mood detection (DeepFace + streamlit-webrtc)
- Iso-Principle playlist generation using MuSe dataset (static CSV)
- Spotify embeds via `spotify_id` (no API auth required)
- Feedback capture and session history
- Progress Dashboard (charts + history)

## Quick Start
1. (Optional) Create and activate a virtual environment.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Download the MuSe dataset CSV (e.g., `muse_v3.csv`) into the project root.
4. Run the app:
   ```bash
   streamlit run app.py
   ```

If `muse_v3.csv` is missing, the app will still launch but show a warning and disable playlist generation.

## Dataset
- Expected file: `muse_v3.csv` in project root
- Required columns: `track`, `artist`, `valence_tags`, `arousal_tags`, `spotify_id`

## Primary Limitation
DeepFace is trained largely on adult faces and may underperform on children. Child-specific datasets like CAFE are not publicly usable for this project due to access and licensing restrictions.

## Advanced Enhancement (Optional)
Inject new music via Spotify Search (Client Credentials Flow) using the artist from a seed MuSe track. This avoids deprecated endpoints (`/recommendations`, `/audio-features`).

## Structure
- `app.py`: Streamlit app entry point
- `database.py`: SQLite utilities
- `music_engine.py`: MuSe loader, caching, V-A filtering
- `emotion_detector.py`: DeepFace wrapper
- `recommendation_logic.py`: Iso-Principle playlist generator
- `requirements.txt`, `.gitignore`

## Troubleshooting
- TensorFlow on Windows can be heavy; ensure compatible Python and build tools.
- Webcam needs browser permission; use Chrome/Edge.
