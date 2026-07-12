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

def build_player_features(engine, steam_id: str) -> dict:
    query = """
        SELECT
            ug.appid,
            ug.playtime_minutes,
            ug.achievements_unlocked,
            g.genres,
            g.developers,
            g.publishers,
            g.release_date,
            g.total_achievements,
            g.positive_reviews,
            g.negative_reviews
        FROM user_game ug
        JOIN games g ON ug.appid = g.appid
        WHERE ug.steam_id = %s
    """
    df = pd.read_sql(query, engine, params=(steam_id,))

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

    total_reviews = df["positive_reviews"] + df["negative_reviews"]
    review_ratio = df["positive_reviews"] / total_reviews.where(total_reviews > 0)
    average_review_score = review_ratio.mean()

    return {"median": median_playtime, "std": std_playtime, "genre_entropy": genre_entropy_value, "developer_entropy_value": developer_entropy_value, "average_game_age": average_game_age, "average_review_score": average_review_score}

def build_bulk_player_features(engine, bulk_user_id) -> dict:
    query = """
            SELECT bug.game_title,
                   bug.playtime_hours,
                   bg.genres,
                   bg.developers,
                   bg.release_date,
                   bg.positive_reviews,
                   bg.negative_reviews
            FROM bulk_user_game bug
                     LEFT JOIN bulk_title_map btm ON bug.game_title = btm.game_title
                     LEFT JOIN bulk_games bg ON btm.appid = bg.appid
            WHERE bug.bulk_user_id = %s
            """
    df = pd.read_sql(query, engine, params=(bulk_user_id,))

    matched_mask = df["genres"].notna()
    total_playtime = df["playtime_hours"].sum()
    match_coverage = (
            df.loc[matched_mask, "playtime_hours"].sum() / total_playtime
            if total_playtime > 0 else 0.0
    )

    playtime_minutes = df["playtime_hours"] * 60
    median_playtime = normalize_playtime(playtime_minutes.median())
    std_playtime = normalize_playtime(playtime_minutes.std(ddof=0))

    matched_df = df[matched_mask]

    MIN_MATCHED_GAMES = 3

    matched_games_count = matched_df["game_title"].nunique()
    insufficient_data = matched_games_count < MIN_MATCHED_GAMES

    genre_playtimes = (
        matched_df.explode("genres")
        .groupby("genres")["playtime_hours"].sum()
        .to_dict()
    )
    genre_entropy_value = None if insufficient_data else category_entropy(genre_playtimes)

    developer_playtimes = (
        matched_df.explode("developers")
        .groupby("developers")["playtime_hours"].sum()
        .to_dict()
    )
    developer_entropy_value = None if insufficient_data else category_entropy(developer_playtimes)

    today = pd.Timestamp(pd.Timestamp.today().date())
    matched_df["release_date"] = pd.to_datetime(matched_df["release_date"])
    ages_in_years = (today - matched_df["release_date"]) / pd.Timedelta(days=365.25)
    average_game_age = None if insufficient_data else ages_in_years.mean()

    total_reviews = matched_df["positive_reviews"] + matched_df["negative_reviews"]
    review_ratio = matched_df["positive_reviews"] / total_reviews.where(total_reviews > 0)
    average_review_score = None if insufficient_data else review_ratio.mean()

    return {
        "match_coverage": match_coverage,
        "median_playtime": median_playtime,
        "std_playtime": std_playtime,
        "genre_entropy": genre_entropy_value,
        "developer_entropy": developer_entropy_value,
        "average_game_age": average_game_age,
        "average_review_score": average_review_score,
    }

def build_all_bulk_player_features(engine) -> pd.DataFrame:
    user_ids = pd.read_sql("SELECT DISTINCT bulk_user_id FROM bulk_user_game", engine)["bulk_user_id"].tolist()

    rows = []
    for uid in user_ids:
        features = build_bulk_player_features(engine, bulk_user_id=uid)
        features["bulk_user_id"] = uid
        rows.append(features)

    return pd.DataFrame(rows)