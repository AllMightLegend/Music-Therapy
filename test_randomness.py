"""Test that different random_state values produce different playlists"""
from recommendation_logic import generate_playlist
from music_engine import MusicEngine

print("=" * 70)
print("TESTING PLAYLIST RANDOMNESS")
print("=" * 70)

engine = MusicEngine()

# Generate 3 playlists for sad->calm with different random states
playlists = []
for i in range(1, 4):
    print(f"\n🎲 Generating playlist with random_state={i * 1000}")
    playlist = generate_playlist(
        music_engine=engine,
        start_emotion="sad",
        target_emotion="calm",
        num_steps=5,
        tolerance=0.1,
        random_state=i * 1000
    )
    playlists.append(playlist)
    
    if not playlist.empty:
        print(f"   Generated {len(playlist)} songs")
        print("   First 3 tracks:")
        for idx in range(min(3, len(playlist))):
            track = playlist.iloc[idx].get('track', 'Unknown')
            artist = playlist.iloc[idx].get('artist', 'Unknown')
            print(f"   {idx+1}. {track} by {artist}")

# Compare playlists
print("\n" + "=" * 70)
print("COMPARISON RESULTS")
print("=" * 70)

if len(playlists) == 3 and all(not p.empty for p in playlists):
    # Compare track IDs
    ids_1 = set(playlists[0]['spotify_id'].tolist())
    ids_2 = set(playlists[1]['spotify_id'].tolist())
    ids_3 = set(playlists[2]['spotify_id'].tolist())
    
    # Calculate overlap
    overlap_12 = len(ids_1 & ids_2)
    overlap_13 = len(ids_1 & ids_3)
    overlap_23 = len(ids_2 & ids_3)
    
    print(f"\n📊 Song Overlap Analysis:")
    print(f"   Playlist 1 vs 2: {overlap_12}/{len(ids_1)} songs in common")
    print(f"   Playlist 1 vs 3: {overlap_13}/{len(ids_1)} songs in common")
    print(f"   Playlist 2 vs 3: {overlap_23}/{len(ids_2)} songs in common")
    
    if overlap_12 < len(ids_1) or overlap_13 < len(ids_1) or overlap_23 < len(ids_2):
        print("\n✅ SUCCESS: Different random_state values produce different playlists!")
    else:
        print("\n❌ FAILURE: All playlists are identical despite different random_state")
else:
    print("\n❌ FAILURE: Could not generate all playlists")
