import pandas as pd

from src.features.engagement import normalize_playtime


def build_player_features(conn, steam_id: str) -> dict:
    query = """
        SELECT
            ug.appid,
            ug.playtime_minutes,
            ug.achievements_unlocked,
            g.genres,
            g.developers,
            g.publishers,
            g.release_date,
            g.total_achievements
        FROM user_game ug
        JOIN games g ON ug.appid = g.appid
        WHERE ug.steam_id = %s
    """
    df = pd.read_sql(query, conn, params=(steam_id,))

    # repurposing the single-game normalizer from features.engagement
    median_playtime = normalize_playtime(df["playtime_minutes"].median())
    std_playtime = normalize_playtime(df["playtime_minutes"].std(ddof=0))

    return {"median": median_playtime, "std": std_playtime}
