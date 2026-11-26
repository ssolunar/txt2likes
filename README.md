# txt2likes

Bulk-import a text file of songs into your Spotify Liked Songs.
Useful when moving from a service with no export or transfer support (e.g. FLO).

Works with the February 2026 Spotify Web API changes (`PUT /me/library`, 40 tracks per request).

## Requirements

- A Spotify **Premium** account (required for Development Mode apps)
- An app created in the [Spotify Developer Dashboard](https://developer.spotify.com/dashboard)
  - Redirect URI: `http://127.0.0.1:8888/callback`
  - API: Web API
- `pip install "spotipy>=2.26.0"`

## Input format

One song per line, `Title - Artist`. Separate multiple artists with `,`.

```
thank u, next - Ariana Grande
멀어 (feat. Beenzino) - 프라이머리
CU - 노윤하, CHERRY BOY 17
```

The default path is `~/Downloads/spotify.txt`. Use `--src` to change it.

## Usage

```powershell
$env:SPOTIPY_CLIENT_ID = "..."
$env:SPOTIPY_CLIENT_SECRET = "..."
$env:SPOTIPY_REDIRECT_URI = "http://127.0.0.1:8888/callback"

python txt2likes.py search            # search only: writes matched.csv, changes nothing in your account
python txt2likes.py save --limit 5    # trial run: save the first 5 tracks
python txt2likes.py save              # save everything
```

Between `search` and `save`, open `matched.csv`, check the rows flagged `?` in the last column, and delete the wrong ones.

## Notes

- The first search result is used as-is, so same-title songs, remixes, and karaoke versions can slip in. Review before saving.
- The `?` flag only compares titles. It also fires when a Korean title is listed in English on Spotify, so most flags are false positives.
- Requests are spaced 2 seconds apart. Running without a delay got the app rate-limited for 24 hours.
- `search` is resumable: run it again and it skips songs already in `matched.csv`.
- `.cache` (login token) and `matched.csv` are git-ignored.
