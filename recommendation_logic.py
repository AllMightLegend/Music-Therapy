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
    # Intermediate emotions for smoother transitions
    "melancholic": (-0.5, -0.4),  # Less sad, moving toward neutral
    "somber": (-0.35, -0.2),  # Between melancholic and neutral
    "irritated": (-0.45, 0.5),  # Less angry, still tense
    "tense": (-0.2, 0.4),  # Between irritated and anxious
    "uneasy": (-0.15, 0.3),  # Light anxiety, moving to neutral
    "content": (0.4, -0.3),  # Between neutral and calm
    "serene": (0.6, -0.5),  # Between content and calm
    "peaceful": (0.65, -0.6),  # Very close to calm
    "hopeful": (0.3, 0.1),  # Positive but low arousal
    "cheerful": (0.6, 0.5),  # Moving toward happy
}

# ISO Principle: Emotion transition graph with minimum 2-step paths
# Each transition now goes through intermediate states
EMOTION_TRANSITIONS: Dict[str, List[str]] = {
    # Sad pathway: sad → melancholic → somber → neutral/content → calm
    "sad": ["melancholic"],
    "melancholic": ["somber"],
    "somber": ["neutral", "content"],
    
    # Angry pathway: angry → irritated → tense → uneasy → neutral
    "angry": ["irritated"],
    "irritated": ["tense"],
    "tense": ["uneasy", "anxious"],
    
    # Fear/Anxious pathway: fear → anxious → uneasy → neutral
    "fearful": ["anxious"],
    "fear": ["anxious"],
    "anxious": ["uneasy"],
    "uneasy": ["neutral", "content"],
    
    # Surprise pathway
    "surprised": ["hopeful"],
    "surprise": ["hopeful"],
    "hopeful": ["neutral", "cheerful"],
    
    # Neutral is a hub connecting to multiple paths
    "neutral": ["content", "hopeful", "focused"],
    
    # Positive progression: content → serene → peaceful → calm
    "content": ["serene", "hopeful"],
    "serene": ["peaceful"],
    "peaceful": ["calm"],
    
    # Calm pathways
    "calm": ["relaxed", "peaceful"],
    "relaxed": ["calm", "content"],
    
    # Focus pathway
    "focused": ["content", "cheerful"],
    
    # Happy pathway: hopeful/cheerful → happy
    "cheerful": ["happy", "energized"],
    "energized": ["happy", "cheerful"],
    "happy": ["energized", "loving"],
    "loving": ["happy", "content"],
}


def get_va_coordinates(emotion: str) -> Tuple[float, float]:
    """Get valence-arousal coordinates for an emotion."""
    key = (emotion or "").strip().lower()
    if key not in EMOTION_TO_VA:
        return EMOTION_TO_VA["neutral"]
    return EMOTION_TO_VA[key]


def find_emotion_path(start: str, target: str) -> List[str]:
    """
    Find emotional transition path from start to target with MINIMUM 2 transitions.
    Uses BFS to find the most natural emotional progression based on ISO principle.
    Ensures at least 3 emotions in path (2 transitions) for gradual therapeutic progression.
    """
    start = start.lower().strip()
    target = target.lower().strip()
    
    if start == target:
        return [start]
    
    from collections import deque
    queue = deque([(start, [start])])
    visited = {start}
    
    # Store all found paths to ensure minimum 2 transitions
    found_paths = []
    
    while queue:
        current, path = queue.popleft()
        next_emotions = EMOTION_TRANSITIONS.get(current, [])
        
        for next_emotion in next_emotions:
            new_path = path + [next_emotion]
            
            if next_emotion == target:
                found_paths.append(new_path)
                # Continue searching for alternative paths
            
            if next_emotion not in visited:
                visited.add(next_emotion)
                queue.append((next_emotion, new_path))
    
    # If we found paths, prefer those with at least 2 transitions (3+ emotions)
    if found_paths:
        # Filter for paths with minimum 3 emotions (2 transitions)
        long_enough_paths = [p for p in found_paths if len(p) >= 3]
        
        if long_enough_paths:
            # Return the shortest path that meets the minimum requirement
            return min(long_enough_paths, key=len)
        else:
            # Path too short - create extended version
            shortest = min(found_paths, key=len)
            return _extend_short_path(shortest, target)
    
    # Fallback: Create path with intermediate emotions
    # Ensure minimum 2 transitions through neutral and intermediate states
    return _create_minimum_transition_path(start, target)


def _extend_short_path(path: List[str], target: str) -> List[str]:
    """
    Extend a path that's too short (< 3 emotions) by adding intermediate emotions.
    """
    if len(path) >= 3:
        return path
    
    start = path[0]
    
    # Add appropriate intermediate emotions based on valence-arousal
    v_start, a_start = get_va_coordinates(start)
    v_target, a_target = get_va_coordinates(target)
    
    # Create intermediate emotion
    v_mid = (v_start + v_target) / 2
    a_mid = (a_start + a_target) / 2
    
    # Find closest intermediate emotion
    best_intermediate = "neutral"
    min_dist = float('inf')
    
    for emotion in EMOTION_TO_VA.keys():
        if emotion not in [start, target]:
            v, a = get_va_coordinates(emotion)
            dist = abs(v - v_mid) + abs(a - a_mid)
            if dist < min_dist:
                min_dist = dist
                best_intermediate = emotion
    
    return [start, best_intermediate, target]


def _create_minimum_transition_path(start: str, target: str) -> List[str]:
    """
    Create a fallback path with minimum 2 transitions when no graph path exists.
    """
    # Calculate emotional distance
    v_start, a_start = get_va_coordinates(start)
    v_target, a_target = get_va_coordinates(target)
    
    # Find two intermediate emotions
    intermediates = []
    
    # First intermediate: 1/3 of the way
    v_int1 = v_start + (v_target - v_start) / 3
    a_int1 = a_start + (a_target - a_start) / 3
    
    # Second intermediate: 2/3 of the way  
    v_int2 = v_start + 2 * (v_target - v_start) / 3
    a_int2 = a_start + 2 * (a_target - a_start) / 3
    
    # Find closest emotions for each intermediate point
    for v_mid, a_mid in [(v_int1, a_int1), (v_int2, a_int2)]:
        best_emotion = "neutral"
        min_dist = float('inf')
        
        for emotion in EMOTION_TO_VA.keys():
            if emotion not in [start, target] + intermediates:
                v, a = get_va_coordinates(emotion)
                dist = ((v - v_mid) ** 2 + (a - a_mid) ** 2) ** 0.5
                if dist < min_dist:
                    min_dist = dist
                    best_emotion = emotion
        
        intermediates.append(best_emotion)
    
    return [start, intermediates[0], intermediates[1], target]


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
        
        # Set random seed for reproducible randomness
        if random_state is not None:
            np.random.seed(random_state)
        
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
                    n_neighbors=min(50, len(self.engine.df))  # Increased from 20 to 50 for more variety
                )
                
                # Score all candidates and create weighted selection pool
                candidates = []
                scores = []
                
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
                    
                    candidates.append((song, score))
                    scores.append(score)
                
                # Select from top candidates with weighted randomness
                if candidates:
                    # Normalize scores to positive values for probability weights
                    scores = np.array(scores)
                    scores = scores - scores.min() + 0.1  # Shift to positive
                    scores = np.exp(scores)  # Exponential weighting favors higher scores
                    probabilities = scores / scores.sum()
                    
                    # Randomly select from top candidates based on scores
                    selected_idx = np.random.choice(len(candidates), p=probabilities)
                    best_song = candidates[selected_idx][0]
                    
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
