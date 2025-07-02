import streamlit as st
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials, SpotifyOAuth
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import os
from typing import List, Dict, Optional

# Spotify API credentials - Use environment variables for security
@st.cache_data
def get_spotify_credentials():
    """Get Spotify credentials from environment variables or Streamlit secrets"""
    try:
        client_id = None
        client_secret = None
        
        # Try Streamlit secrets first
        if hasattr(st, 'secrets'):
            try:
                client_id = st.secrets.get("SPOTIPY_CLIENT_ID")
                client_secret = st.secrets.get("SPOTIPY_CLIENT_SECRET")
            except Exception:
                pass
        
        # Fall back to environment variables
        if not client_id or not client_secret:
            client_id = os.getenv('SPOTIPY_CLIENT_ID')
            client_secret = os.getenv('SPOTIPY_CLIENT_SECRET')
        
        # Validate credentials format
        if client_id and client_secret:
            # Clean any whitespace or quotes
            client_id = client_id.strip().strip('"').strip("'")
            client_secret = client_secret.strip().strip('"').strip("'")
            
            # Basic validation
            if len(client_id) != 32:
                st.error(f"❌ Invalid Client ID format. Expected 32 characters, got {len(client_id)}. Please check your credentials.")
                st.info("💡 Client ID should be a 32-character alphanumeric string")
                st.stop()
            
            if len(client_secret) != 32:
                st.error(f"❌ Invalid Client Secret format. Expected 32 characters, got {len(client_secret)}. Please check your credentials.")
                st.info("💡 Client Secret should be a 32-character alphanumeric string")
                st.stop()
            
            return client_id, client_secret
        
        # Show setup instructions if credentials not found
        st.error("❌ Spotify API credentials not found!")
        st.markdown("""
        ### 🔧 How to set up Spotify API credentials:
        
        1. **Create a Spotify App:**
           - Go to [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
           - Click "Create an App"
           - Fill in the app name and description
           - Accept the terms and create the app
        
        2. **Get your credentials:**
           - Click on your newly created app
           - Copy the **Client ID** (32-character string)
           - Click "Show Client Secret" and copy the **Client Secret** (32-character string)
        
        3. **Set up credentials in Streamlit:**
           
           **Option 1: Environment Variables**
           ```bash
           export SPOTIPY_CLIENT_ID="your_32_char_client_id"
           export SPOTIPY_CLIENT_SECRET="your_32_char_client_secret"
           ```
           
           **Option 2: Streamlit Secrets**
           Create `.streamlit/secrets.toml`:
           ```toml
           SPOTIPY_CLIENT_ID = "your_32_char_client_id"
           SPOTIPY_CLIENT_SECRET = "your_32_char_client_secret"
           ```
        
        4. **Restart the app** after setting up credentials
        """)
        st.stop()
        
    except Exception as e:
        st.error(f"❌ Error loading credentials: {str(e)}")
        st.stop()

# Initialize Spotify client with error handling
@st.cache_resource
def initialize_spotify_client():
    """Initialize and return Spotify client"""
    try:
        client_id, client_secret = get_spotify_credentials()
        
        # Show masked credentials for debugging
        masked_id = client_id[:4] + "*" * 24 + client_id[-4:]
        masked_secret = client_secret[:4] + "*" * 24 + client_secret[-4:]
        st.info(f"🔑 Using Client ID: {masked_id}")
        
        # Check if this is the ID from the original code (Development mode app)
        if client_id == "db92830dca624bb99e5e383038329699":
            st.warning("⚠️ **Development Mode Detected!** Your app is in Development mode. You may need to add users in the User Management section of your Spotify app dashboard.")
            st.session_state.dev_mode_detected = True
        
        sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
            client_id=client_id,
            client_secret=client_secret
        ))
        
        # Test the connection with a simple search
        test_result = sp.search(q="test", limit=1, type='track')
        if test_result:
            st.success("✅ Successfully connected to Spotify API!")
            return sp
        else:
            st.error("❌ Failed to connect to Spotify API - empty response")
            st.stop()
            
    except spotipy.exceptions.SpotifyException as e:
        error_msg = str(e).lower()
        
        if "invalid_client" in error_msg:
            st.error("❌ **Invalid Client Credentials!**")
            st.markdown("""
            ### 🔍 Your app appears to be in Development Mode
            
            Based on your app dashboard, your Spotify app is in **Development mode**. This restricts API access.
            
            #### 🚀 **Quick Fix - Add yourself as a user:**
            1. Go to your [Spotify App Dashboard](https://developer.spotify.com/dashboard)
            2. Click on your app: **SAQ_Mood_recommender**
            3. Go to **"User Management"** tab
            4. Add your Spotify email address as a user
            5. Click **"Add user"**
            6. Restart this app
            
            #### 🎯 **Better Solution - Request Extended Quota:**
            1. In your app dashboard, look for **"Request Extended Quota Mode"**
            2. Fill out the form (mention it's for a playlist generator)
            3. This removes the 25-user limit and enables full API access
            
            #### 📋 **Other potential issues:**
            1. **Credential format**: Ensure 32-character strings with no extra spaces
            2. **Copy-paste errors**: Re-copy from dashboard (avoid typos like 'O' vs '0')
            3. **Old credentials**: Try regenerating Client Secret if needed
            
            **Your Client ID from dashboard:** `db92830dca624bb99e5e383038329699`
            
            Make sure this matches exactly what you're using in your environment variables.
            """)
        else:
            st.error(f"❌ Spotify API Error: {str(e)}")
            
        st.stop()
        
    except Exception as e:
        st.error(f"❌ Unexpected error initializing Spotify client: {str(e)}")
        st.info("💡 Try refreshing the page or check your internet connection")
        st.stop()

# Safe, pre-vetted genre list
VALID_GENRES = sorted([
    "acoustic", "afrobeat", "alt-rock", "alternative", "ambient", "anime", "black-metal",
    "bluegrass", "blues", "brazil", "breakbeat", "british", "cantopop", "chill", "classical",
    "club", "comedy", "country", "dance", "dancehall", "death-metal", "deep-house",
    "disco", "disney", "drum-and-bass", "dub", "dubstep", "edm", "electro", "electronic",
    "emo", "folk", "french", "funk", "garage", "german", "gospel", "grunge", "guitar",
    "happy", "hard-rock", "hardcore", "hardstyle", "heavy-metal", "hip-hop", "holidays",
    "house", "indian", "indie", "indie-pop", "industrial", "j-dance", "j-pop", "j-rock",
    "jazz", "k-pop", "latin", "malay", "mandopop", "metal", "metalcore", "minimal-techno",
    "movies", "new-age", "opera", "party", "philippines-opm", "piano", "pop", "pop-film",
    "power-pop", "progressive-house", "psych-rock", "punk", "r-n-b", "reggae", "reggaeton",
    "rock", "romance", "sad", "salsa", "samba", "sertanejo", "show-tunes",
    "singer-songwriter", "ska", "sleep", "soul", "soundtracks", "spanish", "study", "summer",
    "synth-pop", "tango", "techno", "trance", "trip-hop", "work-out", "world-music"
])

# Streamlit app setup
st.set_page_config(
    page_title="🎵 Spotify Playlist Generator", 
    page_icon="🎧", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Enhanced CSS with better styling and improved contrast
st.markdown("""
    <style>
    .stApp {
        background: linear-gradient(135deg, #0f1419 0%, #1a1f35 50%, #0d1421 100%);
        color: #ffffff;
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    }
    .main-header {
        text-align: center;
        padding: 30px 0;
        background: rgba(29, 185, 84, 0.1);
        border-radius: 20px;
        margin-bottom: 40px;
        backdrop-filter: blur(15px);
        border: 1px solid rgba(29, 185, 84, 0.2);
    }
    h1, h2, h3, h4, h5, h6 {
        color: #ffffff !important;
    }
    .stButton button {
        background: linear-gradient(45deg, #1DB954, #1ed760);
        color: white !important;
        border: none;
        border-radius: 25px;
        padding: 15px 40px;
        font-size: 18px;
        font-weight: 600;
        transition: all 0.3s ease;
        width: 100%;
        box-shadow: 0 4px 15px rgba(29, 185, 84, 0.3);
    }
    .stButton button:hover {
        transform: translateY(-3px);
        box-shadow: 0 8px 25px rgba(29, 185, 84, 0.5);
        background: linear-gradient(45deg, #1ed760, #21e065);
    }
    .stSelectbox > div > div, .stTextInput > div > div, .stNumberInput > div > div {
        background-color: #2a3441 !important;
        color: #ffffff !important;
        border: 2px solid #404854;
        border-radius: 12px;
        transition: all 0.3s ease;
    }
    .stSelectbox > div > div:focus-within, .stTextInput > div > div:focus-within, .stNumberInput > div > div:focus-within {
        border-color: #1DB954 !important;
        box-shadow: 0 0 15px rgba(29, 185, 84, 0.4);
    }
    .stSelectbox label, .stTextInput label, .stNumberInput label, .stSlider label {
        color: #ffffff !important;
        font-weight: 600;
        font-size: 16px;
    }
    .stSelectbox input, .stTextInput input, .stNumberInput input {
        color: #ffffff !important;
        background-color: transparent !important;
    }
    .stSlider > div > div > div {
        background-color: #1DB954 !important;
    }
    .track-container {
        background: linear-gradient(135deg, rgba(42, 52, 65, 0.8), rgba(58, 71, 90, 0.6));
        border-radius: 15px;
        padding: 20px;
        margin: 15px 0;
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
    }
    .track-info {
        background: rgba(29, 185, 84, 0.1);
        border-radius: 12px;
        padding: 15px;
        border: 1px solid rgba(29, 185, 84, 0.2);
    }
    .track-title {
        color: #1DB954 !important;
        font-size: 18px;
        font-weight: 700;
        margin: 0 0 8px 0;
    }
    .track-artist {
        color: #b3b3b3 !important;
        font-size: 14px;
        margin: 0;
    }
    .download-section {
        background: linear-gradient(135deg, rgba(29, 185, 84, 0.15), rgba(30, 215, 96, 0.1));
        border-radius: 20px;
        padding: 25px;
        margin-top: 30px;
        border: 2px solid rgba(29, 185, 84, 0.3);
        backdrop-filter: blur(10px);
    }
    .spotify-export {
        background: linear-gradient(45deg, #191414, #1DB954);
        border-radius: 15px;
        padding: 20px;
        margin: 20px 0;
        border: 1px solid rgba(29, 185, 84, 0.4);
    }
    .stMarkdown {
        color: #ffffff !important;
    }
    .stSelectbox div[data-baseweb="select"] > div {
        background-color: #2a3441 !important;
        color: #ffffff !important;
    }
    .stTextInput input::placeholder {
        color: #8b9dc3 !important;
    }
    </style>
    """, unsafe_allow_html=True)

def get_audio_features(sp, track_id: str) -> Optional[List[float]]:
    """Get audio features for a single track with error handling"""
    try:
        features = sp.audio_features([track_id])
        if features and features[0]:
            return [
                features[0]['danceability'],
                features[0]['energy'],
                features[0]['loudness'] / 100,  # Normalize loudness
                features[0]['speechiness'],
                features[0]['acousticness'],
                features[0]['instrumentalness'],
                features[0]['liveness'],
                features[0]['valence'],
                features[0]['tempo'] / 200  # Normalize tempo
            ]
    except Exception as e:
        st.warning(f"Could not get audio features for track {track_id}: {str(e)}")
    return None

def search_track(sp, query: str) -> Optional[Dict]:
    """Search for a track with error handling"""
    try:
        results = sp.search(q=query, limit=1, type='track')
        if results['tracks']['items']:
            return results['tracks']['items'][0]
    except Exception as e:
        st.error(f"Error searching for track '{query}': {str(e)}")
    return None

def get_enhanced_similar_tracks(sp, seed_track: Dict, eclectic_factor: float, num_songs: int) -> List[Dict]:
    """Enhanced similarity search with diverse strategies and eclectic control"""
    
    artist_name = seed_track['artists'][0]['name']
    track_name = seed_track['name']
    album_name = seed_track['album']['name'] if seed_track['album'] else ""
    
    all_tracks = []
    
    st.info(f"🔍 Finding songs similar to '{track_name}' by {artist_name}...")
    
    # Different search strategies with varying similarity levels
    search_strategies = [
        # Most similar (same artist)
        {"query": f"artist:{artist_name}", "weight": 1.0, "limit": max(5, num_songs // 4)},
        
        # Similar artists (extract artist keywords)
        {"query": artist_name.split()[0] if len(artist_name.split()) > 1 else artist_name, 
         "weight": 0.8, "limit": max(10, num_songs // 3)},
        
        # Album-based similarity
        {"query": f'album:"{album_name}"' if album_name else f"artist:{artist_name}", 
         "weight": 0.9, "limit": max(5, num_songs // 5)},
        
        # Genre-based (try to detect genre from track)
        {"query": f"genre:pop year:2020-2024", "weight": 0.6, "limit": max(15, num_songs // 2)},
        
        # Year-based similarity (if available)
        {"query": f"year:{seed_track['album']['release_date'][:4]}" if seed_track['album'] and seed_track['album'].get('release_date') else "popular", 
         "weight": 0.7, "limit": max(10, num_songs // 3)},
        
        # Broader musical exploration
        {"query": f"{track_name.split()[0]} music", "weight": 0.5, "limit": max(20, num_songs)},
    ]
    
    # Adjust strategy weights based on eclectic factor
    for strategy in search_strategies:
        # Higher eclectic factor = more weight on diverse searches
        if strategy["weight"] < 0.8:
            strategy["weight"] = strategy["weight"] + (eclectic_factor * 0.4)
        else:
            strategy["weight"] = strategy["weight"] - (eclectic_factor * 0.3)
    
    try:
        for strategy in search_strategies:
            try:
                results = sp.search(q=strategy["query"], type='track', 
                                  limit=strategy["limit"], market='US')
                
                if results['tracks']['items']:
                    # Filter out the original song and add weighted tracks
                    filtered_tracks = [
                        {**track, 'similarity_weight': strategy["weight"]}
                        for track in results['tracks']['items'] 
                        if track['id'] != seed_track['id']
                    ]
                    all_tracks.extend(filtered_tracks)
                    
            except Exception:
                continue
        
        # Remove duplicates while preserving highest weight
        track_dict = {}
        for track in all_tracks:
            track_id = track['id']
            if track_id not in track_dict or track['similarity_weight'] > track_dict[track_id]['similarity_weight']:
                track_dict[track_id] = track
        
        unique_tracks = list(track_dict.values())
        
        # Sort by similarity weight and eclectic factor
        if eclectic_factor > 0.5:
            # More eclectic = more randomization
            import random
            random.shuffle(unique_tracks)
            # But still prefer some similar tracks
            similar_tracks = [t for t in unique_tracks if t['similarity_weight'] > 0.7]
            diverse_tracks = [t for t in unique_tracks if t['similarity_weight'] <= 0.7]
            
            similar_count = int(num_songs * (1 - eclectic_factor))
            diverse_count = num_songs - similar_count
            
            final_tracks = similar_tracks[:similar_count] + diverse_tracks[:diverse_count]
        else:
            # Less eclectic = more similar tracks
            unique_tracks.sort(key=lambda x: x['similarity_weight'], reverse=True)
            final_tracks = unique_tracks[:num_songs]
        
        # Clean up the similarity_weight field
        for track in final_tracks:
            if 'similarity_weight' in track:
                del track['similarity_weight']
        
        if final_tracks:
            st.success(f"✅ Found {len(final_tracks)} tracks with {int(eclectic_factor*100)}% eclecticism!")
            return final_tracks
        else:
            st.warning("Could not find similar tracks. Try a different base song.")
            return []
            
    except Exception as e:
        st.error(f"Enhanced search failed: {str(e)}")
        return []

def get_recommendations_by_base_song(sp, base_song: str, eclectic_factor: float, num_songs: int) -> List[Dict]:
    """Get recommendations based on a base song using enhanced similarity"""
    seed_track = search_track(sp, base_song)
    if not seed_track:
        return []
    
    # Check if recommendations API is available
    try:
        test_rec = sp.recommendations(seed_tracks=[seed_track['id']], limit=1, market='US')
        api_available = True
        
        # If API is available and eclectic factor is low, use it for better similarity
        if eclectic_factor < 0.3:
            seed_features = get_audio_features(sp, seed_track['id'])
            if seed_features:
                recommendations = sp.recommendations(seed_tracks=[seed_track['id']], 
                                                   limit=min(50, num_songs * 2), market='US')
                tracks = recommendations['tracks']
                
                # Apply eclectic factor to similarity scoring
                seed_vector = np.array(seed_features).reshape(1, -1)
                track_features = []
                valid_tracks = []
                
                for track in tracks:
                    features = get_audio_features(sp, track['id'])
                    if features:
                        track_features.append(features)
                        valid_tracks.append(track)
                
                if track_features:
                    similarities = cosine_similarity(seed_vector, np.array(track_features)).flatten()
                    
                    # Apply eclectic factor to similarity threshold
                    similarity_threshold = 0.8 - (eclectic_factor * 0.5)
                    
                    # Sort by similarity but add some randomness based on eclectic factor
                    if eclectic_factor > 0.1:
                        # Add some randomness
                        noise = np.random.normal(0, eclectic_factor * 0.2, len(similarities))
                        adjusted_similarities = similarities + noise
                        top_indices = adjusted_similarities.argsort()[-num_songs:][::-1]
                    else:
                        top_indices = similarities.argsort()[-num_songs:][::-1]
                    
                    recommended_tracks = [valid_tracks[i] for i in top_indices]
                    return recommended_tracks
                    
    except spotipy.exceptions.SpotifyException:
        api_available = False
    
    # Use enhanced search-based method
    return get_enhanced_similar_tracks(sp, seed_track, eclectic_factor, num_songs)

def get_recommendations_by_mood_genre(sp, mood: str, genre: str, num_songs: int) -> List[Dict]:
    """Get recommendations based on mood and genre - with fallback for Development mode"""
    
    # Check if we can access recommendations API
    try:
        test_rec = sp.recommendations(seed_genres=["pop"], limit=1, market='US')
        api_available = True
    except spotipy.exceptions.SpotifyException as e:
        if "404" in str(e) or "not found" in str(e).lower():
            st.warning("⚠️ **Development Mode Limitation**: Using search-based recommendations.")
            api_available = False
        else:
            api_available = False
    
    if not api_available:
        return get_recommendations_via_search(sp, mood, genre, num_songs)
    
    # If API is available, use normal recommendations
    mood_targets = {
        "Happy": {"target_valence": 0.8, "target_energy": 0.7},
        "Sad": {"target_valence": 0.2, "target_energy": 0.3},
        "Energetic": {"target_energy": 0.9, "target_danceability": 0.8},
        "Relaxed": {"target_energy": 0.3, "target_valence": 0.6},
        "Romantic": {"target_valence": 0.7, "target_acousticness": 0.5}
    }
    
    target_params = mood_targets.get(mood, {})
    
    try:
        recommendations = sp.recommendations(
            seed_genres=[genre],
            limit=num_songs,
            market='US',
            **target_params
        )
        return recommendations['tracks']
    
    except spotipy.exceptions.SpotifyException:
        return get_recommendations_via_search(sp, mood, genre, num_songs)

def get_recommendations_via_search(sp, mood: str, genre: str, num_songs: int) -> List[Dict]:
    """Fallback method using search when recommendations API is unavailable"""
    
    mood_terms = {
        "Happy": ["upbeat", "cheerful", "joyful", "bright", "positive"],
        "Sad": ["melancholy", "emotional", "heartbreak", "lonely", "blue"],
        "Energetic": ["high energy", "pump up", "workout", "intense", "powerful"],
        "Relaxed": ["chill", "mellow", "calm", "peaceful", "smooth"],
        "Romantic": ["love", "romantic", "tender", "sweet", "intimate"]
    }
    
    genre_terms = {
        "k-pop": ["korean pop", "kpop", "korean music", "hallyu"],
        "j-pop": ["japanese pop", "jpop", "japanese music"],
        "pop": ["pop music", "popular"],
        "rock": ["rock music", "guitar"],
        "hip-hop": ["rap", "hip hop", "urban"],
        "jazz": ["jazz music", "smooth jazz"],
        "classical": ["classical music", "orchestra"],
        "electronic": ["edm", "electronic dance", "techno"],
        "country": ["country music", "americana"],
        "r-n-b": ["rnb", "soul", "rhythm and blues"]
    }
    
    search_terms = mood_terms.get(mood, ["music"])
    genre_search = genre_terms.get(genre, [genre])
    
    all_tracks = []
    
    st.info(f"🔍 Searching for {mood.lower()} {genre} songs...")
    
    try:
        for mood_term in search_terms[:3]:
            for genre_term in genre_search[:2]:
                query = f"{mood_term} {genre_term}"
                
                try:
                    results = sp.search(q=query, type='track', limit=15, market='US')
                    if results['tracks']['items']:
                        all_tracks.extend(results['tracks']['items'])
                        
                except Exception:
                    continue
        
        # Remove duplicates and limit results
        seen_ids = set()
        unique_tracks = []
        for track in all_tracks:
            if track['id'] not in seen_ids:
                seen_ids.add(track['id'])
                unique_tracks.append(track)
                if len(unique_tracks) >= num_songs:
                    break
        
        return unique_tracks[:num_songs]
            
    except Exception as e:
        st.error(f"Search failed: {str(e)}")
        return []

def create_spotify_playlist(sp, tracks: List[Dict], playlist_name: str) -> Optional[str]:
    """Create a playlist on Spotify (requires user authentication)"""
    try:
        # This would require SpotifyOAuth instead of ClientCredentials
        # For now, return None to indicate feature unavailable
        return None
    except Exception as e:
        st.error(f"Error creating Spotify playlist: {str(e)}")
        return None

def display_track(track: Dict, index: int):
    """Display a single track with enhanced two-column layout"""
    track_name = track['name']
    artist_name = track['artists'][0]['name']
    album_name = track['album']['name'] if track['album'] else "Unknown Album"
    track_url = track['external_urls']['spotify']
    track_id = track['id']
    
    with st.container():
        st.markdown('<div class="track-container">', unsafe_allow_html=True)
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.markdown(f"""
                <div class="track-info">
                    <h4 class="track-title">{index + 1}. {track_name}</h4>
                    <p class="track-artist">by {artist_name}</p>
                    <p style="color: #8b9dc3; font-size: 12px; margin: 5px 0 0 0;">
                        Album: {album_name}
                    </p>
                    <p style="margin-top: 10px;">
                        <a href="{track_url}" target="_blank" style="color: #1DB954; text-decoration: none;">
                            🎵 Open in Spotify
                        </a>
                    </p>
                </div>
            """, unsafe_allow_html=True)
        
        with col2:
            try:
                st.markdown(
                    f'<iframe src="https://open.spotify.com/embed/track/{track_id}" '
                    f'width="100%" height="152" frameborder="0" allowtransparency="true" '
                    f'allow="encrypted-media" style="border-radius: 12px;"></iframe>',
                    unsafe_allow_html=True
                )
            except Exception:
                st.markdown(f"""
                    <div style="background: #191414; border-radius: 12px; padding: 40px; text-align: center; color: #1DB954;">
                        <p>🎵 Preview not available</p>
                        <a href="{track_url}" target="_blank" style="color: #1DB954;">Listen on Spotify</a>
                    </div>
                """, unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)

def main():
    # Sidebar for debugging
    with st.sidebar:
        st.header("🔧 Debug Info")
        
        if st.button("🔍 Test Credentials"):
            try:
                client_id, client_secret = get_spotify_credentials()
                st.success("✅ Credentials loaded successfully")
                
                test_sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(
                    client_id=client_id,
                    client_secret=client_secret
                ))
                
                result = test_sp.search(q="hello", limit=1, type='track')
                if result and result['tracks']['items']:
                    st.success("✅ API connection successful!")
                    track = result['tracks']['items'][0]
                    st.info(f"Test track: {track['name']} by {track['artists'][0]['name']}")
                else:
                    st.warning("⚠️ API connected but returned no results")
                    
            except Exception as e:
                st.error(f"❌ Test failed: {str(e)}")
        
        st.markdown("---")
        st.markdown("**Need help?**")
        st.markdown("- Check your [Spotify Dashboard](https://developer.spotify.com/dashboard)")
        st.markdown("- Make sure credentials are 32 characters each")
        st.markdown("- Try regenerating your Client Secret")
    
    # Initialize Spotify client
    sp = initialize_spotify_client()
    
    # Header
    st.markdown("""
        <div class="main-header">
            <h1>🎵 Advanced Spotify Playlist Generator</h1>
            <p style="margin: 0; opacity: 0.8;">Create personalized playlists with precision control!</p>
        </div>
    """, unsafe_allow_html=True)
    
    # Development mode notice
    if hasattr(st.session_state, 'dev_mode_detected') and st.session_state.dev_mode_detected:
        st.info("""
        ℹ️ **Development Mode**: Your app is in Development mode. Some features use search-based alternatives 
        instead of Spotify's recommendations API. For full functionality, consider requesting Extended Quota mode.
        """)
    
    # Main input section
    st.markdown("### 🎛️ Playlist Configuration")
    
    # Create three columns for inputs
    col1, col2, col3 = st.columns(3)
    
    with col1:
        mood = st.selectbox(
            "🎭 Select a mood:",
            ["Happy", "Sad", "Energetic", "Relaxed", "Romantic"],
            help="Choose how you're feeling or want to feel"
        )
        
        genre = st.selectbox(
            "🎸 Select a genre:",
            VALID_GENRES,
            help="Pick your favorite music genre"
        )
    
    with col2:
        num_songs = st.number_input(
            "📊 Number of songs:",
            min_value=5,
            max_value=50,
            value=25,
            step=5,
            help="How many songs do you want in your playlist?"
        )
        
        base_song = st.text_input(
            "🎵 Base song (optional):",
            placeholder="e.g., 'Bohemian Rhapsody Queen'",
            help="Enter a song name and artist to get similar recommendations"
        )
    
    with col3:
        st.markdown("#### 🎲 Eclecticism Control")
        eclectic_factor = st.slider(
            "Variety Level:",
            min_value=0.0,
            max_value=1.0,
            value=0.3,
            step=0.1,
            help="0 = Very similar songs, 1 = Very diverse playlist"
        )
        
        # Visual indicator for eclecticism
        if eclectic_factor <= 0.3:
            st.markdown("🎯 **Similar** - Consistent vibe")
        elif eclectic_factor <= 0.6:
            st.markdown("🌈 **Balanced** - Mix of similar & diverse")
        else:
            st.markdown("🎲 **Eclectic** - Surprising variety")
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Generate button
    if st.button("🎧 Generate My Playlist", type="primary"):
        if not base_song and (not mood or not genre):
            st.error("❌ Please select a mood and genre OR provide a base song.")
            return
        
        with st.spinner("🎶 Creating your perfect playlist..."):
            if base_song:
                st.info(f"🎯 Finding songs similar to: **{base_song}** (Variety: {int(eclectic_factor*100)}%)")
                tracks = get_recommendations_by_base_song(sp, base_song, eclectic_factor, num_songs)
            else:
                st.info(f"🎯 Finding **{mood.lower()}** songs in **{genre}** genre")
                tracks = get_recommendations_by_mood_genre(sp, mood, genre, num_songs)
        
        if tracks:
            st.success(f"✅ Generated playlist with {len(tracks)} awesome tracks!")
            
            # Playlist title suggestion
            if base_song:
                playlist_name = f"Similar to {base_song.split()[0]}..."
            else:
                playlist_name = f"{mood} {genre.title()} Mix"
            
            st.markdown(f"### 🎵 Your Playlist: **{playlist_name}**")
            
            # Display tracks
            playlist_data = []
            for i, track in enumerate(tracks):
                display_track(track, i)
                
                playlist_data.append({
                    "Track": track['name'],
                    "Artist": track['artists'][0]['name'],
                    "Album": track['album']['name'] if track['album'] else "Unknown",
                    "Spotify URL": track['external_urls']['spotify'],
                    "Track ID": track['id']
                })
            
            # Export section
            st.markdown("""
                <div class="download-section">
                    <h3 style="color: #1DB954; margin-top: 0;">📥 Export Your Playlist</h3>
                </div>
            """, unsafe_allow_html=True)
            
            col1, col2 = st.columns(2)
            
            with col1:
                # CSV Download
                df = pd.DataFrame(playlist_data)
                csv_data = df.to_csv(index=False)
                
                filename = f"spotify_playlist_{mood}_{genre}.csv" if not base_song else f"playlist_similar_to_{base_song.replace(' ', '_')}.csv"
                
                st.download_button(
                    label="📊 Download as CSV",
                    data=csv_data,
                    file_name=filename,
                    mime="text/csv",
                    help="Download your playlist to save or import into other music apps!",
                    use_container_width=True
                )
            
            with col2:
                # Spotify Export (placeholder for future implementation)
                st.markdown("""
                    <div class="spotify-export">
                        <h4 style="color: #1DB954; margin-top: 0;">🎵 Export to Spotify</h4>
                        <p style="margin-bottom: 10px;">Direct Spotify playlist creation coming soon!</p>
                        <p style="font-size: 12px; opacity: 0.7;">
                            For now, use the CSV file or manually add songs to your Spotify playlist.
                        </p>
                    </div>
                """, unsafe_allow_html=True)
                
                # Future implementation button (disabled for now)
                if st.button("🚀 Create Spotify Playlist", disabled=True, help="Feature coming soon - requires user authentication"):
                    st.info("This feature requires Spotify user authentication and will be available in a future update!")
            
            # Additional playlist info
            st.markdown("---")
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("📊 Total Tracks", len(tracks))
            
            with col2:
                total_duration = sum([track.get('duration_ms', 0) for track in tracks]) / 1000 / 60
                st.metric("⏱️ Duration", f"{total_duration:.0f} min")
            
            with col3:
                unique_artists = len(set([track['artists'][0]['name'] for track in tracks]))
                st.metric("🎤 Unique Artists", unique_artists)
            
        else:
            st.error("😔 No recommendations found. Please try different parameters.")
            st.markdown("""
            ### 💡 **Troubleshooting Tips:**
            - Try a different genre or mood combination
            - Check your base song spelling and include the artist name
            - Increase the eclecticism slider for more variety
            - Reduce the number of songs if you're having trouble
            """)

if __name__ == "__main__":
    main()