"""Side A — a personal playlist studio, built with Streamlit."""
import html
import hashlib
import os
import re
import time
from pathlib import Path
from urllib.parse import urlparse

import spotipy
import streamlit as st
from genres import VALID_GENRES
from spotify_service import MOODS, make_client, playlist_csv, recommend, safe_filename, sample_tracks

st.set_page_config(page_title="Side A · Your playlist studio", page_icon="◉", layout="wide",
                   initial_sidebar_state="collapsed")
st.markdown(f"<style>{Path(__file__).with_name('styles.css').read_text()}</style>", unsafe_allow_html=True)


def markup(content):
    st.markdown(content, unsafe_allow_html=True)


def credentials():
    values = []
    secret_paths = st.get_option("secrets.files") or []
    has_secrets = any(Path(p).expanduser().exists() for p in secret_paths)
    for key in ("SPOTIPY_CLIENT_ID", "SPOTIPY_CLIENT_SECRET"):
        value = os.getenv(key, "")
        if not value and has_secrets:
            try:
                value = st.secrets.get(key, "")
            except (FileNotFoundError, getattr(st.errors, "StreamlitSecretNotFoundError", FileNotFoundError)):
                pass
        values.append(str(value).strip().strip("\"'"))
    return values


@st.cache_resource(ttl=3300, show_spinner=False)
def spotify_client(client_id, client_secret):
    return make_client(client_id, client_secret)


@st.cache_data(ttl=300, max_entries=128, show_spinner=False)
def cached_mix(_client, credential_key, mood, genre, count, song, variety, market, extended):
    # The credential fingerprint isolates caches across configured Spotify apps.
    return recommend(_client, mood, genre, count, song, variety, market=market,
                     use_recommendations=extended)


def esc(value):
    return html.escape(str(value), quote=True)


def spotify_id(track):
    value = str(track.get("id", ""))
    return value if re.fullmatch(r"[A-Za-z0-9]{22}", value) else None


def track_row(track, index):
    artists = ", ".join(a["name"] for a in track.get("artists", []))
    album = track.get("album") or {}
    images = album.get("images", [])
    image = images[-1].get("url", "") if images else ""
    # Only Spotify's image host is used for external artwork.
    if urlparse(image).scheme == "https" and urlparse(image).hostname == "i.scdn.co":
        art = f'<img class="track-art" src="{esc(image)}" alt="{esc(album.get("name", "Album artwork"))}" loading="lazy">'
    else:
        art = f'<span class="track-art art-{index % 5}" aria-hidden="true">◉</span>'
    seconds = int(track.get("duration_ms", 0)) // 1000
    tid = spotify_id(track)
    link = f'<a class="track-open" href="https://open.spotify.com/track/{tid}" target="_blank" rel="noopener noreferrer" aria-label="Open {esc(track["name"])} in Spotify">↗</a>' if tid else ""
    markup(f'<div class="track-row"><span class="track-number">{index + 1:02}</span>{art}'
           f'<div class="track-copy"><strong>{esc(track["name"])}</strong><span>{esc(artists)}</span></div>'
           f'<span class="track-album">{esc(album.get("name", ""))}</span>'
           f'<span class="track-duration">{seconds // 60}:{seconds % 60:02}</span>{link}</div>')


def apply_preset(mood, genre):
    st.session_state.mood = mood
    st.session_state.genre = genre
    st.session_state.mode = "By mood"


def main():
    for key, value in {"mood": "Relaxed", "genre": "indie", "mode": "By mood", "tracks": [],
                       "mix_name": "", "mix_note": "", "sample": False}.items():
        st.session_state.setdefault(key, value)
    client_id, client_secret = credentials()
    configured = bool(client_id and client_secret)
    markup('<nav class="masthead" aria-label="Brand"><div class="brand"><span class="brand-icon">◉</span>'
           'side a<span class="brand-divider"></span><span class="brand-caption">YOUR PLAYLIST STUDIO</span></div>'
           '<a href="#your-mix" class="nav-link">Your mix <span>↗</span></a></nav>')
    markup('''<section class="hero" aria-labelledby="hero-title">
        <div class="hero-copy"><div class="eyebrow"><span class="live-dot"></span> A LITTLE LESS SCROLLING. A LOT MORE LISTENING.</div>
        <h1 id="hero-title">Life has a mood.<br>Give it a <em>soundtrack.</em></h1>
        <p>Start with a feeling or a song you love.<br>Find your next on-repeat playlist.</p>
        <div class="hero-foot"><span>CURATED AROUND YOU</span><span>↓ &nbsp; FIND YOUR FREQUENCY</span></div></div>
        <div class="record-scene" role="img" aria-label="An illustrated vinyl record with a lime green sleeve">
        <div class="record"><div class="record-label">SIDE A<br><b>33⅓</b><i></i></div></div>
        <div class="sleeve"><span>GOOD MUSIC.<br>YOUR WAY.</span><div class="sleeve-symbol">a</div><small>THE PERSONAL COLLECTION &nbsp; / &nbsp; VOL. 01</small></div>
        <span class="scene-note">MADE FOR THE WAY YOU FEEL.</span></div></section>''')

    heading, status = st.columns([3, 1])
    with heading:
        markup('<div class="section-heading"><span class="step">01 /</span><h2>Find your frequency</h2></div>')
    with status:
        markup(f'<div class="connection"><span class="live-dot {"" if configured else "offline"}"></span>'
               f'{"Spotify configured" if configured else "Explore the studio"}</div>')

    builder, guide = st.columns([2.1, 1], gap="large")
    with builder:
        with st.container(border=True):
            mode = st.radio("Start your mix", ["By mood", "From a song"], horizontal=True, key="mode")
            if mode == "From a song":
                song = st.text_input("A song you love", placeholder="e.g. Pink + White — Frank Ocean", key="seed")
                st.caption("Include the artist for a closer match.")
            else:
                song = ""
            first, second = st.columns(2)
            with first:
                mood = st.selectbox("The feeling", list(MOODS), key="mood",
                                    format_func=lambda m: f"{m} · {MOODS[m][0]}")
            with second:
                genre = st.selectbox("The sound", VALID_GENRES, key="genre", format_func=lambda g: g.replace("-", " ").title())
            size, diversity = st.columns([1, 1.5])
            with size:
                count = st.select_slider("Tracks in your mix", options=[5, 10, 15, 20, 25, 30, 40, 50], value=20)
            with diversity:
                variety = st.slider("Discovery level", 0, 100, 30, 10, disabled=mode == "By mood",
                                    help="For song-based mixes: blend familiar artists with broader discoveries.")
            st.caption("Familiar sounds ← → New territory" if mode == "From a song" else "Mood and genre shape this mix. Switch to ‘From a song’ to tune discovery.")
            generate = st.button("Make my mix  ↗", type="primary", use_container_width=True)
            st.caption("Real tracks. Fresh possibilities. Yours to explore.")
    with guide:
        markup('''<aside class="studio-note"><span class="eyebrow">THE LISTENING ROOM</span>
            <h3>A good mix starts<br>with a feeling.</h3><p>Set the mood, pick your sound, and leave a little room for discovery.</p>
            <div class="note-rule"></div><div class="note-step"><span>01</span> Choose your starting point</div>
            <div class="note-step"><span>02</span> Make it your own</div><div class="note-step"><span>03</span> Find something worth replaying</div>
            <div class="note-bottom">YOUR NEXT FAVOURITE IS OUT THERE. &nbsp; ✳</div></aside>''')

    if generate:
        if mode == "From a song" and not song.strip():
            st.warning("Add a song and artist to start your mix.")
        elif not configured:
            st.info("Add your Spotify credentials in Connection & help below, or explore the example mix.")
        elif time.time() < st.session_state.get("retry_at", 0):
            wait = max(1, int(st.session_state.retry_at - time.time()))
            st.warning(f"Spotify asked us to pause. Try again in {wait} seconds.")
        else:
            with st.spinner("Finding your frequency…"):
                try:
                    credential_key = hashlib.sha256(f"{client_id}:{client_secret}".encode()).hexdigest()
                    market = os.getenv("SPOTIFY_MARKET", "GB").upper()
                    extended = os.getenv("SPOTIFY_USE_RECOMMENDATIONS", "false").lower() == "true"
                    tracks, note = cached_mix(spotify_client(client_id, client_secret), credential_key,
                        mood, genre, count, song.strip(), variety / 100, market, extended)
                    if tracks:
                        st.session_state.update(tracks=tracks, sample=False, mix_note=note,
                            mix_name=f"After {song.strip()}" if song else f"{mood} / {genre.replace('-', ' ').title()}",
                            requested=count)
                    else:
                        st.warning(note if song else "No tracks found for this combination. Try another sound or feeling.")
                except spotipy.SpotifyException as exc:
                    messages = {401: "Spotify could not authenticate. Check your credentials in Connection & help.",
                        403: "Spotify denied catalog access. Check the app owner’s Premium subscription and Developer Dashboard access settings. Changing the mix will not fix this.",
                        429: "Spotify is busy. Please wait a moment before making another mix."}
                    st.error(messages.get(exc.http_status, "Spotify is unavailable right now. Try again shortly."))
                    if exc.http_status == 429:
                        try:
                            delay = max(30, int((exc.headers or {}).get("Retry-After", 60)))
                        except (ValueError, TypeError):
                            delay = 60
                        st.session_state.retry_at = time.time() + delay
                except spotipy.oauth2.SpotifyOauthError:
                    st.error("Spotify rejected the app credentials. Update them in your hosting secrets and restart the app.")
                except ValueError:
                    st.error("The discovery settings are invalid. Check the genre and the SPOTIFY_MARKET country code.")
                except Exception:
                    st.error("We couldn’t reach Spotify. Check your connection and try again.")

    markup('<div class="starter-heading"><span>NEED A STARTING POINT?</span><span>PICK A MOOD, MAKE IT YOURS ↙</span></div>')
    presets = [("SUNLIT MORNINGS", "A brighter kind of day.", "Happy", "pop", "☀", "sun"),
               ("SLOW SUNDAY", "Nowhere to rush to.", "Relaxed", "indie", "≈", "slow"),
               ("AFTER HOURS", "Let the night unfold.", "Romantic", "r-n-b", "☾", "night")]
    for col, (title, description, pmood, pgenre, symbol, tone) in zip(st.columns(3), presets):
        with col:
            markup(f'<div class="preset {tone}"><span class="preset-symbol" aria-hidden="true">{symbol}</span>'
                   f'<span class="eyebrow">{title}</span><p>{description}</p></div>')
            st.button(f"Try {title.lower()}  ↗", key=tone, on_click=apply_preset, args=(pmood, pgenre), use_container_width=True)

    markup('<div id="your-mix" class="section-heading mix-heading"><span class="step">02 /</span><h2>Your next on-repeat</h2></div>')
    tracks = st.session_state.tracks
    if not tracks:
        with st.container(border=True):
            markup('<div class="empty-state"><span class="empty-record" aria-hidden="true">◉</span>'
                   '<div><h3>Something good is about to play.</h3><p>Your mix will land here. Start with a mood, or take a look at an example.</p></div></div>')
            if st.button("Explore an example mix  ↗"):
                st.session_state.update(tracks=sample_tracks(), sample=True, mix_name="A little of everything",
                    mix_note="Example mix · 5 hand-picked tracks to explore the studio. This is not a generated recommendation.")
                st.rerun()
    else:
        with st.container(border=True):
            title_col, export_col = st.columns([3, 1])
            with title_col:
                st.subheader(st.session_state.mix_name)
                minutes = round(sum(t.get("duration_ms", 0) for t in tracks) / 60000)
                artists = len({a["name"] for t in tracks for a in t.get("artists", [])})
                st.caption(f"{len(tracks)} tracks  ·  {minutes} min  ·  {artists} artists")
            with export_col:
                st.download_button("Download CSV ↓", playlist_csv(tracks), safe_filename(st.session_state.mix_name),
                                   mime="text/csv", use_container_width=True)
            st.caption(st.session_state.mix_note)
            if not st.session_state.sample and len(tracks) < st.session_state.get("requested", 0):
                st.info(f"Found {len(tracks)} unique tracks. Try a broader genre for a longer mix.")
            for i, track in enumerate(tracks):
                track_row(track, i)
            playable = [t for t in tracks if spotify_id(t)]
            if playable:
                with st.expander("Listen to a track"):
                    selected = st.selectbox("Choose a track to preview", range(len(playable)),
                        format_func=lambda i: f'{playable[i]["name"]} — {playable[i]["artists"][0]["name"]}')
                    tid = spotify_id(playable[selected])
                    markup(f'<iframe title="Spotify track player" src="https://open.spotify.com/embed/track/{tid}" '
                           'width="100%" height="152" frameborder="0" allow="autoplay; clipboard-write; encrypted-media; fullscreen; picture-in-picture" loading="lazy"></iframe>')
                    st.caption("Playback availability depends on Spotify and your region. You can also open each track in Spotify.")

    with st.expander("Connection & help"):
        st.markdown("**Connect your Spotify app**")
        st.write("Set SPOTIPY_CLIENT_ID and SPOTIPY_CLIENT_SECRET as environment variables, or in .streamlit/secrets.toml, then restart the app.")
        st.code('SPOTIPY_CLIENT_ID = "your_client_id"\nSPOTIPY_CLIENT_SECRET = "your_client_secret"', language="toml")
        st.markdown("Get credentials from your [Spotify Developer Dashboard](https://developer.spotify.com/dashboard).")
        st.caption("Your mix stays in this browser session. Download the CSV to keep it. Direct saving to your Spotify library is not available; open individual tracks to add them in Spotify.")
        st.caption("Identical successful mixes are cached for five minutes to reduce Spotify requests. Discovery ranks catalog metadata; it does not analyse audio or train a model. Search access is required even when credentials authenticate successfully.")
    markup('<footer><span><b>side a</b> &nbsp; A little discovery goes a long way.</span><span>INDEPENDENTLY BUILT · POWERED BY SPOTIFY</span></footer>')


if __name__ == "__main__":
    main()
