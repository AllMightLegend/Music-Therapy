import pandas as pd

from music_engine import MusicEngine
from recommendation_logic import generate_playlist

"""
Usage:
  python test_logic.py

Requires muse_v3.csv. Prints the 5-step playlist from 'angry' to 'calm' and
checks whether valence increases and arousal decreases step-by-step.
"""


def is_monotonic_increasing(series: pd.Series) -> bool:
    diffs = series.diff().fillna(0)
    return (diffs >= -1e-9).all()


def is_monotonic_decreasing(series: pd.Series) -> bool:
    diffs = series.diff().fillna(0)
    return (diffs <= 1e-9).all()


def main() -> None:
    engine = MusicEngine()
    if not engine.is_ready():
        print("Engine not ready. Ensure muse_v3.csv exists with required columns.")
        return

    playlist = generate_playlist(
        music_engine=engine,
        start_emotion="angry",
        target_emotion="calm",
        num_steps=5,
        tolerance=0.12,
    )

    if playlist.empty:
        print("No playlist generated. Try adjusting tolerance or verify the dataset.")
        return

    cols = [c for c in ["track", "artist", "valence", "arousal", "spotify_id"] if c in playlist.columns]
    print(playlist[cols])

    if {"valence", "arousal"}.issubset(set(playlist.columns)):
        v_inc = is_monotonic_increasing(playlist["valence"])
        a_dec = is_monotonic_decreasing(playlist["arousal"])
        print(f"Valence increasing: {v_inc}")
        print(f"Arousal decreasing: {a_dec}")


if __name__ == "__main__":
    main()
