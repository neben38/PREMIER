"""
PREMIER — Instagram Artist Scraper
Scrape des profils artistes publics depuis Instagram.
Utilise Instaloader pour accéder aux données publiques.
"""

import time
import json
import logging
import random
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Optional

try:
    import instaloader
except ImportError:
    print("Installe les dépendances : pip install -r requirements.txt")
    raise

from profile_parser import parse_profile
from scorer import score_profile

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("premier.scraper")

DATA_DIR = Path(__file__).parent.parent / "data"
PROFILES_DIR = DATA_DIR / "profiles"
PROFILES_DIR.mkdir(parents=True, exist_ok=True)


@dataclass
class ScraperConfig:
    # Délais entre requêtes (secondes) pour éviter les bans
    min_delay: float = 3.0
    max_delay: float = 8.0
    # Nombre de posts à analyser par profil
    max_posts: int = 12
    # Session Instagram (optionnel, améliore les résultats)
    session_file: Optional[str] = None


class PremierScraper:
    def __init__(self, config: ScraperConfig = None):
        self.config = config or ScraperConfig()
        self.loader = instaloader.Instaloader(
            download_pictures=False,
            download_videos=False,
            download_video_thumbnails=False,
            download_geotags=False,
            download_comments=False,
            save_metadata=False,
            compress_json=False,
            quiet=True,
        )
        self._load_session()

    def _load_session(self):
        if self.config.session_file:
            try:
                self.loader.load_session_from_file(
                    username=None,
                    filename=self.config.session_file,
                )
                log.info("Session Instagram chargée.")
            except Exception as e:
                log.warning(f"Session non chargée : {e}")

    def _wait(self):
        delay = random.uniform(self.config.min_delay, self.config.max_delay)
        log.debug(f"Pause {delay:.1f}s...")
        time.sleep(delay)

    def scrape(self, username: str) -> dict:
        """Scrape un profil artiste et retourne les données structurées."""
        username = username.lstrip("@").strip()
        log.info(f"Scraping @{username}...")

        try:
            profile = instaloader.Profile.from_username(
                self.loader.context, username
            )
        except instaloader.exceptions.ProfileNotExistsException:
            log.error(f"Profil @{username} introuvable.")
            return {"error": "Profil introuvable", "username": username}
        except instaloader.exceptions.LoginRequiredException:
            log.error(f"@{username} : connexion requise (profil privé).")
            return {"error": "Profil privé", "username": username}
        except Exception as e:
            log.error(f"Erreur pour @{username} : {e}")
            return {"error": str(e), "username": username}

        self._wait()

        # Récupération des posts récents
        posts_data = []
        try:
            for i, post in enumerate(profile.get_posts()):
                if i >= self.config.max_posts:
                    break
                posts_data.append({
                    "date": str(post.date_utc),
                    "likes": post.likes,
                    "comments": post.comments,
                    "caption": (post.caption or "")[:300],
                    "is_video": post.is_video,
                    "video_view_count": getattr(post, "video_view_count", None),
                    "typename": post.typename,
                })
                self._wait()
        except Exception as e:
            log.warning(f"Erreur lors de la récup des posts : {e}")

        raw_data = {
            "username": profile.username,
            "full_name": profile.full_name,
            "biography": profile.biography,
            "external_url": profile.external_url,
            "followers": profile.followers,
            "followees": profile.followees,
            "mediacount": profile.mediacount,
            "is_verified": profile.is_verified,
            "is_business_account": profile.is_business_account,
            "business_category_name": getattr(profile, "business_category_name", None),
            "posts": posts_data,
        }

        parsed = parse_profile(raw_data)
        scored = score_profile(parsed)

        output_path = PROFILES_DIR / f"{username}.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(scored, f, ensure_ascii=False, indent=2)

        log.info(f"Profil @{username} sauvegardé → {output_path}")
        return scored

    def batch_scrape(self, usernames: list[str]) -> list[dict]:
        """Scrape une liste de profils."""
        results = []
        for i, username in enumerate(usernames, 1):
            log.info(f"[{i}/{len(usernames)}] @{username}")
            result = self.scrape(username)
            results.append(result)
            if i < len(usernames):
                self._wait()
        return results


def print_fiche(data: dict):
    """Affiche une fiche profil formatée en console."""
    if "error" in data:
        print(f"\n❌ Erreur : {data['error']} (@{data.get('username', '?')})")
        return

    score = data.get("score_premier", {})
    print(f"""
╔══════════════════════════════════════════════════╗
║  FICHE ARTISTE PREMIER                          ║
╠══════════════════════════════════════════════════╣
  @{data.get('username')} — {data.get('full_name')}
  Bio : {data.get('biography', '')[:80]}
  Lien : {data.get('external_url', 'N/A')}

  Followers : {data.get('followers', 0):,}
  Posts     : {data.get('mediacount', 0):,}
  Engagement: {data.get('engagement_rate', 0):.2f}%
  Vérifié   : {'✓' if data.get('is_verified') else '✗'}

  Genre(s)  : {', '.join(data.get('genres', [])) or 'N/D'}
  Catégorie : {data.get('business_category_name') or 'N/D'}

━━━━━━━━━━━━ SCORE PREMIER ━━━━━━━━━━━━
  Potentiel commercial    : {score.get('potentiel_commercial', 0)}/10
  Engagement communauté   : {score.get('engagement', 0)}/10
  Qualité de contenu      : {score.get('qualite_contenu', 0)}/10
  Cohérence artistique    : {score.get('coherence', 0)}/10
  Opportunité collab      : {score.get('opportunite_collab', 0)}/10

  SCORE GLOBAL : {score.get('global', 0)}/10
  RECOMMANDATION : {score.get('recommandation', 'N/D')}
╚══════════════════════════════════════════════════╝
""")


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python instagram_scraper.py @username1 [@username2 ...]")
        sys.exit(1)

    usernames = [u.lstrip("@") for u in sys.argv[1:]]
    scraper = PremierScraper()

    if len(usernames) == 1:
        result = scraper.scrape(usernames[0])
        print_fiche(result)
        print("\n📦 JSON export :")
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        results = scraper.batch_scrape(usernames)
        for r in results:
            print_fiche(r)
        print(f"\n✅ {len(results)} profils scrapés — sauvegardés dans data/profiles/")
