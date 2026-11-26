"""텍스트 목록(제목 - 아티스트) -> Spotify 좋아요.

  python txt2likes.py search            # matched.csv / not_found.txt 생성 (계정 변경 없음)
  python txt2likes.py save [--limit N]  # matched.csv 의 URI를 좋아요에 추가

search 는 중간에 끊겨도 다시 실행하면 이어서 합니다.

환경 변수(spotipy가 직접 읽음):
  SPOTIPY_CLIENT_ID, SPOTIPY_CLIENT_SECRET, SPOTIPY_REDIRECT_URI
필요: pip install "spotipy>=2.26.0"  (2026-02 이후 PUT /me/library 대응 버전)
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
    """'제목 (feat. X) - 가수1, 가수2' -> ('제목', '가수1')"""
    title, artist = line.rsplit(" - ", 1)
    return FEAT.sub("", title).strip(), artist.split(",")[0].strip()


assert parse("멀어 (feat. Beenzino) - 프라이머리") == ("멀어", "프라이머리")
assert parse("CU - 노윤하, CHERRY BOY 17") == ("CU", "노윤하")
assert parse("A - B - C") == ("A - B", "C")


def remaining(lines):
    """이미 matched.csv / not_found.txt 에 있는 줄을 뺀 나머지."""
    done = set()
    if Path("matched.csv").exists():
        with open("matched.csv", encoding="utf-8-sig", newline="") as f:
            done = {r["원본"] for r in csv.DictReader(f)}
    if Path("not_found.txt").exists():
        done |= set(Path("not_found.txt").read_text(encoding="utf-8").splitlines())
    return [l for l in lines if l not in done]


def client():
    import spotipy
    from spotipy.oauth2 import SpotifyOAuth

    # retries=0: 속도 제한(429)에 걸리면 Retry-After 만큼(최대 24시간) 잠들지 않고 바로 오류를 냄
    return spotipy.Spotify(auth_manager=SpotifyOAuth(scope="user-library-modify"),
                           retries=0, status_retries=0)


def search(src):
    text = src.read_text(encoding="utf-8-sig")
    lines = list(dict.fromkeys(l.strip() for l in text.splitlines() if " - " in l))
    todo = remaining(lines)
    print(f"전체 {len(lines)}곡 중 {len(lines) - len(todo)}곡 완료, {len(todo)}곡 검색")
    if not todo:
        return
    sp = client()
    new_file = not Path("matched.csv").exists() or Path("matched.csv").stat().st_size == 0
    with open("matched.csv", "a", newline="", encoding="utf-8-sig" if new_file else "utf-8") as f, \
         open("not_found.txt", "a", encoding="utf-8") as nf:
        w = csv.writer(f)
        if new_file:
            w.writerow(["원본", "찾은 제목", "찾은 아티스트", "uri", "의심"])
        for i, line in enumerate(todo, 1):
            title, artist = parse(line)
            items = []
            try:
                for q in (f"track:{title} artist:{artist}", f"{title} {artist}"):
                    items = sp.search(q=q, type="track", limit=1)["tracks"]["items"]
                    time.sleep(2)  # ponytail: 고정 지연(30초당 15회). 또 429가 나면 값을 키울 것
                    if items:
                        break
            except Exception as e:  # 429 등: 여기까지 저장하고 중단
                wait = (getattr(e, "headers", None) or {}).get("Retry-After", "?")
                print(f"\n중단: {e}\n재시도 가능까지 {wait}초. 그 뒤 같은 명령을 다시 실행하면 이어서 합니다.")
                return
            if not items:
                nf.write(line + "\n")
            else:
                t = items[0]
                # ponytail: 제목 유사도만 봄(아티스트는 한글/영문 표기가 달라 비교 불가). 눈으로 확인 필요.
                similar = SequenceMatcher(None, title.lower(), FEAT.sub("", t["name"]).lower()).ratio()
                w.writerow([line, t["name"], ", ".join(a["name"] for a in t["artists"]),
                            t["uri"], "?" if similar < 0.6 else ""])
            print(f"\r{i}/{len(todo)} 검색", end="", flush=True)
    print("\n완료: matched.csv 와 not_found.txt 를 확인하세요")


def save(limit):
    with open("matched.csv", encoding="utf-8-sig", newline="") as f:
        uris = [r["uri"] for r in csv.DictReader(f) if r["uri"]]
    uris = uris[:limit] if limit else uris
    uris.reverse()  # 아래 줄부터 넣어 원본 첫 줄이 좋아요 맨 위로 오게 함
    sp = client()
    for i in range(0, len(uris), 40):  # PUT /me/library 는 요청당 최대 40개
        sp.current_user_saved_tracks_add(tracks=uris[i:i + 40])
        print(f"\r{min(i + 40, len(uris))}/{len(uris)} 저장", end="", flush=True)
    print("\n완료")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("cmd", choices=["search", "save"])
    p.add_argument("--src", type=Path, default=SRC)
    p.add_argument("--limit", type=int, help="save: 앞에서 N곡만 저장(시험용)")
    a = p.parse_args()
    search(a.src) if a.cmd == "search" else save(a.limit)
