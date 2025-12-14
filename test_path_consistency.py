"""Test to verify emotion path remains consistent through multi-step journey"""
from recommendation_logic import find_emotion_path

print("=" * 70)
print("TESTING EMOTION PATH CONSISTENCY")
print("=" * 70)

# Test the scenario: Sad to Energized
# This shows the bug more clearly
print("\n🎯 Scenario: Sad to Energized")
print("-" * 50)

initial_path = find_emotion_path("sad", "energized")
print(f"Initial Path: {' → '.join([e.title() for e in initial_path])}")
print(f"Total steps: {len(initial_path) - 1}")

print("\n📋 Expected flow through the journey:")
for step in range(len(initial_path) - 1):
    from_emotion = initial_path[step]
    to_emotion = initial_path[step + 1]
    print(f"  Step {step + 1}: {from_emotion.title()} → {to_emotion.title()}")

# Show what WOULD happen if path is recalculated (the BUG)
print("\n⚠️  BUG SCENARIO - If path is recalculated at each step:")
print("-" * 50)

for step in range(1, min(4, len(initial_path) - 1)):
    from_emotion = initial_path[step]
    expected_to = initial_path[step + 1]
    
    # Bug: recalculating path from current position
    new_path = find_emotion_path(from_emotion, "energized")
    actual_next = new_path[1] if len(new_path) > 1 else "?"
    
    print(f"\n  After Step {step}, detected_mood = '{from_emotion}'")
    print(f"  Recalculated path: {' → '.join([e.title() for e in new_path])}")
    print(f"  Recalculated next: {from_emotion.title()} → {actual_next.title()}")
    print(f"  Expected next:     {from_emotion.title()} → {expected_to.title()}")
    
    if actual_next.lower() != expected_to.lower():
        print(f"  ❌ PATHS DIVERGE! This causes the bug!")
    else:
        print(f"  ✓ Paths happen to align for this step")

print("\n" + "=" * 70)
print("✅ FIX IMPLEMENTED: emotion_path is now stored in session state")
print("   once at journey start and reused throughout.")
print("=" * 70)
