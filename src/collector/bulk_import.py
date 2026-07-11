import pandas as pd
from psycopg2.extras import execute_values

USER_GAME_DATASET_PATH = "../data/raw/user_game_dataset.csv"
USER_GAME_DATASET_COLS = ["user_id", "game_title", "behavior", "value", "unused"]

GAMES_DATASET_PATH = "../data/raw/games_dataset.csv"
GAMES_DATASET_COLS = ["appid", "name", "release_date", "genres", "price", "developer", "publisher"]

def load_user_game_dataset(conn):
    df = pd.read_csv(USER_GAME_DATASET_PATH, header=None, names=USER_GAME_DATASET_COLS)

    play_rows = df[df["behavior"] == "play"]

    with conn.cursor() as cur:
        for _, row in play_rows.iterrows():
            cur.execute(
                """
                INSERT INTO bulk_user_game (bulk_user_id, game_title, playtime_hours) 
                VALUES (%s, %s, %s)
                ON CONFLICT (bulk_user_id, game_title) DO NOTHING
                """,
                (int(row["user_id"]), row["game_title"], row["value"])
            )
        conn.commit()

def load_games_dataset(conn):
    df = pd.read_csv(GAMES_DATASET_PATH)

    rows_to_insert = []
    skipped = 0

    for _, row in df.iterrows():
        try:
            genres = row["Genres"].split(",") if pd.notna(row["Genres"]) else []
            tags = row["Tags"].split(",") if pd.notna(row["Tags"]) else []
            developers = row["Developers"].split(";") if pd.notna(row["Developers"]) else []
            publishers = row["Publishers"].split(";") if pd.notna(row["Publishers"]) else []
            metacritic = row["Metacritic score"] if row["Metacritic score"] > 0 else None
            price = round(row["Price"] * 100)
            positive_reviews = row["Positive"] if pd.notna(row["Positive"]) else None
            negative_reviews = row["Negative"] if pd.notna(row["Negative"]) else None
            total_achievements = row["Achievements"] if pd.notna(row["Achievements"]) else None

            try:
                release_date = pd.to_datetime(row["Release date"], errors="raise").date()
            except (ValueError, TypeError):
                release_date = None

            rows_to_insert.append((
                int(row["AppID"]), row["Name"], release_date, price, genres, tags,
                developers, publishers, row["Recommendations"], metacritic,
                positive_reviews, negative_reviews, total_achievements
            ))
        except Exception as e:
            print(f"Skipped appid {row.get('AppID', '?')}: {e}")
            skipped += 1

    print(f"Parsed {len(rows_to_insert)} rows, skipped {skipped}")

    with conn.cursor() as cur:
        execute_values(
            cur,
            """
            INSERT INTO bulk_games (appid, title, release_date, price, genres, tags, developers, publishers, recommendations, metacritic, positive_reviews, negative_reviews, total_achievements)
            VALUES %s
            ON CONFLICT (appid) DO NOTHING
            """,
            rows_to_insert
        )
        conn.commit()