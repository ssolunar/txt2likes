# txt2likes

텍스트 파일의 곡 목록을 Spotify "좋아요 표시한 곡"에 일괄 추가하는 스크립트.
FLO 등 내보내기 기능이 없는 서비스에서 Spotify로 옮길 때 쓴다.

2026년 2월 Spotify Web API 변경(`PUT /me/library`, 요청당 40곡)에 대응한다.

## 준비

- Spotify **Premium** 계정 (개발자 앱 동작 조건)
- [Spotify 개발자 대시보드](https://developer.spotify.com/dashboard)에서 앱 생성
  - Redirect URI: `http://127.0.0.1:8888/callback`
  - API: Web API
- `pip install "spotipy>=2.26.0"`

## 입력 형식

한 줄에 한 곡, `제목 - 아티스트`. 아티스트가 여럿이면 `,`로 구분한다.

```
thank u, next - Ariana Grande
멀어 (feat. Beenzino) - 프라이머리
CU - 노윤하, CHERRY BOY 17
```

기본 경로는 `~/Downloads/spotify.txt`이고 `--src`로 바꿀 수 있다.

## 사용법

```powershell
$env:SPOTIPY_CLIENT_ID = "..."
$env:SPOTIPY_CLIENT_SECRET = "..."
$env:SPOTIPY_REDIRECT_URI = "http://127.0.0.1:8888/callback"

python txt2likes.py search            # 검색만. matched.csv 생성, 계정 변경 없음
python txt2likes.py save --limit 5    # 5곡만 시험 저장
python txt2likes.py save              # 전체 저장
```

`search`와 `save` 사이에 `matched.csv`를 열어 `의심` 칸에 `?`가 붙은 줄을 확인하고, 틀린 줄은 지운다.

## 알아둘 점

- 검색 첫 결과를 그대로 쓴다. 동명이곡, 리믹스, 노래방 반주 버전이 잡힐 수 있어 확인이 필요하다.
- `?` 표시는 제목 유사도만 본다. 한글 제목이 영문으로 등록된 곡에도 붙으므로 대부분은 오탐이다.
- 요청 간격은 2초다. 지연 없이 돌리면 앱에 24시간 요청 제한이 걸린다.
- `search`는 중단돼도 다시 실행하면 이어서 한다.
- `.cache`(로그인 토큰)와 `matched.csv`는 저장소에 올리지 않는다.
