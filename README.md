# Side A · Your playlist studio

A redesigned Streamlit music discovery app. Choose a mood and genre, or start with
a song and tune the balance between familiar sounds and broader discoveries.

## Run

```bash
python -m pip install -r requirements.txt
python -m streamlit run spotify_app.py
```

The interface and a labelled example mix work without Spotify credentials.
For live discovery, set `SPOTIPY_CLIENT_ID` and `SPOTIPY_CLIENT_SECRET` in the
environment or create `.streamlit/secrets.toml`:

```toml
SPOTIPY_CLIENT_ID = "your_client_id"
SPOTIPY_CLIENT_SECRET = "your_client_secret"
```

Create or manage your app at the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard).
Restart after changing credentials. Never commit secrets or OAuth cache files.

## Features

- Mood and genre discovery, including the original genre selection.
- Song-based discovery with deterministic relevance ranking, seed artist genre
  enrichment when available, and discovery control.
- Catalog search as the default, clearly described as approximate mood matching.
  Extended-quota accounts can explicitly opt into Spotify recommendations.
- Three starting presets, persistent session results, album artwork and duration.
- One selectable Spotify preview player and links to individual tracks.
- CSV download of the current mix. Direct saving to Spotify is not implemented.
- Responsive paper-and-green interface with keyboard focus and reduced motion.

Spotify access and playback depend on app permissions, account and region. The
app can return fewer unique tracks than requested; it displays the actual count.
The fixed example is independent of the chosen controls and is never represented
as a live recommendation. Session results are temporary; download a CSV to keep them.

## Structure and checks

`spotify_app.py` contains the interface, `styles.css` the visual system,
`spotify_service.py` Spotify access and export, and `genres.py` the genre list.
See `DESIGN.md` for design sources, decisions and accessibility checks.

```bash
python -m unittest test_redesign.py
```

These regression tests run offline with fake Spotify responses. They cover
fallback results, authentication errors, CSV safety, preset behaviour, validation,
and results surviving widget changes. They do not verify live Spotify permissions.

## Recommendation approach

This is a transparent metadata ranker, not a trained audio model. It combines
weighted search relevance across mood/genre queries, seed-artist overlap and
release-year proximity. Greedy selection penalises repeated artists and albums,
and enforces an artist ceiling. Higher discovery levels increase the repetition
penalty. Recording identifiers and normalised titles remove duplicate releases;
local and explicitly unplayable tracks are excluded. A small candidate pool can
produce fewer results rather than padding the mix with repeated artists.

Search uses ten-item pages with a bounded request budget and stops exhausted
queries. Identical successful mixes are cached for five minutes. Tokens are kept
in memory, and rate-limit responses trigger a session cooldown. No random shuffle
is used, so the same candidate pool and settings give reproducible rankings.

Optional settings: `SPOTIFY_MARKET=GB` and
`SPOTIFY_USE_RECOMMENDATIONS=true` (only for accounts with endpoint access).
The default avoids repeatedly probing restricted recommendation/audio APIs.

## Hosting and live access

See [DEPLOYMENT.md](DEPLOYMENT.md) for the observed Spotify Premium blocker,
Community Cloud sleeping behaviour and the optional always-on Render Blueprint.
Committing `render.yaml` does not provision a service or incur hosting charges.
Previously tracked local secrets, OAuth cache and the credential-bearing manual
script are ignored; their local copies are retained. Rotate exposed credentials:
removing them from the current tree does not remove them from Git history.
