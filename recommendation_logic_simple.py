from typing import Dict, Tuple, Optional, List, Set

import pandas as pd

from music_engine import MusicEngine


EMOTION_TO_VA: Dict[str, Tuple[float, float]] = {
    "happy": (0.8, 0.8),
    "sad": (-0.7, -0.6),
    "angry": (-0.6, 0.7),
    "fear": (-0.4, 0.8),
    "fearful": (-0.4, 0.8),  # Alias for fear
    "surprise": (0.1, 0.9),
    "surprised": (0.1, 0.9),  # Alias for surprise
    "disgust": (-0.7, 0.1),
    "neutral": (0.0, 0.0),
    "calm": (0.7, -0.7),
    "anxious": (-0.3, 0.6),
    "focused": (0.3, 0.2),
    "energized": (0.6, 0.8),
    "relaxed": (0.5, -0.6),
    "loving": (0.7, 0.3),
}

# ISO Principle: Emotion transition graph
# Defines which emotions can be reached from a given emotion in one step
# Based on psychological transitions - gradual movement through emotional space
EMOTION_TRANSITIONS: Dict[str, List[str]] = {
    "sad": ["neutral", "calm", "relaxed"],
    "angry": ["anxious", "neutral", "focused"],
    "fearful": ["anxious", "neutral", "calm"],
    "fear": ["anxious", "neutral", "calm"],
    "anxious": ["neutral", "calm", "focused"],
    "surprised": ["neutral", "happy", "curious"],
    "surprise": ["neutral", "happy"],
    "neutral": ["calm", "focused", "happy", "relaxed"],
    "calm": ["relaxed", "focused", "happy"],
    "relaxed": ["calm", "happy", "focused"],
    "focused": ["calm", "energized", "happy"],
    "energized": ["happy", "focused", "excited"],
    "happy": ["energized", "loving", "calm"],
    "loving": ["happy", "calm", "relaxed"],
}


def get_va_coordinates(emotion: str) -> Tuple[float, float]:
    """Get valence-arousal coordinates for an emotion."""
    key = (emotion or "").strip().lower()
    if key not in EMOTION_TO_VA:
        return EMOTION_TO_VA["neutral"]
    return EMOTION_TO_VA[key]


def find_emotion_path(start: str, target: str) -> List[str]:
    """
    Find the shortest emotional transition path from start to target emotion.
    Uses BFS to find the most natural emotional progression based on ISO principle.
    
    Args:
        start: Starting emotion
        target: Target emotion
        
    Returns:
        List of emotions representing the path (including start and target)
    """
    start = start.lower().strip()
    target = target.lower().strip()
    
    # If start and target are the same, return single emotion
    if start == target:
        return [start]
    
    # BFS to find shortest path
    from collections import deque
    
    queue = deque([(start, [start])])
    visited = {start}
    
    while queue:
        current, path = queue.popleft()
        
        # Get possible next emotions
        next_emotions = EMOTION_TRANSITIONS.get(current, [])
        
        for next_emotion in next_emotions:
            if next_emotion == target:
                # Found the target!
                return path + [target]
            
            if next_emotion not in visited:
                visited.add(next_emotion)
                queue.append((next_emotion, path + [next_emotion]))
    
    # If no path found, create a direct path through neutral
    # This is a fallback for emotions not in the transition graph
    if start != "neutral" and target != "neutral":
        return [start, "neutral", target]
    else:
        return [start, target]


def generate_playlist(
    music_engine: MusicEngine,
    start_emotion: str,
    target_emotion: str = "calm",
    num_steps: int = 5,
    tolerance: float = 0.1,
    random_state: Optional[int] = None,
) -> pd.DataFrame:
    """
    Generate a therapeutic music playlist using the ISO principle.
    
    The ISO principle (Isochronic Principle) suggests that music therapy should start
    with music matching the current emotional state and gradually transition to the
    desired emotional state through intermediate steps.
    
    Args:
        music_engine: MusicEngine instance
        start_emotion: Current emotional state
        target_emotion: Desired emotional state
        num_steps: Number of songs in the playlist
        tolerance: Tolerance for valence/arousal matching
        random_state: Random seed for reproducibility
        
    Returns:
        DataFrame with playlist songs or empty DataFrame if generation fails
    """
    if not music_engine.is_ready():
        return pd.DataFrame()
    
    # Normalize emotions
    start_emotion = start_emotion.lower().strip()
    target_emotion = target_emotion.lower().strip()
    
    # Check if start and target are the same
    if start_emotion == target_emotion:
        # Return empty DataFrame to signal "no transition needed"
        return pd.DataFrame()
    
    # Find the emotional transition path using ISO principle
    emotion_path = find_emotion_path(start_emotion, target_emotion)
    
    # Calculate how many songs per emotion transition
    path_length = len(emotion_path)
    if path_length < 2:
        # Fallback to direct transition if path finding fails
        emotion_path = [start_emotion, target_emotion]
        path_length = 2
    
    # Distribute songs across the emotion path
    songs_per_step = max(1, num_steps // path_length)
    
    selected_rows: List[pd.Series] = []
    used_ids: Set[str] = set()
    
    # Generate playlist following the emotion path
    for i, emotion in enumerate(emotion_path):
        # Get V-A coordinates for current emotion in path
        v_current, a_current = get_va_coordinates(emotion)
        
        # Get next emotion for smooth transition
        if i < len(emotion_path) - 1:
            v_next, a_next = get_va_coordinates(emotion_path[i + 1])
            # Calculate number of songs for this transition
            songs_for_transition = songs_per_step
            
            # If this is the last transition, use remaining songs
            if i == len(emotion_path) - 2:
                songs_for_transition = num_steps - len(selected_rows)
            
            # Create smooth transition between current and next emotion
            for j in range(songs_for_transition):
                # Interpolate between current and next emotion
                progress = j / max(1, songs_for_transition - 1) if songs_for_transition > 1 else 1.0
                interpolated_v = v_current + (v_next - v_current) * progress
                interpolated_a = a_current + (a_next - a_current) * progress
                
                v_min, v_max = interpolated_v - tolerance, interpolated_v + tolerance
                a_min, a_max = interpolated_a - tolerance, interpolated_a + tolerance
                
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
                    # Widen search if no songs found
                    widen = tolerance * 2
                    song_df = music_engine.get_songs_in_va_range(
                        interpolated_v - widen,
                        interpolated_v + widen,
                        interpolated_a - widen,
                        interpolated_a + widen,
                        num_songs=1,
                        exclude_spotify_ids=used_ids,
                        random_state=random_state,
                    )
                    if not song_df.empty:
                        row = song_df.iloc[0]
                        selected_rows.append(row)
                        used_ids.add(str(row.get("spotify_id")))
                
                # Stop if we have enough songs
                if len(selected_rows) >= num_steps:
                    break
        
        if len(selected_rows) >= num_steps:
            break
    
    if not selected_rows:
        return pd.DataFrame()
    
    result = pd.DataFrame(selected_rows).reset_index(drop=True)
    keep_cols = [c for c in ["track", "artist", "spotify_id", "valence", "arousal"] if c in result.columns]
    return result[keep_cols]
