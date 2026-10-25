# Deployment and availability

The portfolio currently links to https://saq-spotfify-app.streamlit.app/.

## Current live check — 25 October 2026

- The deployed app was asleep and successfully woke when requested.
- The old deployment reports HTTP 403: **Active premium subscription required for
  the owner of the app**. Spotify says it can take a few hours for access to return
  after the subscription status changes.
- A read-only local check obtained a client token successfully, but search returned
  403 and a subsequent diagnostic returned 429. Playlist relevance could not be
  evaluated against the live catalog. Offline tests cover ranking and failure cases.

An access token alone does not prove that catalog endpoints are accessible.
The app owner must resolve the Spotify account requirement and verify the app's
Developer Dashboard settings. Credentials previously committed to Git should be
rotated. They are no longer tracked in the current tree; old commits still contain
them. This change intentionally does not rewrite repository history.

## Streamlit Community Cloud

Community Cloud puts apps to sleep after 12 hours without traffic. This is a hosting
policy rather than a recommendation-model performance issue. Anyone who can view
the app can use its wake button. Caching and lighter dependencies reduce app work,
but do not disable the hosting policy.

Source: https://docs.streamlit.io/deploy/streamlit-community-cloud/manage-your-app

Before removing secrets from Git, retain the credentials in the deployed app's
**Settings → Secrets**. Add these values through that interface:

```toml
SPOTIPY_CLIENT_ID = "your_client_id"
SPOTIPY_CLIENT_SECRET = "your_client_secret"
```

If they are already configured there, no change is necessary. Never add them back
to the repository. Python 3.11 is the tested runtime. The entry point remains
`spotify_app.py` on `main`, so the current app can keep its existing URL.

## Always-on option

`render.yaml` is a ready-to-review Render Blueprint for a **paid Starter web
service**. Paid Render compute does not spin down when idle; the free service does.
No service is provisioned by committing this file. Deploying it is a separate,
billable action. Verify the current cost before creating the service.

1. Create a Render Blueprint from this GitHub repository.
2. Review the `starter` plan and cost.
3. Enter Spotify credentials as private environment variables.
4. Deploy; verify `/_stcore/health`, the example mix, then live catalog generation.
5. Update the portfolio's Try App link after confirming the new URL works.

Sources: https://render.com/docs/faq and https://render.com/pricing

The service uses `$PORT`, binds on `0.0.0.0`, and has a Streamlit health check.
`SPOTIFY_MARKET` defaults to `GB`; change it to a supported two-letter country code
as appropriate. `SPOTIFY_USE_RECOMMENDATIONS=true` opts into Spotify's recommendations
endpoint for accounts that already have access; ordinary development apps should
leave it unset. It cannot bypass account or endpoint restrictions.

## Fast portfolio demos

For future projects, precompute public datasets and serve the interactive demo as a
static site where possible. The UI can load immediately without a Python process
waking up. Keep a visible last-updated date and a working sample when live APIs fail.
