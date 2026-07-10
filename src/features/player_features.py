import pandas as pd
import math

from src.features.engagement import normalize_playtime
from datetime import date

def category_entropy(category_playtimes: dict[str, float]) -> float:
    total_playtime = sum(category_playtimes.values())

    if total_playtime == 0:
        return 0.0

    entropy = 0.0
    for minutes in category_playtimes.values():
        p_i = minutes / total_playtime
        if p_i > 0:
            entropy -= p_i * math.log(p_i)

    max_entropy = math.log(len(category_playtimes))
    return entropy / max_entropy if max_entropy > 0 else 0.0

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

    genre_playtimes = (df.explode("genres").groupby("genres")["playtime_minutes"].sum().to_dict())
    genre_entropy_value = category_entropy(genre_playtimes)

    # entropy is probably not the most complete choice here. going with a scalar loses information such as preferred developers. might revisit later
    developer_playtimes = (df.explode("developers").groupby("developers")["playtime_minutes"].sum().to_dict())
    developer_entropy_value = category_entropy(developer_playtimes)

    today = pd.Timestamp(date.today())
    df["release_date"] = pd.to_datetime(df["release_date"])
    ages_in_years = (today - df["release_date"]) / pd.Timedelta(days=365.25)
    average_game_age = ages_in_years.mean()

    # it's still missing the average review score

    return {"median": median_playtime, "std": std_playtime, "genre_entropy": genre_entropy_value, "developer_entropy_value": developer_entropy_value, "average_game_age": average_game_age}
