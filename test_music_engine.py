from music_engine import MusicEngine

"""
Usage:
  python test_music_engine.py

Requires muse_v3.csv in project root. Prints 3 example queries.
"""


def demo_query(v_min, v_max, a_min, a_max, label):
    engine = MusicEngine()
    if not engine.is_ready():
        print("Engine not ready. Ensure muse_v3.csv exists with required columns.")
        return
    df = engine.get_songs_in_va_range(v_min, v_max, a_min, a_max, num_songs=3)
    print(f"\n{label} -> {len(df)} results")
    if not df.empty:
        cols = [c for c in ["track", "artist", "valence", "arousal", "spotify_id"] if c in df.columns]
        print(df[cols].head())


def main():
    # Example: Angry (Low V, High A)
    demo_query(v_min=-0.8, v_max=-0.5, a_min=0.6, a_max=0.9, label="Angry-range")
    # Example: Sad (Low V, Low A)
    demo_query(v_min=-0.9, v_max=-0.4, a_min=-0.8, a_max=-0.3, label="Sad-range")
    # Example: Calm target (High V, Low A)
    demo_query(v_min=0.6, v_max=0.9, a_min=-0.9, a_max=-0.5, label="Calm-range")


if __name__ == "__main__":
    main()
