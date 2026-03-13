"""
PREMIER — Scoring Engine
Évalue le potentiel d'un artiste pour PREMIER.
"""


def score_profile(data: dict) -> dict:
    """Calcule le score PREMIER d'un profil artiste (0-10 par critère)."""
    followers = data.get("followers", 0)
    engagement = data.get("engagement_rate", 0.0)
    genres = data.get("genres", [])
    platforms = data.get("platforms", [])
    music_activity = data.get("music_activity_score", 0)
    is_verified = data.get("is_verified", False)
    posts = data.get("posts", [])

    # --- 1. Potentiel commercial (followers + vérification) ---
    if 5_000 <= followers <= 500_000:
        commercial = 8
    elif followers > 500_000:
        commercial = 6  # trop gros → moins accessible
    elif 1_000 <= followers < 5_000:
        commercial = 5
    else:
        commercial = 2

    if is_verified:
        commercial = min(10, commercial + 1)

    # --- 2. Engagement communauté ---
    if engagement >= 8:
        eng_score = 10
    elif engagement >= 5:
        eng_score = 8
    elif engagement >= 3:
        eng_score = 7
    elif engagement >= 2:
        eng_score = 5
    elif engagement >= 1:
        eng_score = 3
    else:
        eng_score = 1

    # --- 3. Qualité de contenu (activité musicale + plateformes) ---
    content_score = min(10, music_activity + len(platforms) * 2)

    # --- 4. Cohérence artistique (genre identifié + catégorie pro) ---
    coherence = 5
    if genres:
        coherence = min(10, coherence + len(genres) * 2)
    if data.get("is_business_account"):
        coherence = min(10, coherence + 1)
    if data.get("external_url"):
        coherence = min(10, coherence + 1)

    # --- 5. Opportunité de collaboration ---
    collab = 5
    target_genres = {"afro", "rnb", "rap_fr", "pop_urbaine", "amapiano"}
    if any(g in target_genres for g in genres):
        collab = min(10, collab + 3)
    if 5_000 <= followers <= 200_000:
        collab = min(10, collab + 2)
    if engagement >= 3:
        collab = min(10, collab + 1)

    # --- Score global ---
    global_score = round(
        (commercial * 0.25 + eng_score * 0.30 + content_score * 0.20 + coherence * 0.15 + collab * 0.10),
        1,
    )

    # --- Recommandation ---
    if global_score >= 7.5:
        recommandation = "CONTACTER RAPIDEMENT"
    elif global_score >= 5.5:
        recommandation = "À SURVEILLER"
    else:
        recommandation = "PAS PRIORITAIRE"

    data["score_premier"] = {
        "potentiel_commercial": commercial,
        "engagement": eng_score,
        "qualite_contenu": content_score,
        "coherence": coherence,
        "opportunite_collab": collab,
        "global": global_score,
        "recommandation": recommandation,
    }

    return data
