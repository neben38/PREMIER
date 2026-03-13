"""
PREMIER — Profile Parser
Analyse et enrichit les données brutes d'un profil Instagram.
"""

import re
from datetime import datetime, timezone


GENRE_KEYWORDS = {
    "afro": ["afro", "afrobeats", "afropop", "afrobeat"],
    "rnb": ["r&b", "rnb", "r'n'b", "soul", "neo soul"],
    "rap_fr": ["rap", "trap", "drill", "rap français", "rappeur", "rappeuse"],
    "pop_urbaine": ["pop urbaine", "urban", "urbain"],
    "amapiano": ["amapiano", "piano"],
    "dancehall": ["dancehall", "reggaeton", "caribbean"],
    "gospel": ["gospel", "worship", "louange"],
}

PLATFORM_KEYWORDS = ["spotify", "apple music", "deezer", "youtube", "soundcloud", "tidal", "boomplay"]

MUSIC_KEYWORDS = ["single", "album", "ep", "clip", "feat.", "ft.", "collab", "featuring",
                  "prod.", "beats", "studio", "recording", "mix", "mastering", "sortie",
                  "disponible", "streaming", "available", "out now", "new music"]


def detect_genres(text: str) -> list[str]:
    text_lower = text.lower()
    found = []
    for genre, keywords in GENRE_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            found.append(genre)
    return found


def detect_platforms(text: str) -> list[str]:
    text_lower = text.lower()
    return [p for p in PLATFORM_KEYWORDS if p in text_lower]


def detect_hashtags(captions: list[str]) -> list[str]:
    all_tags = []
    for caption in captions:
        all_tags.extend(re.findall(r"#\w+", caption.lower()))
    freq = {}
    for tag in all_tags:
        freq[tag] = freq.get(tag, 0) + 1
    return sorted(freq, key=freq.get, reverse=True)[:15]


def calc_engagement_rate(followers: int, posts: list[dict]) -> float:
    if not followers or not posts:
        return 0.0
    total_interactions = sum(p.get("likes", 0) + p.get("comments", 0) for p in posts)
    avg_interactions = total_interactions / len(posts)
    return round((avg_interactions / followers) * 100, 2)


def estimate_post_frequency(posts: list[dict]) -> str:
    if len(posts) < 2:
        return "N/D"
    try:
        dates = sorted([datetime.fromisoformat(p["date"].replace("Z", "+00:00")) for p in posts], reverse=True)
        if len(dates) >= 2:
            delta = (dates[0] - dates[-1]).days
            if delta == 0:
                return "N/D"
            posts_per_week = round((len(dates) / delta) * 7, 1)
            if posts_per_week >= 5:
                return "Très actif (5+ /semaine)"
            elif posts_per_week >= 2:
                return f"Actif ({posts_per_week} /semaine)"
            elif posts_per_week >= 0.5:
                return "Modéré (1-2 /semaine)"
            else:
                return "Peu actif (< 1/semaine)"
    except Exception:
        pass
    return "N/D"


def detect_content_types(posts: list[dict]) -> list[str]:
    types = set()
    for p in posts:
        typename = p.get("typename", "")
        if p.get("is_video"):
            if typename == "GraphVideo":
                types.add("Reels/Vidéos")
        else:
            types.add("Posts image")
    return list(types) or ["N/D"]


def parse_profile(raw: dict) -> dict:
    """Enrichit un profil brut avec les données analysées."""
    bio = raw.get("biography", "") or ""
    posts = raw.get("posts", [])
    captions = [p.get("caption", "") for p in posts if p.get("caption")]
    all_text = bio + " " + " ".join(captions)

    last_post_date = None
    if posts:
        try:
            last_post_date = sorted([p["date"] for p in posts], reverse=True)[0]
        except Exception:
            pass

    return {
        **raw,
        "genres": detect_genres(all_text),
        "platforms": detect_platforms(all_text),
        "top_hashtags": detect_hashtags(captions),
        "engagement_rate": calc_engagement_rate(raw.get("followers", 0), posts),
        "post_frequency": estimate_post_frequency(posts),
        "content_types": detect_content_types(posts),
        "last_post_date": last_post_date,
        "music_activity_score": sum(1 for kw in MUSIC_KEYWORDS if kw in all_text.lower()),
    }
