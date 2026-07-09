import math

CEILING_MINUTES = 200 * 60

def normalize_playtime(playtime_minutes: int) -> float:
    log_playtime = math.log1p(playtime_minutes)
    log_ceiling = math.log1p(CEILING_MINUTES)
    return min(log_playtime / log_ceiling, 1.0)

def compute_engagement_score(playtime_minutes: int, achievements_unlocked: int | None, total_achievements: int) -> float:
    # this is actually temporary, we are still missing an extra weight: the reviews
    # the final weights will be playtime: 0.5, achievements: 0.3, reviews: 0.2
    components = [(normalize_playtime(playtime_minutes), 0.7)]

    if achievements_unlocked is not None and total_achievements > 0:
        components.append((achievements_unlocked / total_achievements, 0.3))

    total_weight = sum(w for _, w in components)
    return sum(v * w for v, w in components) / total_weight

def update_engagement_score(conn):
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT 
                ug.steam_id, 
                ug.appid, 
                ug.playtime_minutes, 
                ug.achievements_unlocked, 
                g.total_achievements
            FROM user_game ug
            JOIN games g ON ug.appid = g.appid
                """
        )
        # alias are needed since appid share the same name
        rows = cur.fetchall()

        # if not rows? simply there's no work left to do

        for steam_id, appid, playtime_minutes, achievements_unlocked, total_achievements in rows:
            score = compute_engagement_score(playtime_minutes, achievements_unlocked, total_achievements)
            cur.execute(
                """
                UPDATE user_game AS ug
                SET
                    engagement_score = %s,
                    updated_at = CURRENT_TIMESTAMP
                WHERE ug.steam_id = %s AND ug.appid = %s
                """,
                (score, steam_id, appid)
            )
            conn.commit()