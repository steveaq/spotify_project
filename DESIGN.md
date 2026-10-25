# Side A — playlist studio

Make music discovery feel like browsing a thoughtfully arranged record shop.

This redesign applies the hierarchy, semantic tokens, explicit interaction states,
8px spacing rhythm and accessibility guidance from the MIT-licensed
[Sleek skill by TypeUI / Bergside](https://github.com/bergside/awesome-design-skills/blob/main/skills/sleek/SKILL.md).
The serif display accent and structured composition also draw on the repository's
[Editorial skill](https://github.com/bergside/awesome-design-skills/blob/main/skills/editorial/SKILL.md).
The palette is adapted to this music product rather than copying generic blue tokens.

## Foundations

- Paper: #f8f7f2; ink: #20281f; muted text: #61665b.
- Action green: #315443; decorative lime: #d4e68b; borders: #dddfd3.
- System sans for controls and content; Georgia for expressive display accents.
- 8px spacing baseline, 44px minimum action targets, restrained 4–6px corners.
- No font CDN or third-party decorative image requests. Vinyl artwork is CSS.

## Components and states

The hero establishes identity. The builder offers mood and song entry paths.
Presets change the inputs without silently generating a playlist. Discovery level
applies to song mixes and is explicitly disabled for mood mixes. Loading, missing
credentials, empty results, access errors and rate limits have visible messages.
Existing results survive failed requests and widget changes. A new successful
generation replaces them. A fixed example is explicitly labelled as such.

Track rows contain artwork, title, artist, album, time and an accessible Spotify
link. A single optional player avoids loading dozens of embeds. Export uses the
current playlist's metadata. There is no inactive 'save to Spotify' action.

## Responsive and accessibility requirements

At 640px and below, the hero stacks, controls use Streamlit's responsive columns,
album text is omitted from track rows, and the footer wraps. Keep real widget
labels, visible keyboard focus and explanatory disabled states. Decorative artwork
is labelled as one image. Respect reduced motion. Metadata is escaped before HTML
rendering; player IDs and image hosts are validated.

## Content

Use short labels and useful errors. Describe search fallback as approximate mood
matching. Never claim a configured credential has been successfully authenticated.
Keep credential setup under Connection & help, with no secrets in logs or UI.

## Maintenance and QA

Replace the previous global dark styles with styles.css and the light Streamlit
theme. Keep tokens in :root consistent with .streamlit/config.toml. Avoid stacked
debug alerts, oversized per-track players and disabled promises of future features.

- Run python -m unittest test_redesign.py from the project directory.
- Inspect at desktop and 390px mobile widths for clipping and hierarchy.
- Check keyboard focus, empty song validation, presets and reduced motion.
- Confirm example and generated results survive control changes.
- Check live Spotify access separately with the user's configured application.

## Discovery maintenance

The default service is now a deterministic metadata ranker with artist caps and
recording deduplication. Do not describe it as trained machine learning or audio
analysis. Successful identical generations are cached for five minutes. Preserve
existing results during errors and respect the 429 cooldown. See DEPLOYMENT.md for
live account access and sleeping-host constraints.
