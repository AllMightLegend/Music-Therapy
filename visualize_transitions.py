"""
Visualize emotion transition graph for ISO Principle
"""
from recommendation_logic import EMOTION_TRANSITIONS, EMOTION_TO_VA
from collections import defaultdict

def print_transition_map():
    """Print a detailed ASCII map of emotion transitions"""
    
    print("\n" + "=" * 70)
    print(" " * 15 + "EMOTION TRANSITION MAP (ISO PRINCIPLE)")
    print("=" * 70)
    
    # Group emotions by valence
    negative = []
    neutral = []
    positive = []
    
    for emotion in EMOTION_TRANSITIONS.keys():
        v, _ = EMOTION_TO_VA.get(emotion, (0, 0))
        if v < -0.2:
            negative.append(emotion)
        elif v > 0.2:
            positive.append(emotion)
        else:
            neutral.append(emotion)
    
    print("\n📊 VALENCE-AROUSAL SPACE:\n")
    print("  NEGATIVE EMOTIONS (V < -0.2):")
    for emotion in sorted(negative):
        v, a = EMOTION_TO_VA[emotion]
        transitions = EMOTION_TRANSITIONS[emotion]
        print(f"    • {emotion.upper():12} (V={v:+.1f}, A={a:+.1f}) → {', '.join([t.title() for t in transitions])}")
    
    print("\n  NEUTRAL EMOTIONS (-0.2 ≤ V ≤ 0.2):")
    for emotion in sorted(neutral):
        v, a = EMOTION_TO_VA[emotion]
        transitions = EMOTION_TRANSITIONS[emotion]
        print(f"    • {emotion.upper():12} (V={v:+.1f}, A={a:+.1f}) → {', '.join([t.title() for t in transitions])}")
    
    print("\n  POSITIVE EMOTIONS (V > 0.2):")
    for emotion in sorted(positive):
        v, a = EMOTION_TO_VA[emotion]
        transitions = EMOTION_TRANSITIONS[emotion]
        print(f"    • {emotion.upper():12} (V={v:+.1f}, A={a:+.1f}) → {', '.join([t.title() for t in transitions])}")

def print_transition_statistics():
    """Print statistics about the transition graph"""
    
    print("\n" + "=" * 70)
    print(" " * 20 + "TRANSITION STATISTICS")
    print("=" * 70)
    
    # Count transitions
    total_emotions = len(EMOTION_TRANSITIONS)
    total_transitions = sum(len(targets) for targets in EMOTION_TRANSITIONS.values())
    
    print(f"\n📈 Overview:")
    print(f"  • Total Emotions: {total_emotions}")
    print(f"  • Total Possible Transitions: {total_transitions}")
    print(f"  • Average Transitions per Emotion: {total_transitions / total_emotions:.1f}")
    
    # Count incoming transitions
    incoming = defaultdict(int)
    for emotion, targets in EMOTION_TRANSITIONS.items():
        for target in targets:
            incoming[target] += 1
    
    # Count outgoing transitions
    outgoing = {emotion: len(targets) for emotion, targets in EMOTION_TRANSITIONS.items()}
    
    print(f"\n🎯 Most Reachable Emotions (Hub States):")
    for emotion, count in sorted(incoming.items(), key=lambda x: x[1], reverse=True)[:5]:
        print(f"  • {emotion.title():12} ← {count} incoming transitions")
    
    print(f"\n🚀 Most Flexible Emotions (Gateway States):")
    for emotion, count in sorted(outgoing.items(), key=lambda x: x[1], reverse=True)[:5]:
        print(f"  • {emotion.title():12} → {count} outgoing transitions")
    
    # Check connectivity
    all_emotions = set(EMOTION_TRANSITIONS.keys())
    reachable = set()
    for targets in EMOTION_TRANSITIONS.values():
        reachable.update(targets)
    
    unreachable = reachable - all_emotions
    if unreachable:
        print(f"\n⚠️  Emotions mentioned but no outgoing transitions: {', '.join(unreachable)}")

def print_common_journeys():
    """Print common therapeutic journeys"""
    
    from recommendation_logic import find_emotion_path
    
    print("\n" + "=" * 70)
    print(" " * 20 + "COMMON THERAPEUTIC JOURNEYS")
    print("=" * 70)
    
    journeys = [
        ("sad", "happy", "Negative to Positive"),
        ("sad", "calm", "Distress to Peace"),
        ("angry", "calm", "Agitation to Peace"),
        ("anxious", "relaxed", "Tension to Release"),
        ("fearful", "happy", "Fear to Joy"),
        ("surprised", "calm", "Excitement to Stability"),
    ]
    
    print()
    for start, target, description in journeys:
        path = find_emotion_path(start, target)
        path_str = " → ".join([e.title() for e in path])
        print(f"  {description:25} | {path_str}")
    
    print("\n" + "=" * 70)

if __name__ == "__main__":
    print_transition_map()
    print_transition_statistics()
    print_common_journeys()
    print("\n✅ Emotion transition graph analysis complete!\n")
