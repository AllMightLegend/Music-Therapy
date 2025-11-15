import os
from typing import Optional

import pandas as pd
import streamlit as st


@st.cache_data(show_spinner=False)
def load_music_data(csv_path: str = "muse_v3.csv") -> pd.DataFrame:
    if not os.path.exists(csv_path):
        # Return empty DataFrame with expected columns if file is missing
        return pd.DataFrame(
            columns=["track", "artist", "valence_tags", "arousal_tags", "spotify_id"]
        )
    df = pd.read_csv(csv_path)
    return df


def _coalesce_columns(df: pd.DataFrame, targets: dict) -> pd.DataFrame:
    """
    Map possibly varying source column names to desired target names if found.
    targets: {target_name: [possible_source_names...]}
    """
    rename_map = {}
    for target, candidates in targets.items():
        for cand in candidates:
            if cand in df.columns:
                rename_map[cand] = target
                break
    if rename_map:
        df = df.rename(columns=rename_map)
    return df


def _normalize_series_to_minus1_1(series: pd.Series) -> pd.Series:
    mn = pd.to_numeric(series, errors="coerce").min()
    mx = pd.to_numeric(series, errors="coerce").max()
    if pd.isna(mn) or pd.isna(mx) or mx == mn:
        return series
    # If already roughly within [-1.2, 1.2], keep as-is
    if mn >= -1.2 and mx <= 1.2:
        return series
    # If clearly in [0,1], map to [-1,1]
    if 0.0 <= mn <= 1.0 and 0.0 <= mx <= 1.0:
        return (series * 2.0) - 1.0
    # Generic min-max to [-1,1]
    return 2.0 * ((series - mn) / (mx - mn)) - 1.0


def preprocess_data(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    # Try to coalesce common MuSe variants
    df = _coalesce_columns(
        df,
        targets={
            "track": ["track", "title", "song", "name"],
            "artist": ["artist", "artists", "artist_name"],
            "valence_tags": ["valence_tags", "valence_tag", "valence"],
            "arousal_tags": ["arousal_tags", "arousal_tag", "arousal", "energy"],
            "spotify_id": ["spotify_id", "id", "spotify_uri", "uri"],
        },
    )

    # Rename valence/arousal tags to standardized names
    rename_map = {
        "valence_tags": "valence",
        "arousal_tags": "arousal",
    }
    df = df.rename(columns=rename_map)

    # Ensure numeric
    for col in ["valence", "arousal"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    # Drop invalid/missing essentials
    required = ["spotify_id", "valence", "arousal"]
    present_required = [c for c in required if c in df.columns]
    if present_required:
        df = df.dropna(subset=present_required)

    # Normalize valence/arousal to [-1,1] robustly
    if "valence" in df.columns:
        df["valence"] = _normalize_series_to_minus1_1(df["valence"])
    if "arousal" in df.columns:
        df["arousal"] = _normalize_series_to_minus1_1(df["arousal"])

    # Deduplicate by spotify_id to avoid repeats
    if "spotify_id" in df.columns:
        df = df.drop_duplicates(subset=["spotify_id"])  

    return df


class MusicEngine:
    def __init__(self, csv_path: str = "muse_v3.csv") -> None:
        raw = load_music_data(csv_path)
        self.df = preprocess_data(raw)

    def is_ready(self) -> bool:
        return (not self.df.empty) and all(
            c in self.df.columns for c in ["track", "artist", "valence", "arousal", "spotify_id"]
        )

    def get_songs_in_va_range(
        self,
        v_min: float,
        v_max: float,
        a_min: float,
        a_max: float,
        num_songs: int = 1,
        exclude_spotify_ids: Optional[set] = None,
        random_state: Optional[int] = None,
    ) -> pd.DataFrame:
        if self.df.empty or not all(c in self.df.columns for c in ["valence", "arousal"]):
            return pd.DataFrame()
        subset = self.df[
            (self.df["valence"] >= v_min)
            & (self.df["valence"] <= v_max)
            & (self.df["arousal"] >= a_min)
            & (self.df["arousal"] <= a_max)
        ]
        if exclude_spotify_ids and not subset.empty and "spotify_id" in subset.columns:
            subset = subset[~subset["spotify_id"].isin(exclude_spotify_ids)]
        if subset.empty:
            return pd.DataFrame()
        count = min(num_songs, len(subset))
        return subset.sample(n=count, random_state=random_state)
