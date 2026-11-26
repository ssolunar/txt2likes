"""Text song list ("Title - Artist" per line) -> Spotify Liked Songs.

  python txt2likes.py search            # writes matched.csv / not_found.txt (no account changes)
  python txt2likes.py save [--limit N]  # adds the URIs in matched.csv to Liked Songs

search is resumable: run it again after an interruption and it continues.

Environment variables (read by spotipy itself):
  SPOTIPY_CLIENT_ID, SPOTIPY_CLIENT_SECRET, SPOTIPY_REDIRECT_URI
Requires: pip install "spotipy>=2.26.0"  (first version using PUT /me/library, Feb 2026)
"""
import argparse
import csv
import re
import time
from difflib import SequenceMatcher
from pathlib import Path

SRC = Path.home() / "Downloads" / "spotify.txt"
FEAT = re.compile(r"\s*[(\[](feat|with|prod)[^)\]]*[)\]]", re.I)


def parse(line):
    """'Title (feat. X) - Artist1, Artist2' -> ('Title', 'Artist1')"""
    title, artist = line.rsplit(" - ", 1)
    return FEAT.sub("", title).strip(), artist.split(",")[0].strip()


assert parse("멀어 (feat. Beenzino) - 프라이머리") == ("멀어", "프라이머리")
assert parse("CU - 노윤하, CHERRY BOY 17") == ("CU", "노윤하")
assert parse("A - B - C") == ("A - B", "C")


def remaining(lines):
    """Lines not yet recorded in matched.csv / not_found.txt."""
    done = set()
    if Path("matched.csv").exists():
        with open("matched.csv", encoding="utf-8-sig", newline="") as f:
            done = {r["source"] for r in csv.DictReader(f)}
    if Path("not_found.txt").exists():
        done |= set(Path("not_found.txt").read_text(encoding="utf-8").splitlines())
    return [l for l in lines if l not in done]


def client():
    import spotipy
    from spotipy.oauth2 import SpotifyOAuth

    # retries=0: on a rate limit (429) fail immediately instead of sleeping for Retry-After (up to 24h)
    return spotipy.Spotify(auth_manager=SpotifyOAuth(scope="user-library-modify"),
                           retries=0, status_retries=0)


def search(src):
    text = src.read_text(encoding="utf-8-sig")
    lines = list(dict.fromkeys(l.strip() for l in text.splitlines() if " - " in l))
    todo = remaining(lines)
    print(f"{len(lines)} songs total, {len(lines) - len(todo)} done, searching {len(todo)}")
    if not todo:
        return
    sp = client()
    new_file = not Path("matched.csv").exists() or Path("matched.csv").stat().st_size == 0
    with open("matched.csv", "a", newline="", encoding="utf-8-sig" if new_file else "utf-8") as f, \
         open("not_found.txt", "a", encoding="utf-8") as nf:
        w = csv.writer(f)
        if new_file:
            w.writerow(["source", "found_title", "found_artist", "uri", "suspect"])
        for i, line in enumerate(todo, 1):
            title, artist = parse(line)
            items = []
            try:
                for q in (f"track:{title} artist:{artist}", f"{title} {artist}"):
                    items = sp.search(q=q, type="track", limit=1)["tracks"]["items"]
                    time.sleep(2)  # ponytail: fixed delay (15 requests / 30s). Raise it if 429 comes back
                    if items:
                        break
            except Exception as e:  # 429 etc.: keep what we have and stop
                wait = (getattr(e, "headers", None) or {}).get("Retry-After", "?")
                print(f"\nStopped: {e}\nRetry possible in {wait}s. Run the same command again to resume.")
                return
            if not items:
                nf.write(line + "\n")
            else:
                t = items[0]
                # ponytail: compares titles only (artist names differ between Korean and English
                # spellings, so they can't be compared). Flagged rows need a manual look.
                similar = SequenceMatcher(None, title.lower(), FEAT.sub("", t["name"]).lower()).ratio()
                w.writerow([line, t["name"], ", ".join(a["name"] for a in t["artists"]),
                            t["uri"], "?" if similar < 0.6 else ""])
            print(f"\r{i}/{len(todo)} searched", end="", flush=True)
    print("\nDone: review matched.csv and not_found.txt")


def save(limit):
    with open("matched.csv", encoding="utf-8-sig", newline="") as f:
        uris = [r["uri"] for r in csv.DictReader(f) if r["uri"]]
    uris = uris[:limit] if limit else uris
    uris.reverse()  # add bottom-up so the first line of the source ends up on top of Liked Songs
    sp = client()
    for i in range(0, len(uris), 40):  # PUT /me/library takes at most 40 URIs per request
        sp.current_user_saved_tracks_add(tracks=uris[i:i + 40])
        print(f"\r{min(i + 40, len(uris))}/{len(uris)} saved", end="", flush=True)
    print("\nDone")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("cmd", choices=["search", "save"])
    p.add_argument("--src", type=Path, default=SRC)
    p.add_argument("--limit", type=int, help="save: only the first N tracks (trial run)")
    a = p.parse_args()
    search(a.src) if a.cmd == "search" else save(a.limit)
