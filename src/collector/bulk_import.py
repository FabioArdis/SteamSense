import pandas as pd

RAW_CSV_PATH = "../data/raw/dataset.csv"
COLUMN_NAMES = ["user_id", "game_title", "behavior", "value", "unused"]

def load_bulk_dataset(conn):
    df = pd.read_csv(RAW_CSV_PATH, header=None, names=COLUMN_NAMES)

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