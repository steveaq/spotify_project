import streamlit as st
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

# Spotify API credentials
SPOTIPY_CLIENT_ID = 'db92830dca624bb99e5e383038329699'
SPOTIPY_CLIENT_SECRET = '8333de6242494266b8d8f32c08c5cadd'


# Initialize Spotipy client
sp = spotipy.Spotify(auth_manager=SpotifyClientCredentials(client_id=SPOTIPY_CLIENT_ID,
                                                           client_secret=SPOTIPY_CLIENT_SECRET))

# Streamlit app
st.set_page_config(page_title="🎵 Spotify Playlist Generator", page_icon="🎧", layout="centered")

# Custom CSS for navy background and Apple-like design
st.markdown("""
    <style>
    .stApp {
        background-color: #001f3f; /* Navy background */
        color: #ffffff; /* White text */
        font-family: -apple-system, BlinkMacSystemFont, sans-serif;
    }
    h1, h2, h3, h4, h5, h6 {
        color: #ffffff; /* White text for headings */
    }
    .stButton button {
        background-color: #007aff; /* Apple blue */
        color: white;
        border-radius: 20px;
        padding: 10px 20px;
        font-size: 16px;
    }
    .stSelectbox, .stTextInput {
        background-color: #ffffff; /* White background for inputs */
        border-radius: 10px;
        padding: 10px;
    }
    .stMarkdown {
        color: #ffffff; /* White text for markdown */
    }
    </style>
    """, unsafe_allow_html=True)

st.title("🎵 Spotify Playlist Generator")
st.write("Select a mood, genre, or provide a base song to generate a playlist!")

# Mood and genre selection
mood = st.selectbox("Select a mood:", ["Happy", "Sad", "Energetic", "Relaxed", "Romantic"])

# Valid Spotify seed genres
valid_genres = [
    "pop", "rock", "hip-hop", "jazz", "classical", "electronic", "indie", "reggae", "blues", "country", "metal", "r&b", "edm"
]
genre = st.selectbox("Select a genre:", valid_genres)

# Base song input
base_song = st.text_input("Or enter a base song (optional):")

# Function to get audio features for a track
def get_audio_features(track_id):
    features = sp.audio_features(track_id)[0]
    return [
        features['danceability'],
        features['energy'],
        features['loudness'],
        features['speechiness'],
        features['acousticness'],
        features['instrumentalness'],
        features['liveness'],
        features['valence'],
        features['tempo']
    ]

# Function to get recommendations using cosine similarity
def get_recommendations(mood, genre, base_song=None):
    if base_song:
        # Search for the base song
        results = sp.search(q=base_song, limit=1, type='track')
        if results['tracks']['items']:
            seed_track = results['tracks']['items'][0]
            seed_track_id = seed_track['id']
            seed_track_features = np.array(get_audio_features(seed_track_id)).reshape(1, -1)

            # Get similar tracks using cosine similarity
            recommendations = sp.recommendations(seed_tracks=[seed_track_id], limit=50, market='US')
            tracks = recommendations['tracks']

            # Calculate cosine similarity for each track
            track_features = []
            for track in tracks:
                track_id = track['id']
                features = get_audio_features(track_id)
                track_features.append(features)

            track_features = np.array(track_features)
            similarities = cosine_similarity(seed_track_features, track_features).flatten()
            top_indices = similarities.argsort()[-10:][::-1]  # Top 10 similar tracks
            recommended_tracks = [tracks[i] for i in top_indices]

            return recommended_tracks
        else:
            st.error("Base song not found. Please try again.")
            return []
    else:
        # Use mood and genre to get recommendations
        target_energy = 0.5  # Default energy level
        # if mood == "Happy":
        #     target_energy = 0.8
        # elif mood == "Sad":
        #     target_energy = 0.3
        # elif mood == "Energetic":
        #     target_energy = 0.9
        # elif mood == "Relaxed":
        #     target_energy = 0.4
        # elif mood == "Romantic":
        #     target_energy = 0.6

        # Ensure genre is valid
        if genre not in valid_genres:
            st.error(f"Invalid genre: {genre}. Please select a valid genre.")
            return []

        # Use target_energy as part of the target_audio_features
        recommendations = sp.recommendations(seed_genres=[genre], limit=10, target_energy=target_energy, market='US')
        return recommendations['tracks']

# Generate playlist button
if st.button("Generate Playlist"):
    if not base_song and (not mood or not genre):
        st.error("Please select a mood and genre or provide a base song.")
    else:
        st.write("🎧 Generating your playlist...")
        tracks = get_recommendations(mood, genre, base_song)

        if tracks:
            st.write("### Your Playlist:")
            playlist = []
            for track in tracks:
                track_name = track['name']
                artist_name = track['artists'][0]['name']
                track_url = track['external_urls']['spotify']
                track_id = track['id']
                playlist.append({"Track": track_name, "Artist": artist_name, "URL": track_url})

                # Embed Spotify player
                st.write(f"**{track_name}** by **{artist_name}**")
                st.markdown(f'<iframe src="https://open.spotify.com/embed/track/{track_id}" width="300" height="80" frameborder="0" allowtransparency="true" allow="encrypted-media"></iframe>', unsafe_allow_html=True)

            # Save playlist to a CSV file
            df = pd.DataFrame(playlist)
            df.to_csv("generated_playlist.csv", index=False)
            st.success("Playlist generated and saved as 'generated_playlist.csv'!")
        else:
            st.error("No recommendations found. Please try again.")