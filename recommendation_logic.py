from typing import Dict, Tuple, Optional, List, Set

import pandas as pd

from music_engine import MusicEngine


EMOTION_TO_VA: Dict[str, Tuple[float, float]] = {
    "happy": (0.8, 0.8),
    "sad": (-0.7, -0.6),
    "angry": (-0.6, 0.7),
    "fear": (-0.4, 0.8),
    "surprise": (0.1, 0.9),
    "disgust": (-0.7, 0.1),
    "neutral": (0.0, 0.0),
    "calm": (0.7, -0.7),
}


def get_va_coordinates(emotion: str) -> Tuple[float, float]:
    key = (emotion or "").strip().lower()
    if key not in EMOTION_TO_VA:
        return EMOTION_TO_VA["neutral"]
    return EMOTION_TO_VA[key]


def generate_playlist(
    music_engine: MusicEngine,
    start_emotion: str,
    target_emotion: str = "calm",
    num_steps: int = 5,
    tolerance: float = 0.1,
    random_state: Optional[int] = None,
) -> pd.DataFrame:
    if not music_engine.is_ready():
        return pd.DataFrame()

    v_start, a_start = get_va_coordinates(start_emotion)
    v_target, a_target = get_va_coordinates(target_emotion)

    if num_steps < 2:
        num_steps = 2

    v_step = (v_target - v_start) / (num_steps - 1)
    a_step = (a_target - a_start) / (num_steps - 1)

    selected_rows: List[pd.Series] = []
    used_ids: Set[str] = set()

    for i in range(num_steps):
        current_v = v_start + (i * v_step)
        current_a = a_start + (i * a_step)

        v_min, v_max = current_v - tolerance, current_v + tolerance
        a_min, a_max = current_a - tolerance, current_a + tolerance

        song_df = music_engine.get_songs_in_va_range(
            v_min,
            v_max,
            a_min,
            a_max,
            num_songs=1,
            exclude_spotify_ids=used_ids,
            random_state=random_state,
        )

        if not song_df.empty:
            row = song_df.iloc[0]
            selected_rows.append(row)
            used_ids.add(str(row.get("spotify_id")))
        else:
            widen = tolerance * 2
            song_df = music_engine.get_songs_in_va_range(
                current_v - widen,
                current_v + widen,
                current_a - widen,
                current_a + widen,
                num_songs=1,
                exclude_spotify_ids=used_ids,
                random_state=random_state,
            )
            if not song_df.empty:
                row = song_df.iloc[0]
                selected_rows.append(row)
                used_ids.add(str(row.get("spotify_id")))

    if not selected_rows:
        return pd.DataFrame()

    result = pd.DataFrame(selected_rows).reset_index(drop=True)
    keep_cols = [c for c in ["track", "artist", "spotify_id", "valence", "arousal"] if c in result.columns]
    return result[keep_cols]
