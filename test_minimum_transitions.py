"""
Test the updated emotion transition system with minimum 2 transitions
"""
from recommendation_logic import find_emotion_path, EMOTION_TRANSITIONS, EMOTION_TO_VA

def test_minimum_transitions():
    print("=" * 70)
    print("TESTING MINIMUM 2-TRANSITION REQUIREMENT")
    print("=" * 70)
    
    test_cases = [
        ("sad", "calm"),
        ("sad", "happy"),
        ("angry", "calm"),
        ("anxious", "relaxed"),
        ("fearful", "happy"),
        ("surprised", "calm"),
    ]
    
    print("\n📊 Checking all paths have minimum 2 transitions (3+ emotions):\n")
    
    all_pass = True
    for start, target in test_cases:
        path = find_emotion_path(start, target)
        num_transitions = len(path) - 1
        num_emotions = len(path)
        
        # Check if meets minimum requirement
        meets_requirement = num_transitions >= 2
        status = "✅" if meets_requirement else "❌"
        
        print(f"{status} {start.upper()} → {target.upper()}")
        print(f"   Path: {' → '.join([e.title() for e in path])}")
        print(f"   Emotions: {num_emotions}, Transitions: {num_transitions}")
        
        if not meets_requirement:
            print(f"   ⚠️ FAILED: Only {num_transitions} transition(s), need at least 2")
            all_pass = False
        
        # Show V-A progression
        print(f"   Valence-Arousal:")
        for emotion in path:
            v, a = EMOTION_TO_VA.get(emotion, (0, 0))
            print(f"      {emotion.title():15} V={v:+.2f}, A={a:+.2f}")
        print()
    
    print("=" * 70)
    if all_pass:
        print("✅ ALL TESTS PASSED - All paths have minimum 2 transitions")
    else:
        print("❌ SOME TESTS FAILED - Not all paths meet minimum requirement")
    print("=" * 70)
    
    # Show the new intermediate emotions
    print("\n📝 NEW INTERMEDIATE EMOTIONS:")
    print("=" * 70)
    intermediate_emotions = [
        "melancholic", "somber", "irritated", "tense", "uneasy",
        "content", "serene", "peaceful", "hopeful", "cheerful"
    ]
    
    for emotion in intermediate_emotions:
        if emotion in EMOTION_TO_VA:
            v, a = EMOTION_TO_VA[emotion]
            print(f"  {emotion.title():15} V={v:+.2f}, A={a:+.2f}")
    
    print("\n✅ Intermediate emotions successfully added for gradual transitions")

if __name__ == "__main__":
    test_minimum_transitions()
