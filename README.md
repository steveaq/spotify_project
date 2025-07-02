# Spotify Playlist Generator 🎵

A Streamlit-based web app that generates personalized Spotify playlists based on user-selected mood, genre, or a base song. The app uses the Spotify API to fetch song data, calculates cosine similarity for recommendations, and allows users to preview songs directly in the app.

---

## Features ✨

- **Mood-Based Playlists**: Select a mood (e.g., Happy, Sad, Energetic) to generate a playlist.
- **Genre-Based Playlists**: Choose from a variety of genres (e.g., Pop, Rock, Jazz, Deep House).
- **Base Song Recommendations**: Enter a base song, and the app will recommend similar tracks using cosine similarity.
- **Embedded Spotify Player**: Preview recommended songs directly in the app.
- **Download Playlist**: Save the generated playlist as a CSV file.

---

## Tech Stack 🛠️

- **Python**: Primary programming language.
- **Streamlit**: For building the web app interface.
- **Spotify API**: To fetch song data and generate recommendations.
- **Spotipy**: A lightweight Python library for the Spotify Web API.
- **Scikit-learn**: For calculating cosine similarity between songs.
- **Pandas**: For data manipulation and saving playlists as CSV files.

---

## Prerequisites 📋

Before running the app, ensure you have the following:

1. **Spotify Developer Account**:
   - Create an account on the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard/applications).
   - Register a new app to get your `Client ID` and `Client Secret`.

2. **Python 3.8+**: Ensure Python is installed on your system.

3. **Required Libraries**:
   Install the required Python libraries using the following command:
   ```bash
   pip install streamlit spotipy pandas scikit-learn
