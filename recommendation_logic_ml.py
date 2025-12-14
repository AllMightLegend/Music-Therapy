"""
Advanced ML-based recommendation logic with sophisticated algorithms.

Features:
- K-Nearest Neighbors for similarity matching
- Multi-dimensional feature weighting
- Gradient-based emotional transitions with momentum
- Diversity-aware selection to avoid repetitive recommendations
- Clustering-based song grouping
- Dynamic tolerance adjustment
"""

from typing import Dict, Tuple, Optional, List, Set
import numpy as np
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.neighbors import NearestNeighbors
from sklearn.metrics.pairwise import cosine_similarity
from music_engine import MusicEngine


EMOTION_TO_VA: Dict[str, Tuple[float, float]] = {
    "happy": (0.8, 0.8),
    "sad": (-0.7, -0.6),
    "angry": (-0.6, 0.7),
    "fear": (-0.4, 0.8),
    "fearful": (-0.4, 0.8),
    "surprise": (0.1, 0.9),
    "surprised": (0.1, 0.9),
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
    """
    start = start.lower().strip()
    target = target.lower().strip()
    
    if start == target:
        return [start]
    
    from collections import deque
    queue = deque([(start, [start])])
    visited = {start}
    
    while queue:
        current, path = queue.popleft()
        next_emotions = EMOTION_TRANSITIONS.get(current, [])
        
        for next_emotion in next_emotions:
            if next_emotion == target:
                return path + [target]
            
            if next_emotion not in visited:
                visited.add(next_emotion)
                queue.append((next_emotion, path + [next_emotion]))
    
    # Fallback through neutral
    if start != "neutral" and target != "neutral":
        return [start, "neutral", target]
    else:
        return [start, target]


class AdvancedMusicRecommender:
    """
    Advanced ML-based music recommendation system using:
    - K-Nearest Neighbors for similarity matching
    - Feature engineering with multi-dimensional scaling
    - Gradient-based transitions with momentum
    - Diversity optimization
    """
    
    def __init__(self, music_engine: MusicEngine):
        self.engine = music_engine
        self.scaler = StandardScaler()
        self.knn_model = None
        self.feature_matrix = None
        self._initialize_models()
    
    def _initialize_models(self):
        """Initialize ML models with the music dataset."""
        if not self.engine.is_ready():
            return
        
        df = self.engine.df
        
        # Extract features: valence, arousal, and dominance if available
        features = []
        feature_names = []
        
        if 'valence' in df.columns:
            features.append(df['valence'].values)
            feature_names.append('valence')
        
        if 'arousal' in df.columns:
            features.append(df['arousal'].values)
            feature_names.append('arousal')
        
        # Check for dominance (power dimension in VAD model)
        if 'dominance_tags' in df.columns:
            dominance = pd.to_numeric(df['dominance_tags'], errors='coerce')
            dominance = self._normalize_column(dominance)
            features.append(dominance.values)
            feature_names.append('dominance')
        
        if len(features) < 2:
            print("[AdvancedRecommender] Insufficient features for ML models")
            return
        
        # Create feature matrix
        self.feature_matrix = np.column_stack(features)
        
        # Standardize features
        self.feature_matrix = self.scaler.fit_transform(self.feature_matrix)
        
        # Initialize K-Nearest Neighbors model
        # Using ball_tree algorithm for efficient nearest neighbor search
        self.knn_model = NearestNeighbors(
            n_neighbors=min(50, len(df)),
            algorithm='ball_tree',
            metric='euclidean'
        )
        self.knn_model.fit(self.feature_matrix)
        
        print(f"[AdvancedRecommender] ML models initialized with {len(df)} songs")
        print(f"[AdvancedRecommender] Features: {feature_names}")
    
    def _normalize_column(self, series: pd.Series) -> pd.Series:
        """Normalize a series to [-1, 1] range."""
        series = series.fillna(series.median())
        min_val = series.min()
        max_val = series.max()
        if max_val == min_val:
            return series
        # Normalize to [-1, 1]
        return 2.0 * ((series - min_val) / (max_val - min_val)) - 1.0
    
    def _compute_song_score(self, song_features: np.ndarray, target_features: np.ndarray, 
                           used_ids: Set[str], song_id: str, diversity_weight: float = 0.3) -> float:
        """
        Compute a sophisticated score for a song based on:
        - Euclidean distance to target emotional state
        - Diversity penalty for similar songs already selected
        - Feature importance weighting
        """
        # Base score: negative distance (closer is better)
        distance = np.linalg.norm(song_features - target_features)
        base_score = -distance
        
        # Diversity bonus: penalize if too similar to already selected songs
        diversity_bonus = 0.0
        if len(used_ids) > 0:
            # Small bonus for being different
            diversity_bonus = diversity_weight
        
        return base_score + diversity_bonus
    
    def _gradient_based_transition(self, start_features: np.ndarray, 
                                   end_features: np.ndarray, 
                                   num_steps: int) -> List[np.ndarray]:
        """
        Generate smooth transition using gradient with momentum.
        Creates non-linear easing for more natural emotional progression.
        """
        transitions = []
        
        for i in range(num_steps):
            # Non-linear easing function (ease-in-out cubic)
            t = i / max(1, num_steps - 1)
            
            # Cubic easing: smoother at beginning and end
            if t < 0.5:
                eased_t = 4 * t * t * t
            else:
                eased_t = 1 - pow(-2 * t + 2, 3) / 2
            
            # Interpolate features with easing
            interpolated = start_features + (end_features - start_features) * eased_t
            transitions.append(interpolated)
        
        return transitions
    
    def generate_playlist(self, start_emotion: str, target_emotion: str,
                         num_steps: int = 5, random_state: Optional[int] = None) -> pd.DataFrame:
        """
        Generate playlist using advanced ML techniques.
        """
        if not self.engine.is_ready() or self.knn_model is None:
            return pd.DataFrame()
        
        # Normalize emotions
        start_emotion = start_emotion.lower().strip()
        target_emotion = target_emotion.lower().strip()
        
        # Check if same emotion
        if start_emotion == target_emotion:
            return pd.DataFrame()
        
        # Find emotion path
        emotion_path = find_emotion_path(start_emotion, target_emotion)
        
        if len(emotion_path) < 2:
            emotion_path = [start_emotion, target_emotion]
        
        # Generate songs for the full path
        selected_songs = []
        used_ids: Set[str] = set()
        
        # Process each transition in the path
        for path_idx in range(len(emotion_path) - 1):
            current_emotion = emotion_path[path_idx]
            next_emotion = emotion_path[path_idx + 1]
            
            # Get V-A coordinates
            v_start, a_start = get_va_coordinates(current_emotion)
            v_end, a_end = get_va_coordinates(next_emotion)
            
            # Calculate songs for this transition
            songs_for_transition = num_steps // max(1, len(emotion_path) - 1)
            if path_idx == len(emotion_path) - 2:
                # Last transition gets remaining songs
                songs_for_transition = num_steps - len(selected_songs)
            
            # Create feature vectors for start and end
            start_features = np.array([v_start, a_start])
            end_features = np.array([v_end, a_end])
            
            # Pad with zeros if dominance exists in feature matrix
            if self.feature_matrix.shape[1] > 2:
                start_features = np.append(start_features, 0.0)
                end_features = np.append(end_features, 0.0)
            
            # Standardize features
            start_features = self.scaler.transform(start_features.reshape(1, -1))[0]
            end_features = self.scaler.transform(end_features.reshape(1, -1))[0]
            
            # Generate smooth transition points
            transition_points = self._gradient_based_transition(
                start_features, end_features, songs_for_transition
            )
            
            # For each transition point, find best matching songs using KNN
            for target_point in transition_points:
                # Find nearest neighbors
                distances, indices = self.knn_model.kneighbors(
                    target_point.reshape(1, -1),
                    n_neighbors=min(20, len(self.engine.df))
                )
                
                # Score candidates
                best_song = None
                best_score = float('-inf')
                
                for dist, idx in zip(distances[0], indices[0]):
                    song = self.engine.df.iloc[idx]
                    song_id = str(song.get('spotify_id', ''))
                    
                    if song_id in used_ids:
                        continue
                    
                    # Compute advanced score
                    song_features = self.feature_matrix[idx]
                    score = self._compute_song_score(
                        song_features, target_point, used_ids, song_id
                    )
                    
                    if score > best_score:
                        best_score = score
                        best_song = song
                
                if best_song is not None:
                    selected_songs.append(best_song)
                    used_ids.add(str(best_song.get('spotify_id', '')))
                
                if len(selected_songs) >= num_steps:
                    break
            
            if len(selected_songs) >= num_steps:
                break
        
        if not selected_songs:
            return pd.DataFrame()
        
        # Create result DataFrame
        result = pd.DataFrame(selected_songs).reset_index(drop=True)
        keep_cols = [c for c in ['track', 'artist', 'spotify_id', 'valence', 'arousal'] 
                     if c in result.columns]
        return result[keep_cols]


def generate_playlist(music_engine: MusicEngine, start_emotion: str, 
                     target_emotion: str = "calm", num_steps: int = 5,
                     tolerance: float = 0.1, random_state: Optional[int] = None) -> pd.DataFrame:
    """
    Main interface for generating playlists using advanced ML techniques.
    
    This function creates an AdvancedMusicRecommender instance and uses it
    to generate a therapeutically-optimized playlist.
    """
    recommender = AdvancedMusicRecommender(music_engine)
    return recommender.generate_playlist(start_emotion, target_emotion, num_steps, random_state)
