"""Spotify access and recommendation logic, independent of the interface."""
import csv
import io
import re
import math
from datetime import date
from collections import Counter

import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
from spotipy.cache_handler import MemoryCacheHandler


MOODS = {
    "Happy": ("Feel-good favourites", "upbeat", {"target_valence": .8, "target_energy": .7}),
    "Relaxed": ("Take it slow", "chill", {"target_energy": .3, "target_valence": .6}),
    "Energetic": ("Turn it up", "workout", {"target_energy": .9, "target_danceability": .8}),
    "Sad": ("Sit with the feeling", "melancholy", {"target_valence": .2, "target_energy": .3}),
    "Romantic": ("A little closer", "love", {"target_valence": .7, "target_acousticness": .5}),
}


def make_client(client_id, client_secret):
    return spotipy.Spotify(
        auth_manager=SpotifyClientCredentials(client_id=client_id, client_secret=client_secret, cache_handler=MemoryCacheHandler()),
        requests_timeout=12, retries=0, status_retries=0,
    )


# The default ranker uses catalog relevance and metadata, not a trained audio model.
# Keep mood keywords explicit: search cannot reliably infer how a song feels.
MOOD_TERMS = {
    "Happy": ("upbeat", "feel good"), "Relaxed": ("chill", "mellow"),
    "Energetic": ("workout", "energetic"), "Sad": ("melancholy", "sad"),
    "Romantic": ("love", "romantic"),
}


def normalized(value):
    return re.sub(r"[^\w]+", " ", str(value).casefold()).strip()


def recording_key(track):
    # Prefer the recording identifier; Spotify can list one recording on many albums.
    isrc = track.get("external_ids", {}).get("isrc")
    if isrc:
        return ("isrc", isrc.upper())
    title = re.sub(r"\s*[-(]\s*(?:\d{4}\s+)?remaster(?:ed)?[^)]*\)?", "", track.get("name", ""), flags=re.I)
    artists = tuple(sorted(normalized(a.get("name", "")) for a in track.get("artists", [])))
    return ("title", normalized(title), artists)


def eligible(track):
    return bool(track and re.fullmatch(r"[A-Za-z0-9]{22}", str(track.get("id", "")))
                and track.get("name") and track.get("artists")
                and not track.get("is_local") and track.get("is_playable") is not False)


def unique_tracks(tracks, exclude=None, seed=None):
    ids = {exclude} if exclude else set()
    recordings = {recording_key(seed)} if seed else set()
    result = []
    for track in tracks:
        if not eligible(track):
            continue
        key = recording_key(track)
        if track["id"] not in ids and key not in recordings:
            ids.add(track["id"])
            recordings.add(key)
            result.append(track)
    return result


def search_candidates(client, queries, count, market):
    """Bounded retrieval with ten-item pages and reciprocal-rank evidence.

    The same recording found by several searches gets stronger evidence, rather
    than whichever query happens to run first monopolising the final playlist.
    """
    candidates, evidence = {}, {}
    requests = 0
    max_requests = min(16, max(6, math.ceil(count / 10) * 3))
    exhausted = set()
    for offset in (0, 10, 20):
        for query, weight in queries:
            if requests >= max_requests:
                break
            if query in exhausted:
                continue
            requests += 1
            try:
                response = client.search(q=query, type="track", limit=10, offset=offset, market=market)
            except spotipy.SpotifyException as exc:
                if exc.http_status in (401, 403, 429):
                    raise
                # A rejected query is actionable; do not disguise server errors as no results.
                if exc.http_status == 400:
                    continue
                raise
            page = response.get("tracks", {})
            items = page.get("items", [])
            if len(items) < 10 or ("next" in page and page["next"] is None):
                exhausted.add(query)
            for rank, track in enumerate(items):
                if eligible(track):
                    tid = track["id"]
                    candidates[tid] = track
                    evidence[tid] = evidence.get(tid, 0.) + weight / (20 + offset + rank)
        if len(candidates) >= max(count * 2, 20) or requests >= max_requests or len(exhausted) == len(queries):
            break
    return list(candidates.values()), evidence


def artist_keys(track):
    return {a.get("id") or normalized(a.get("name", "")) for a in track.get("artists", [])}


def release_year(track):
    try:
        return int((track.get("album") or {}).get("release_date", "")[:4])
    except (ValueError, TypeError):
        return None


def rank_tracks(tracks, evidence, count, variety, seed=None):
    """Greedy relevance/diversity selection with a per-artist ceiling.

    Evidence is normalized to 0..1. Song mixes also use artist overlap and release
    proximity. Diversity penalises artists/albums already selected. Ties use IDs
    so identical requests produce reproducible results without random shuffling.
    """
    remaining = unique_tracks(tracks, seed.get("id") if seed else None, seed)
    if not remaining:
        return []
    scale = max(evidence.values(), default=1.) or 1.
    seed_artists = artist_keys(seed) if seed else set()
    seed_year = release_year(seed) if seed else None
    # Small pools still get a bounded ceiling; don't fill every slot from one artist.
    artist_limit = max(2, math.ceil(count * (.25 - .15 * variety)))
    artist_counts, album_counts = Counter(), Counter()
    chosen = []
    while remaining and len(chosen) < count:
        ranked = []
        for track in remaining:
            artists = artist_keys(track)
            if any(artist_counts[a] >= artist_limit for a in artists):
                continue
            year = release_year(track)
            era = max(0., 1 - abs(year - seed_year) / 20) if year and seed_year else 0.
            shared = bool(seed_artists & artists)
            relevance = evidence.get(track["id"], 0.) / scale
            relevance += (1 - variety) * (.35 * shared + .15 * era)
            album = (track.get("album") or {}).get("id") or normalized((track.get("album") or {}).get("name", ""))
            repeat_artist = max((artist_counts[a] for a in artists), default=0)
            score = relevance - (.18 + .5 * variety) * repeat_artist - .10 * album_counts[album]
            ranked.append((score, track["id"], track, artists, album))
        if not ranked:
            break
        _, _, track, artists, album = max(ranked, key=lambda r: (r[0], r[1]))
        chosen.append(track)
        artist_counts.update(artists)
        album_counts[album] += 1
        remaining.remove(track)
    return chosen


def quoted(value):
    return str(value).replace('"', ' ').strip()


def recommend(client, mood, genre, count, base_song="", variety=.3, market="GB", use_recommendations=False):
    """Build a metadata-ranked discovery mix using supported catalog search.

    Extended-quota accounts can opt into Spotify recommendations. Development
    apps avoid probing restricted recommendations/audio endpoints on every mix.
    """
    if mood not in MOODS or not isinstance(count, int) or not 5 <= count <= 50:
        raise ValueError("Choose a supported mood and 5–50 tracks.")
    if not isinstance(variety, (int, float)) or not 0 <= variety <= 1:
        raise ValueError("Discovery level must be between 0 and 1.")
    if not re.fullmatch(r"[a-z][a-z-]*", genre):
        raise ValueError("Choose a valid genre.")
    if not re.fullmatch(r"[A-Z]{2}", market):
        raise ValueError("Use a two-letter market code.")
    seed = None
    if base_song.strip():
        found = client.search(q=base_song.strip()[:250], type="track", limit=5, market=market)
        matches = [t for t in found.get("tracks", {}).get("items", []) if eligible(t)]
        if not matches:
            return [], "No matching song. Try adding the artist name."
        seed = matches[0]
    if use_recommendations:
        try:
            params = {"seed_tracks": [seed["id"]]} if seed else {"seed_genres": [genre], **MOODS[mood][2]}
            tracks = client.recommendations(limit=min(100, count * 2), market=market, **params).get("tracks", [])
            if tracks:
                evidence = {t["id"]: 1 / (20 + i) for i, t in enumerate(tracks) if eligible(t)}
                return rank_tracks(tracks, evidence, count, variety if seed else .5, seed), "Spotify recommendations, ranked for relevance and artist variety."
        except spotipy.SpotifyException as exc:
            if exc.http_status not in (403, 404):
                raise
    terms = MOOD_TERMS[mood]
    sound = genre
    seed_genre_used = False
    if seed and hasattr(client, "artist") and seed["artists"][0].get("id"):
        try:
            genres = client.artist(seed["artists"][0]["id"]).get("genres", [])
            if genres:
                sound = genres[0]
                seed_genre_used = True
        except spotipy.SpotifyException as exc:
            if exc.http_status not in (403, 404):
                raise
    queries = [(f'{terms[0]} genre:"{quoted(sound)}"', 1.),
               (f'{terms[1]} genre:"{quoted(sound)}"', .9),
               (f'genre:"{quoted(sound)}"', .7)]
    if seed:
        artist = quoted(seed["artists"][0]["name"])
        queries.insert(0, (f'artist:"{artist}"', 1. - .6 * variety))
        year = release_year(seed)
        if year:
            queries.append((f'genre:"{quoted(sound)}" year:{max(1900, year-3)}-{min(date.today().year, year+3)}', .8))
        if sound != genre:
            queries.append((f'genre:"{genre}"', .35 + .5 * variety))
    # Add an unfiltered mood phrase as a last, lower-confidence source.
    queries.append((f'{terms[0]} {quoted(sound)}', .4))
    tracks, evidence = search_candidates(client, queries, count, market)
    ranked = rank_tracks(tracks, evidence, count, variety if seed else .5, seed)
    note = "Catalog discovery · ranked by search relevance and artist variety. Mood matching is approximate."
    if seed:
        basis = "the seed artist’s genre" if seed_genre_used else "your selected genre"
        note += f' Seed: {seed["name"]} — {seed["artists"][0]["name"]}. Discovery uses {basis}.'
    return ranked, note


def playlist_csv(tracks):
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Track", "Artist", "Album", "Spotify URL", "Track ID"])
    for track in tracks:
        cells = [track["name"], ", ".join(a["name"] for a in track["artists"]),
                 (track.get("album") or {}).get("name", ""),
                 track.get("external_urls", {}).get("spotify", ""), track["id"]]
        # Keep song metadata from being interpreted as spreadsheet formulas.
        writer.writerow(["'" + str(c) if str(c).startswith(("=", "+", "-", "@")) else c for c in cells])
    return output.getvalue()


def safe_filename(name):
    return (re.sub(r"[^a-zA-Z0-9_-]+", "_", name).strip("_")[:80] or "my_mix") + ".csv"


def sample_tracks():
    """A fixed, labelled example; never presented as live recommendations."""
    songs = [
        ("Blinding Lights", "The Weeknd", "After Hours", "0VjIjW4GlUZAMYd2vXMi3b", 200040),
        ("Dreams", "Fleetwood Mac", "Rumours", "0ofHAoxe9vBkTCp2UQIavz", 257800),
        ("Get Lucky", "Daft Punk, Pharrell Williams", "Random Access Memories", "69kOkLUCkxIZYexIgSG8rq", 369626),
        ("Heat Waves", "Glass Animals", "Dreamland", "3USxtqRwSYz57Ewm6wWRMp", 238805),
        ("As It Was", "Harry Styles", "Harry's House", "4Dvkj6JhhA12EX05fT7y2e", 167303),
    ]
    return [{"name": name, "artists": [{"name": artist}], "album": {"name": album, "images": []},
             "id": tid, "duration_ms": duration, "external_urls": {"spotify": f"https://open.spotify.com/track/{tid}"}}
            for name, artist, album, tid, duration in songs]
