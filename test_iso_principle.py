"""
Test script for ISO Principle emotion transitions
"""
from recommendation_logic import find_emotion_path, EMOTION_TRANSITIONS, get_va_coordinates

def test_emotion_paths():
    """Test various emotion transition paths"""
    
    test_cases = [
        ("sad", "happy"),
        ("sad", "calm"),
        ("angry", "calm"),
        ("fearful", "happy"),
        ("anxious", "relaxed"),
        ("happy", "happy"),  # Same emotion
    ]
    
    print("=" * 60)
    print("ISO PRINCIPLE - EMOTION TRANSITION PATHS")
    print("=" * 60)
    
    for start, target in test_cases:
        path = find_emotion_path(start, target)
        print(f"\n{start.upper()} → {target.upper()}")
        print(f"Path: {' → '.join([e.title() for e in path])}")
        print(f"Steps: {len(path)}")
        
        # Show V-A coordinates
        print("Valence-Arousal progression:")
        for emotion in path:
            v, a = get_va_coordinates(emotion)
            print(f"  {emotion.title()}: V={v:+.2f}, A={a:+.2f}")
    
    print("\n" + "=" * 60)
    print("AVAILABLE EMOTION TRANSITIONS")
    print("=" * 60)
    
    for emotion, transitions in sorted(EMOTION_TRANSITIONS.items()):
        print(f"\n{emotion.upper()}: {', '.join([t.title() for t in transitions])}")

if __name__ == "__main__":
    test_emotion_paths()
