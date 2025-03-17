from spotipy.oauth2 import SpotifyOAuth
import spotipy

SPOTIPY_CLIENT_ID = "db92830dca624bb99e5e383038329699"
SPOTIPY_CLIENT_SECRET = "8333de6242494266b8d8f32c08c5cadd"
SPOTIPY_REDIRECT_URI = "http://localhost:8888/callback"

scope = "user-library-read"

# Authenticate with OAuth
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(client_id=SPOTIPY_CLIENT_ID,
                                               client_secret=SPOTIPY_CLIENT_SECRET,
                                               redirect_uri=SPOTIPY_REDIRECT_URI,
                                               scope=scope))

# Test a track ID
track_id = "11dFghVXANMlKmJXsNCbNl"
features = sp.audio_features([track_id])
print(features)
