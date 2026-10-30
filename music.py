import csv
import hashlib
import io
import json
import random
import threading
import time
from pathlib import Path
from urllib.parse import quote, urlparse

import requests
import streamlit as st

st.set_page_config(page_title="오늘 노래 추천", page_icon="🎵", layout="centered")

# ---------- UI 스타일링 (스포티파이/멜론 감성의 밝고 화사한 라이트 테마) ----------
st.markdown(
    """
    <style>
        .stApp {
            background-color: #f8fafc;
            color: #1e293b;
        }
        h1 {
            color: #0f172a !important;
            font-weight: 800 !important;
        }
        p, .stCaption {
            color: #475569 !important;
        }
        .stSelectbox label, .stTextInput label, .stRadio label {
            color: #334155 !important;
            font-weight: 700;
        }
        .stButton>button {
            border-radius: 24px;
            font-weight: 700;
            border: none;
            background-color: #1db954;
            color: #ffffff;
            transition: 0.2s;
            box-shadow: 0 4px 12px rgba(29, 185, 84, 0.3);
        }
        .stButton>button:hover {
            background-color: #1aa34a;
            color: #ffffff;
            box-shadow: 0 6px 16px rgba(29, 185, 84, 0.4);
        }
        .stTabs [data-baseweb="tab-list"] {
            gap: 10px;
            background-color: #e2e8f0;
            padding: 6px;
            border-radius: 16px;
        }
        .stTabs [data-baseweb="tab"] {
            border-radius: 12px;
            padding: 10px 20px;
            background-color: transparent;
            color: #64748b;
            font-weight: 700;
        }
        .stTabs [aria-selected="true"] {
            background-color: #ffffff !important;
            color: #0f172a !important;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------- 국가별·장르별 유명 아티스트 사전 ----------
ARTIST_DICTIONARY = {
    "한국": {
        "발라드": [
            "김광석",
            "신승훈",
            "성시경",
            "김동률",
            "박효신",
            "이소라",
            "아이유",
            "임창정",
            "백지영",
            "폴킴",
            "멜로망스",
            "정승환",
            "이무진",
            "케이시",
        ],
        "힙합": [
            "타이거JK",
            "다이나믹듀오",
            "에픽하이",
            "리쌍",
            "지누션",
            "버벌진트",
            "빈지노",
            "창모",
            "지코",
            "릴보이",
            "기리보이",
        ],
        "댄스": [
            "서태지와아이들",
            "듀스",
            "엄정화",
            "god",
            "보아",
            "신화",
            "쿨",
            "코요태",
            "뉴진스",
            "아이브",
            "르세라핌",
            "에스파",
        ],
        "R&B": [
            "김조한",
            "브라운아이드소울",
            "바비킴",
            "휘성",
            "거미",
            "크러쉬",
            "딘",
            "비비",
            "헤이즈",
            "Colde",
            "GSoul",
        ],
        "인디": [
            "장기하와얼굴들",
            "볼빨간사춘기",
            "혁오",
            "잔나비",
            "10CM",
            "검정치마",
            "루시",
            "너드커넥션",
            "실리카겔",
            "카더가든",
            "선우정아",
            "쏜애플",
            "ADOY",
        ],
        "록": [
            "들국화",
            "부활",
            "YB",
            "국카스텐",
            "자우림",
            "체리필터",
            "크라잉넛",
            "딕펑스",
        ],
        "트로트": ["나훈아", "남진", "송가인", "임영웅", "장윤정", "영탁", "진성"],
    },
    "미국": {
        "팝": [
            "Michael Jackson",
            "Madonna",
            "Whitney Houston",
            "Taylor Swift",
            "Bruno Mars",
            "Adele",
            "Ed Sheeran",
            "Justin Bieber",
            "The Kid LAROI",
            "Benson Boone",
            "Lauv",
            "Olivia Rodrigo",
            "Sabrina Carpenter",
            "Billie Eilish",
            "Harry Styles",
        ],
        "힙합": [
            "Tupac",
            "Eminem",
            "Jay-Z",
            "Kendrick Lamar",
            "Kanye West",
            "Drake",
            "Snoop Dogg",
            "Post Malone",
            "Travis Scott",
        ],
        "R&B": [
            "Stevie Wonder",
            "Marvin Gaye",
            "Alicia Keys",
            "Usher",
            "Beyonce",
            "John Legend",
            "The Weeknd",
            "Frank Ocean",
            "SZA",
        ],
        "록": [
            "The Beatles",
            "Queen",
            "Led Zeppelin",
            "Nirvana",
            "AC/DC",
            "Bon Jovi",
            "Foo Fighters",
            "AJR",
            "Imagine Dragons",
            "Coldplay",
        ],
        "컨트리": [
            "Johnny Cash",
            "Taylor Swift",
            "Luke Bryan",
            "Chris Stapleton",
            "Shania Twain",
            "Carrie Underwood",
            "Morgan Wallen",
        ],
        "인디": [
            "Arctic Monkeys",
            "The Strokes",
            "Tame Impala",
            "Radiohead",
            "Vampire Weekend",
            "Lorde",
            "Lizzy McAlpine",
            "Avicii",
            "Clairo",
            "Wallows",
            "Conan Gray",
        ],
        "OST": [
            "Hans Zimmer",
            "John Williams",
            "Lady Gaga",
            "Elton John",
            "Phil Collins",
            "Celine Dion",
            "FINNEAS",
        ],
    },
    "일본": {
        "J-pop": [
            "Hikaru Utada",
            "Ayumi Hamasaki",
            "Kenshi Yonezu",
            "Aimyon",
            "Official髭男dism",
            "YOASOBI",
            "Vaundy",
            "Fujii Kaze",
            "Ado",
            "Mrs. GREEN APPLE",
        ],
        "시티팝": [
            "Tatsuro Yamashita",
            "Mariya Takeuchi",
            "Anri",
            "Toshiki Kadomatsu",
            "Miki Matsubara",
        ],
        "애니송": [
            "LiSA",
            "Linked Horizon",
            "Yoko Kanno",
            "Aimer",
            "RADWIMPS",
            "Flow",
            "Creepy Nuts",
            "Eve",
        ],
        "J-록": [
            "X Japan",
            "L'Arc-en-Ciel",
            "B'z",
            "ONE OK ROCK",
            "King Gnu",
            "GLAY",
            "Mrs. GREEN APPLE",
            "Radwimps",
        ],
        "힙합": ["RIP SLYME", "Zeebra", "Bad Hop", "Creepy Nuts", "KREVA"],
        "엔카": ["Hibari Misora", "Hiroshi Itsuki", "Sayuri Ishikawa", "Kiyoshi Hikawa"],
        "보컬로이드": ["Kenshi Yonezu", "Supercell", "DECO*27", "ryo"],
    },
}

# 수면용 공통 장르 및 아티스트
SLEEP_GENRES = {
    "클래식": ["Chopin", "Beethoven", "Bach", "Mozart", "Ludovico Einaudi"],
    "수면음악": [
        "Ambient Sleep",
        "Deep Sleep Music",
        "Meditation Relax",
        "Nature Sounds",
    ],
    "잔잔한 피아노": [
        "Relaxing Piano",
        "Solo Piano",
        "Café Piano",
        "Peaceful Piano",
    ],
}

MUSIC = {}
for country in ARTIST_DICTIONARY:
  MUSIC[country] = ARTIST_DICTIONARY[country].copy()
  MUSIC[country].update(SLEEP_GENRES)

MOOD_GENRES = {
    "😄 기쁨": {
        "한국": ["댄스", "힙합", "인디"],
        "미국": ["팝", "힙합", "인디"],
        "일본": ["J-pop", "애니송", "시티팝"],
    },
    "😢 슬픔": {
        "한국": ["발라드", "인디", "R&B"],
        "미국": ["R&B", "인디", "OST"],
        "일본": ["시티팝", "J-pop", "J-록"],
    },
    "😡 분노": {
        "한국": ["록", "힙합", "댄스"],
        "미국": ["록", "힙합"],
        "일본": ["J-록", "힙합"],
    },
    "😌 평온": {
        "한국": ["R&B", "발라드", "수면음악"],
        "미국": ["팝", "컨트리", "잔잔한 피아노"],
        "일본": ["시티팝", "클래식", "J-pop"],
    },
    "😴 졸림": {c: list(SLEEP_GENRES) for c in ARTIST_DICTIONARY},
}

DATA_FILE = Path("shared_lists.json")
MAX_BOARDS = 100
MAX_SONGS = 30
YT_HOSTS = ("youtube.com", "youtu.be")
SP_HOSTS = ("spotify.com", "spotify.link")


# ---------- 함수 정의 ----------
def to_song(s, genre=""):
  year_text = s.get("releaseDate", "")[:4]
  return {
      "id": s["trackId"],
      "title": s["trackName"],
      "artist": s["artistName"],
      "image": s["artworkUrl100"],
      "preview": s["previewUrl"],
      "genre": genre,
      "itunes_genre": s.get("primaryGenreName", ""),
      "year": int(year_text) if year_text.isdigit() else None,
  }


def search_songs_by_artist(artist_name, country):
  res = requests.get(
      "https://itunes.apple.com/search",
      params={
          "term": artist_name,
          "media": "music",
          "entity": "song",
          "limit": 100,
      },
      timeout=10,
  )
  res.raise_for_status()
  songs = [s for s in res.json().get("results", []) if s.get("previewUrl")]

  # 한국을 선택했을 때 동명이인이나 외국 가수가 섞여 나오는 것을 방지하기 위한 안전 필터
  if country == "한국":
    filtered = []
    for s in songs:
      artist_lower = s.get("artistName", "").lower()
      # 영문 아티스트명이나 명백히 외국 아티스트인 경우 제외 (단, 영어로 등록된 한국 가수 예외 처리를 위해 기본 키워드 대조)
      if not any(
          eng in artist_lower
          for eng in [
              "youngboy",
              "drake",
              "eminem",
              "justin",
              "taylor",
              "kanye",
              "bts",
              "blackpink",
          ]
      ):
        filtered.append(s)
    if filtered:
      songs = filtered

  return songs


def song_key(s):
  return f"{s['artistName'].lower()}|{s['trackName'].lower()}"


def youtube_link(song):
  query = quote(f"{song['artist']} {song['title']}")
  return f"https://www.youtube.com/results?search_query={query}"


def valid_link(url, hosts):
  if not url:
    return True
  p = urlparse(url)
  host = (p.hostname or "").lower()
  return p.scheme == "https" and any(
      host == h or host.endswith("." + h) for h in hosts
  )


@st.cache_resource
def get_lock():
  return threading.Lock()


def load_boards():
  if not DATA_FILE.exists():
    return {}
  try:
    return json.loads(DATA_FILE.read_text(encoding="utf-8"))
  except (json.JSONDecodeError, OSError):
    return {}


def save_boards(boards):
  tmp = DATA_FILE.with_suffix(".tmp")
  tmp.write_text(json.dumps(boards, ensure_ascii=False), encoding="utf-8")
  tmp.replace(DATA_FILE)


def hash_pin(pin):
  return hashlib.sha256(pin.encode("utf-8")).hexdigest()


def clean_nick(nick):
  for ch in "*_`[]()#<>~|\\":
    nick = nick.replace(ch, "")
  return nick.strip()


# ---------- 세션 상태 초기화 ----------
if "current" not in st.session_state:
  st.session_state.current = None
if "favorites" not in st.session_state:
  st.session_state.favorites = []
if "seen" not in st.session_state:
  st.session_state.seen = set()

# ---------- 화면 구성 ----------
st.title("🎵 오늘 노래 추천")
st.caption(
    "국가별 레전드 및 인기 아티스트의 명곡을 기분과 장르에 맞게 추천해 드립니다."
)

tab1, tab2, tab3 = st.tabs(["🎧 추천 받기", "❤️ 나의 음악리스트", "🗂️ 공유 서랍"])

# ---------- 탭 1: 추천 받기 ----------
with tab1:
  col1, col2 = st.columns(2)
  with col1:
    country = st.selectbox("🌍 음악 나라", list(ARTIST_DICTIONARY.keys()))
  with col2:
    mood = st.selectbox("✨ 오늘 기분", list(MOOD_GENRES.keys()))

  if st.button("🎵 맞춤 음악 추천받기", use_container_width=True):
    genre = random.choice(MOOD_GENRES[mood][country])
    artist_pool = MUSIC[country][genre]
    chosen_artist = random.choice(artist_pool)

    try:
      pool = search_songs_by_artist(chosen_artist, country)
    except requests.RequestException:
      pool = []
      st.error("음악 검색에 실패했어요. 잠시 후 다시 시도해 주세요.")

    seen = st.session_state.seen
    fresh = [s for s in pool if song_key(s) not in seen]
    if pool and not fresh:
      seen.clear()
      fresh = pool[:]
      st.info(
          f"'{chosen_artist}'의 모든 곡을 추천받아 기록을 산뜻하게"
          " 초기화했어요!"
      )

    if fresh:
      picked = random.choice(fresh)
      seen.add(song_key(picked))
      st.session_state.current = to_song(picked, f"{country} · {genre}")
    else:
      st.session_state.current = None
      st.warning(
          "조건에 맞는 곡을 찾지 못했어요. 버튼을 다시 한 번 눌러보세요!"
      )

  song = st.session_state.current
  if song:
    st.markdown("---")
    st.success(f"🎶 추천 트랙: **{song['title']}** - *{song['artist']}*")

    c_img, c_info = st.columns([1, 2])
    with c_img:
      st.image(song["image"], width=160)
    with c_info:
      info = []
      if song.get("genre"):
        info.append(f"🎼 장르: {song['genre']}")
      if song.get("year"):
        info.append(f"📅 발매: {song['year']}년")
      if info:
        st.write("\n\n".join(info))
      st.audio(song["preview"])
      st.link_button("▶️ 유튜브 전곡 검색", youtube_link(song))

    fav_ids = [f["id"] for f in st.session_state.favorites]
    if song["id"] in fav_ids:
      if st.button("❤️ 좋아요 취소", use_container_width=True):
        st.session_state.favorites = [
            f for f in st.session_state.favorites if f["id"] != song["id"]
        ]
        st.rerun()
    else:
      if st.button("🤍 좋아요 보관함에 담기", use_container_width=True):
        st.session_state.favorites.append(song)
        st.rerun()

# ---------- 탭 2: 나의 음악리스트 ----------
with tab2:
  with st.expander("📂 백업 파일에서 리스트 불러오기"):
    up = st.file_uploader("my_music_list.json 파일 업로드", type="json")
    if up is not None and st.button("불러오기 실행"):
      try:
        loaded = json.load(up)
        REQUIRED = {"id", "title", "artist", "image", "preview"}
        have = {f["id"] for f in st.session_state.favorites}
        new = [
            s
            for s in loaded
            if isinstance(s, dict) and REQUIRED <= s.keys() and s["id"] not in have
        ]
        st.session_state.favorites.extend(new)
        st.success(f"성공적으로 {len(new)}곡을 불러왔습니다!")
      except (json.JSONDecodeError, TypeError):
        st.error("올바른 형식의 파일이 아닙니다.")

  favs = st.session_state.favorites
  if not favs:
    st.info(
        "아직 좋아요한 노래가 없어요. 첫 번째 탭에서 마음에 드는 곡을 담아보세요!"
    )
  else:
    st.subheader(f"❤️ 나의 보관함 ({len(favs)}곡)")
    for f in favs:
      c1, c2, c3, c4 = st.columns([1, 4, 2, 1])
      c1.image(f["image"], width=50)
      c2.write(f"**{f['title']}**\n\n_{f['artist']}_")
      c3.link_button("유튜브 ▶️", youtube_link(f))
      if c4.button("🗑️", key=f"del_{f['id']}"):
        st.session_state.favorites = [
            x for x in favs if x["id"] != f["id"]
        ]
        st.rerun()
      st.audio(f["preview"])
      st.divider()

    st.subheader("📤 커뮤니티 공유 서랍에 올리기")
    nick = clean_nick(st.text_input("닉네임", max_chars=20, key="share_nick"))
    pin = st.text_input(
        "비밀번호 (4자리 이상, 수정/삭제 시 필요)",
        type="password",
        key="share_pin",
    )
    yt_url = st.text_input("유튜브 플레이리스트 링크 (선택)", key="share_yt").strip()
    sp_url = st.text_input(
        "스포티파이 플레이리스트 링크 (선택)", key="share_sp"
    ).strip()

    if st.button("서랍에 공유하기 🚀"):
      safe = [
          f
          for f in st.session_state.favorites
          if str(f.get("image", "")).startswith("https://")
          and str(f.get("preview", "")).startswith("https://")
      ][:MAX_SONGS]
      if not nick:
        st.error("닉네임을 입력해주세요.")
      elif len(pin) < 4:
        st.error("비밀번호는 4자리 이상이어야 해요.")
      elif not valid_link(yt_url, YT_HOSTS):
        st.error("올바른 유튜브 링크 형식이 아닙니다.")
      elif not valid_link(sp_url, SP_HOSTS):
        st.error("올바른 스포티파이 링크 형식이 아닙니다.")
      else:
        with get_lock():
          boards = load_boards()
          if nick in boards and boards[nick].get("pin") != hash_pin(pin):
            st.error(
                "이미 사용 중인 닉네임이거나 비밀번호가 올바르지 않습니다."
            )
          elif nick not in boards and len(boards) >= MAX_BOARDS:
            st.error("공유 서랍 용량이 가득 찼습니다.")
          else:
            boards[nick] = {
                "pin": hash_pin(pin),
                "songs": safe,
                "yt_url": yt_url,
                "sp_url": sp_url,
                "ts": time.time(),
            }
            save_boards(boards)
            st.success(f"'{nick}' 님의 리스트가 공유 서랍에 등록되었습니다!")

    st.divider()
    st.download_button(
        "💾 JSON 백업 파일 다운로드",
        json.dumps(favs, ensure_ascii=False, indent=2),
        file_name="my_music_list.json",
        mime="application/json",
    )
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["제목", "가수", "유튜브 링크"])
    for f in favs:
      writer.writerow([f["title"], f["artist"], youtube_link(f)])
    st.download_button(
        "📥 CSV 파일 다운로드 (엑셀용)",
        buf.getvalue().encode("utf-8-sig"),
        file_name="my_music_list.csv",
        mime="text/csv",
    )

# ---------- 탭 3: 공유 서랍 (삭제 기능 포함) ----------
with tab3:
  boards = load_boards()
  if not boards:
    st.info("아직 공유된 리스트가 없습니다. 첫 번째 주인공이 되어보세요!")
  else:
    st.caption(f"🗂️ 총 {len(boards)}개의 플레이리스트가 공유되어 있습니다.")

    with st.expander("🗑️ 내가 올린 공유 리스트 삭제하기"):
      del_nick = clean_nick(
          st.text_input("등록했던 닉네임", key="del_nick_input")
      )
      del_pin = st.text_input(
          "비밀번호", type="password", key="del_pin_input"
      )
      if st.button("공유 리스트 삭제 ⚠️"):
        with get_lock():
          boards_data = load_boards()
          if (
              del_nick in boards_data
              and boards_data[del_nick].get("pin") == hash_pin(del_pin)
          ):
            del boards_data[del_nick]
            save_boards(boards_data)
            st.success(f"'{del_nick}' 님의 공유 리스트가 삭제되었습니다.")
            st.rerun()
          else:
            st.error("닉네임이 존재하지 않거나 비밀번호가 일치하지 않습니다.")

    for name, board in sorted(
        boards.items(), key=lambda kv: kv[1].get("ts", 0), reverse=True
    ):
      songs = board.get("songs", [])
      with st.expander(f"🎧 {name} 님의 플레이리스트 ({len(songs)}곡)"):
        l1, l2 = st.columns(2)
        if board.get("yt_url"):
          l1.link_button("▶️ 유튜브 플레이리스트", board["yt_url"])
        if board.get("sp_url"):
          l2.link_button("🟢 스포티파이 플레이리스트", board["sp_url"])

        for sg in songs:
          c1, c2, c3 = st.columns([1, 4, 2])
          c1.image(sg["image"], width=50)
          c2.write(f"**{sg['title']}**\n\n_{sg['artist']}_")
          c3.link_button("유튜브 ▶️", youtube_link(sg))
          st.audio(sg["preview"])
        if songs and st.button("➕ 내 보관함에 전체 담기", key=f"take_{name}"):
          have = {f["id"] for f in st.session_state.favorites}
          new = [sg for sg in songs if sg["id"] not in have]
          st.session_state.favorites.extend(new)
          st.success(f"총 {len(new)}곡을 내 보관함에 추가했습니다!")