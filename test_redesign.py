"""Offline regression checks. Never reads credentials or contacts Spotify."""
import unittest
import os
from copy import deepcopy
from unittest.mock import patch

import spotipy
from streamlit.testing.v1 import AppTest
from spotify_service import playlist_csv, recommend, safe_filename, sample_tracks, unique_tracks, rank_tracks, search_candidates


class FakeSpotify:
    def search(self, **kwargs):
        return {"tracks": {"items": sample_tracks()}}

    def recommendations(self, **kwargs):
        raise spotipy.SpotifyException(404, -1, "Unavailable")


class ServiceTests(unittest.TestCase):
    def test_fallback_deduplicates_and_excludes_seed(self):
        tracks, note = recommend(FakeSpotify(), "Happy", "pop", 20, "Blinding Lights", .5)
        self.assertEqual(len(tracks), 4)
        self.assertNotIn(sample_tracks()[0]["id"], [t["id"] for t in tracks])
        self.assertIn("approximate", note)

    def test_mood_fallback(self):
        tracks, _ = recommend(FakeSpotify(), "Relaxed", "indie", 5)
        self.assertEqual(len(tracks), 5)

    def test_auth_errors_are_not_silenced(self):
        client = FakeSpotify()
        client.search = lambda **kwargs: (_ for _ in ()).throw(spotipy.SpotifyException(401, -1, "Unauthorized"))
        with self.assertRaises(spotipy.SpotifyException):
            recommend(client, "Happy", "pop", 5)

    def test_csv_and_filename(self):
        tracks = sample_tracks()
        tracks[0]["name"] = "=1+1"
        self.assertIn("'=1+1", playlist_csv(tracks))
        self.assertEqual(safe_filename("../mix / name"), "mix_name.csv")
        self.assertEqual(len(unique_tracks(tracks + tracks)), 5)

    def test_recordings_unplayable_and_remasters_are_filtered(self):
        original = sample_tracks()[0]
        remaster = deepcopy(original)
        remaster.update(id="a" * 22, name=original["name"] + " - 2020 Remaster")
        local = {**sample_tracks()[1], "is_local": True}
        blocked = {**sample_tracks()[2], "is_playable": False}
        self.assertEqual(len(unique_tracks([original, remaster, local, blocked])), 1)

    def test_artist_diversity_and_deterministic_ranking(self):
        tracks = []
        for i in range(30):
            track = deepcopy(sample_tracks()[0])
            track.update(id=str(i).zfill(22), name=f"Track {i}")
            track["artists"] = [{"name": "Dominant artist" if i < 15 else f"Artist {i}"}]
            tracks.append(track)
        evidence = {t["id"]: 2 if i < 15 else 1 for i, t in enumerate(tracks)}
        selected = rank_tracks(tracks, evidence, 10, 1.)
        self.assertEqual(len(selected), 10)
        self.assertLessEqual(sum(t["artists"][0]["name"] == "Dominant artist" for t in selected), 2)
        self.assertEqual(selected, rank_tracks(tracks, evidence, 10, 1.))

    def test_pages_are_bounded_and_exhausted_queries_not_repeated(self):
        client = FakeSpotify()
        with patch.object(client, "search", wraps=client.search) as search:
            tracks, _ = search_candidates(client, [("indie", 1), ("chill", .8)], 50, "GB")
            self.assertEqual(search.call_count, 2)
            self.assertEqual(len(tracks), 5)
        client.search = lambda **kwargs: {"tracks": {"items": [
            {**deepcopy(sample_tracks()[0]), "id": str(kwargs["offset"] + i).zfill(22), "name": f'Song {kwargs["offset"] + i}'}
            for i in range(10)]}}
        tracks, _ = search_candidates(client, [("indie", 1)], 20, "GB")
        self.assertEqual(len(tracks), 30)

    def test_search_default_skips_restricted_endpoints_and_propagates_rate_limit(self):
        client = FakeSpotify()
        with patch.object(client, "recommendations") as restricted:
            recommend(client, "Happy", "pop", 5)
            restricted.assert_not_called()
        client.search = lambda **kwargs: (_ for _ in ()).throw(spotipy.SpotifyException(429, -1, "Rate limit"))
        with self.assertRaises(spotipy.SpotifyException):
            recommend(client, "Happy", "pop", 5)

    def test_input_validation(self):
        for mood, count, variety in [("Unknown", 10, .5), ("Happy", 100, .5), ("Happy", 10, 2)]:
            with self.assertRaises(ValueError):
                recommend(FakeSpotify(), mood, "pop", count, variety=variety)


class InterfaceTests(unittest.TestCase):
    def setUp(self):
        import streamlit as st
        st.cache_data.clear()
        st.cache_resource.clear()
        secrets_patch = patch.object(st.secrets, "get", return_value="")
        env_patch = patch.dict(os.environ, {"SPOTIPY_CLIENT_ID": "", "SPOTIPY_CLIENT_SECRET": ""})
        secrets_patch.start()
        env_patch.start()
        self.addCleanup(secrets_patch.stop)
        self.addCleanup(env_patch.stop)

    def app(self):
        # Force a disconnected launch even when tests run beside local secrets.
        return AppTest.from_file("spotify_app.py", default_timeout=15).run()

    def test_initial_view_and_example_persist(self):
        app = self.app()
        self.assertFalse(app.exception)
        app.button[4].click().run()
        self.assertFalse(app.exception)
        self.assertEqual(len(app.session_state["tracks"]), 5)
        app.selectbox[0].select("Happy").run()
        self.assertEqual(len(app.session_state["tracks"]), 5)
        self.assertFalse(app.exception)

    def test_seed_validation_and_presets(self):
        app = self.app()
        app.radio[0].set_value("From a song").run()
        app.button[0].click().run()
        self.assertIn("Add a song", app.warning[0].value)
        app.button[1].click().run()
        self.assertEqual(app.session_state["mood"], "Happy")
        self.assertEqual(app.session_state["genre"], "pop")
        self.assertEqual(app.session_state["mode"], "By mood")
        self.assertFalse(app.exception)

    def test_generation_and_failed_retry_keep_previous_mix(self):
        with patch.dict(os.environ, {"SPOTIPY_CLIENT_ID": "test-id", "SPOTIPY_CLIENT_SECRET": "test-secret"}), \
             patch("spotify_service.make_client", return_value=FakeSpotify()), \
             patch("spotify_service.recommend", return_value=(sample_tracks(), "Test selection")):
            app = self.app()
            app.button[0].click().run()
            self.assertFalse(app.exception)
            self.assertEqual(len(app.session_state["tracks"]), 5)
            self.assertFalse(app.session_state["sample"])
        with patch.dict(os.environ, {"SPOTIPY_CLIENT_ID": "test-id", "SPOTIPY_CLIENT_SECRET": "test-secret"}), \
             patch("spotify_service.make_client", return_value=FakeSpotify()), \
             patch("spotify_service.recommend", side_effect=spotipy.SpotifyException(429, -1, "Rate limit")):
            app.selectbox[0].select("Happy").run()
            app.button[0].click().run()
            self.assertIn("Spotify is busy", app.error[0].value)
            self.assertEqual(len(app.session_state["tracks"]), 5)
            self.assertFalse(app.exception)

    def test_identical_success_is_cached(self):
        with patch.dict(os.environ, {"SPOTIPY_CLIENT_ID": "cache-id", "SPOTIPY_CLIENT_SECRET": "cache-secret"}), \
             patch("spotify_service.make_client", return_value=FakeSpotify()), \
             patch("spotify_service.recommend", return_value=(sample_tracks(), "Test selection")) as generate:
            app = self.app()
            app.button[0].click().run()
            app.button[0].click().run()
            self.assertEqual(generate.call_count, 1)
            self.assertFalse(app.exception)

    def test_missing_credentials_has_useful_message(self):
        app = self.app()
        app.button[0].click().run()
        self.assertIn("Add your Spotify credentials", app.info[0].value)
        self.assertFalse(app.exception)


if __name__ == "__main__":
    unittest.main()
