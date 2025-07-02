import spotipy
from spotipy.oauth2 import SpotifyOAuth

SPOTIPY_CLIENT_ID = "db92830dca624bb99e5e383038329699"
SPOTIPY_CLIENT_SECRET = "8333de6242494266b8d8f32c08c5cadd"
SPOTIPY_REDIRECT_URI = "http://localhost:8888/callback"

sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    client_id=SPOTIPY_CLIENT_ID,
    client_secret=SPOTIPY_CLIENT_SECRET,
    redirect_uri=SPOTIPY_REDIRECT_URI,
    scope="user-library-read"
))

params = {
    "limit": 10,
    "seed_genres": ["samba"],
    "market": "US"  # Optional but helps
}

try:
    recs = sp.recommendations(**params)
    print("✅ Recommendations received:\n")
    for track in recs['tracks']:
        print(f"{track['name']} - {track['artists'][0]['name']}")
except spotipy.exceptions.SpotifyException as e:
    print("❌ Spotify error:", e)
