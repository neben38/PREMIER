"""
PREMIER — Meta Ad Library Scraper
Trouve les artistes qui font de la pub payante pour leur musique sur Instagram.
Sortie : liste de @usernames uniquement.

Deux modes :
  1. API officielle Meta (nécessite un access token)
  2. Scraping HTML de la bibliothèque publique (sans token)

Usage :
  python ad_library_scraper.py --countries FR BE CI --keywords spotify clip single
  python ad_library_scraper.py --token VOTRE_TOKEN --countries FR
"""

import argparse
import json
import time
import re
import sys
from pathlib import Path

try:
    import requests
except ImportError:
    print("pip install requests")
    raise

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

MUSIC_KEYWORDS = [
    "single", "clip", "disponible", "streaming", "spotify", "écouter",
    "out now", "apple music", "deezer", "youtube", "ep", "album",
    "nouveau son", "new music", "feat", "prod",
]

TARGET_COUNTRIES = ["FR", "BE", "CH", "CI", "SN", "CM", "MA"]

AD_LIBRARY_API = "https://graph.facebook.com/v19.0/ads_archive"

OUTPUT_FILE = Path(__file__).parent.parent / "data" / "usernames.txt"

# ---------------------------------------------------------------------------
# Mode 1 : API officielle Meta (avec access token)
# ---------------------------------------------------------------------------

def fetch_via_api(token: str, countries: list[str], keywords: list[str]) -> list[str]:
    """
    Appelle l'API Meta Ads Library et retourne les usernames Instagram trouvés.
    Nécessite un token Meta Graph avec la permission ads_read.
    Obtenir un token : https://developers.facebook.com/tools/explorer/
    """
    usernames = set()

    for keyword in keywords:
        params = {
            "access_token": token,
            "ad_type": "ALL",
            "ad_active_status": "ACTIVE",
            "search_terms": keyword,
            "ad_reached_countries": json.dumps(countries),
            "fields": "page_name,publisher_platforms,ad_creative_link_captions,ad_snapshot_url",
            "limit": 100,
        }

        while True:
            resp = requests.get(AD_LIBRARY_API, params=params, timeout=15)
            if resp.status_code != 200:
                print(f"[API] Erreur {resp.status_code} pour '{keyword}'", file=sys.stderr)
                break

            data = resp.json()
            ads = data.get("data", [])

            for ad in ads:
                platforms = ad.get("publisher_platforms", [])
                if "instagram" not in platforms:
                    continue
                username = extract_username_from_ad(ad)
                if username:
                    usernames.add(username)

            # Pagination
            next_page = data.get("paging", {}).get("next")
            if not next_page:
                break
            params = {"access_token": token, "after": data["paging"]["cursors"]["after"]}
            time.sleep(1)

    return sorted(usernames)


def extract_username_from_ad(ad: dict) -> str | None:
    """Tente d'extraire le @username Instagram depuis les données d'une pub."""
    # snapshot_url contient souvent l'ig_username en query param
    snapshot = ad.get("ad_snapshot_url", "")
    match = re.search(r"ig_username=([^&]+)", snapshot)
    if match:
        return "@" + match.group(1)

    # Fallback : page_name nettoyé (approximatif)
    page_name = ad.get("page_name", "")
    if page_name:
        slug = re.sub(r"[^a-zA-Z0-9._]", "", page_name.lower())
        if slug:
            return "@" + slug

    return None


# ---------------------------------------------------------------------------
# Mode 2 : Scraping HTML public (sans token)
# ---------------------------------------------------------------------------

def fetch_via_scraping(countries: list[str], keywords: list[str]) -> list[str]:
    """
    Scrape la page publique Meta Ad Library.
    Moins fiable que l'API mais ne nécessite pas de token.
    """
    usernames = set()
    session = requests.Session()
    session.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (X11; Linux x86_64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept-Language": "fr-FR,fr;q=0.9",
    })

    for country in countries:
        for keyword in keywords:
            url = (
                f"https://www.facebook.com/ads/library/"
                f"?active_status=active"
                f"&ad_type=all"
                f"&country={country}"
                f"&q={requests.utils.quote(keyword)}"
                f"&media_type=all"
            )

            try:
                resp = session.get(url, timeout=15)
            except requests.RequestException as e:
                print(f"[scrape] Erreur réseau ({country}, '{keyword}'): {e}", file=sys.stderr)
                continue

            # Extraction des ig_username depuis le HTML brut
            found = re.findall(r'"ig_username"\s*:\s*"([^"]+)"', resp.text)
            for u in found:
                usernames.add("@" + u)

            # Extraction depuis les URLs snapshot
            found_urls = re.findall(r'ig_username=([^&\\"]+)', resp.text)
            for u in found_urls:
                usernames.add("@" + u)

            time.sleep(2)

    return sorted(usernames)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="PREMIER — Trouve les artistes qui font de la pub Instagram pour leur musique"
    )
    parser.add_argument(
        "--token",
        help="Access token Meta Graph (optionnel — active le mode API officiel)",
        default=None,
    )
    parser.add_argument(
        "--countries",
        nargs="+",
        default=TARGET_COUNTRIES,
        help=f"Codes pays ISO (défaut: {' '.join(TARGET_COUNTRIES)})",
    )
    parser.add_argument(
        "--keywords",
        nargs="+",
        default=MUSIC_KEYWORDS[:6],
        help="Mots-clés à rechercher dans les pubs",
    )
    args = parser.parse_args()

    print(f"Pays cibles : {', '.join(args.countries)}")
    print(f"Mots-clés   : {', '.join(args.keywords)}")
    print()

    if args.token:
        print("Mode : API officielle Meta")
        usernames = fetch_via_api(args.token, args.countries, args.keywords)
    else:
        print("Mode : scraping public (sans token)")
        print("Conseil : utilise --token pour des résultats plus fiables\n")
        usernames = fetch_via_scraping(args.countries, args.keywords)

    if not usernames:
        print("Aucun username trouvé.")
        return

    # Affichage
    print(f"\n{len(usernames)} compte(s) trouvé(s) :\n")
    for u in usernames:
        print(u)

    # Sauvegarde
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(usernames) + "\n")

    print(f"\nSauvegardé → {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
