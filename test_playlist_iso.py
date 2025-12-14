"""
Test recommendation logic with ISO principle
"""
from music_engine import MusicEngine
from recommendation_logic import generate_playlist, find_emotion_path

def test_playlist_generation():
    """Test playlist generation with different emotion transitions"""
    
    print("=" * 60)
    print("TESTING PLAYLIST GENERATION WITH ISO PRINCIPLE")
    print("=" * 60)
    
    # Initialize music engine
    engine = MusicEngine()
    
    if not engine.is_ready():
        print("❌ Music engine not ready. Make sure muse_v3.csv exists.")
        return
    
    print(f"✅ Music engine loaded with {len(engine.df)} songs\n")
    
    # Test cases
    test_cases = [
        ("sad", "calm", "Should transition: Sad → Calm"),
        ("sad", "happy", "Should transition: Sad → Neutral → Happy"),
        ("angry", "calm", "Should transition: Angry → Anxious → Calm"),
        ("happy", "happy", "Same emotion - should return empty (no transition needed)"),
    ]
    
    for start, target, description in test_cases:
        print(f"\n{'=' * 60}")
        print(f"TEST: {start.upper()} → {target.upper()}")
        print(f"Expected: {description}")
        print(f"{'=' * 60}")
        
        # Find emotion path
        path = find_emotion_path(start, target)
        print(f"Emotion Path: {' → '.join([e.title() for e in path])}")
        
        # Generate playlist
        playlist = generate_playlist(
            music_engine=engine,
            start_emotion=start,
            target_emotion=target,
            num_steps=5,
            tolerance=0.15
        )
        
        if playlist.empty:
            if start == target:
                print("✅ PASS: Empty playlist returned (same emotion)")
            else:
                print("⚠️ WARNING: No songs found for this transition")
        else:
            print(f"✅ Generated {len(playlist)} songs:")
            for idx, row in playlist.iterrows():
                track = row.get('track', 'Unknown')
                artist = row.get('artist', 'Unknown')
                valence = row.get('valence', 0)
                arousal = row.get('arousal', 0)
                print(f"  {idx+1}. {track} by {artist} (V={valence:.2f}, A={arousal:.2f})")

if __name__ == "__main__":
    test_playlist_generation()
