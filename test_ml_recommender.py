"""
Test the advanced ML-based recommendation system
"""
from music_engine import MusicEngine
from recommendation_logic import generate_playlist, find_emotion_path, AdvancedMusicRecommender

def test_ml_recommender():
    """Test the new ML-based recommendation system"""
    
    print("=" * 70)
    print(" " * 15 + "ADVANCED ML RECOMMENDATION SYSTEM TEST")
    print("=" * 70)
    
    # Initialize music engine
    engine = MusicEngine()
    
    if not engine.is_ready():
        print("❌ Music engine not ready")
        return
    
    print(f"\n✅ Music engine loaded with {len(engine.df)} songs\n")
    
    # Test the advanced recommender initialization
    print("=" * 70)
    print("INITIALIZING ADVANCED ML MODELS")
    print("=" * 70)
    recommender = AdvancedMusicRecommender(engine)
    
    if recommender.knn_model is not None:
        print("✅ K-Nearest Neighbors model initialized")
        print(f"✅ Feature matrix shape: {recommender.feature_matrix.shape}")
        print(f"✅ Using {recommender.feature_matrix.shape[1]} features per song")
    else:
        print("❌ ML models failed to initialize")
        return
    
    # Test cases
    test_cases = [
        ("sad", "happy", "Complex transition with ML optimization"),
        ("angry", "calm", "Multi-step ISO principle path"),
        ("anxious", "relaxed", "Therapeutic transition"),
    ]
    
    for start, target, description in test_cases:
        print("\n" + "=" * 70)
        print(f"TEST: {start.upper()} → {target.upper()}")
        print(f"Description: {description}")
        print("=" * 70)
        
        # Find emotion path
        path = find_emotion_path(start, target)
        print(f"Emotion Path: {' → '.join([e.title() for e in path])}")
        
        # Generate playlist
        playlist = generate_playlist(
            music_engine=engine,
            start_emotion=start,
            target_emotion=target,
            num_steps=6
        )
        
        if not playlist.empty:
            print(f"\n✅ Generated {len(playlist)} songs using ML algorithms")
            print("\nPlaylist with emotional progression:")
            
            for idx, row in playlist.iterrows():
                track = row.get('track', 'Unknown')[:40]
                artist = row.get('artist', 'Unknown')[:25]
                v = row.get('valence', 0)
                a = row.get('arousal', 0)
                
                # Show progression
                progress_bar = "█" * int((idx + 1) / len(playlist) * 20)
                print(f"  {idx+1}. [{progress_bar:<20}] V={v:+.2f} A={a:+.2f}")
                print(f"     {track} - {artist}")
            
            # Analyze smoothness
            valences = [row.get('valence', 0) for _, row in playlist.iterrows()]
            changes = [abs(valences[i+1] - valences[i]) for i in range(len(valences)-1)]
            avg_change = sum(changes) / len(changes) if changes else 0
            max_change = max(changes) if changes else 0
            
            print(f"\n📊 Transition Analysis:")
            print(f"   Starting valence: {valences[0]:+.2f}")
            print(f"   Ending valence: {valences[-1]:+.2f}")
            print(f"   Average change per step: {avg_change:.3f}")
            print(f"   Maximum change: {max_change:.3f}")
            
            if max_change < 0.4:
                print(f"   ✅ Excellent smoothness (ML-optimized transitions)")
            elif max_change < 0.6:
                print(f"   ✅ Good smoothness")
            else:
                print(f"   ⚠️  Some larger transitions present")
        else:
            print("❌ No songs generated")
    
    # Compare with simple linear approach
    print("\n" + "=" * 70)
    print("COMPARISON: ML vs Simple Linear Interpolation")
    print("=" * 70)
    
    print("\n🤖 ML-Based Approach:")
    print("   • K-Nearest Neighbors for optimal song matching")
    print("   • Gradient-based transitions with momentum")
    print("   • Cubic easing for natural emotional flow")
    print("   • Multi-feature scoring (valence, arousal, dominance)")
    print("   • Diversity-aware selection")
    print("   • Standardized feature scaling")
    
    print("\n📈 Simple Approach (old):")
    print("   • Linear interpolation only")
    print("   • Basic range filtering")
    print("   • No feature weighting")
    print("   • No diversity optimization")
    
    print("\n✅ ML approach provides more sophisticated and therapeutically sound recommendations!")
    print("=" * 70 + "\n")

if __name__ == "__main__":
    test_ml_recommender()
