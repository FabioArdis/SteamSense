from datetime import datetime
import time

from sqlalchemy import create_engine

import psycopg2

from src.collector.exceptions import SteamAPIError, StoreGameNotFound, AchievementsNotFound, ReviewsNotFound
from src.collector.steam_client import SteamClient


def get_connection(host: str, port: int, dbname: str, user: str, password: str):
    try:
        conn = psycopg2.connect(host=host, port=port, dbname=dbname, user=user, password=password)
        return conn
    except Exception as e:
        raise Exception(f"Database connection failed: {str(e)}")

# we need an SQLAlchemy engine or pandas will complain.
def get_engine(host: str, port: int, dbname: str, user: str, password: str):
    try:
        return create_engine(f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{dbname}")
    except Exception as e:
        raise Exception(f"Engine creation failed: {str(e)}")

def is_game_cached(conn, appid: int) -> bool:
    with conn.cursor() as cur:
        cur.execute("""
            SELECT 1 FROM games 
            WHERE appid = %s AND title IS NOT NULL AND developers != '{}' AND positive_reviews IS NOT NULL
        """, (appid,))
        return cur.fetchone() is not None


def sync_owned_games(client: SteamClient, conn, steam_id: str):
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO users (steam_id) VALUES (%s) ON CONFLICT (steam_id) DO NOTHING",
            (steam_id,)
        )
        conn.commit()

        try:
            owned_games = client.get_owned_games(steam_id)
        except SteamAPIError as e:
            print(f"Failed to fetch owned games for steam_id {steam_id}: {e}")
            return

        for game in owned_games:
            appid = game["appid"]

            if not is_game_cached(conn, appid):
                try:
                    details = client.get_app_details(appid)[str(appid)]["data"]

                    genres = [g["description"] for g in details.get("genres", [])]
                    developers = details.get("developers", [])
                    publishers = details.get("publishers", [])
                    metacritic = details.get("metacritic", {}).get("score")
                    total_achievements = details.get("achievements", {}).get("total", 0)
                    price_overview = details.get("price_overview")
                    price = price_overview["final"] if price_overview else None
                    release_date_raw = details.get("release_date", {}).get("date")

                    release_date_parsed = None
                    try:
                        release_date_parsed = datetime.strptime(release_date_raw, "%d %b, %Y").date()
                    except (ValueError, TypeError):
                        print(f"Failed to parse release date '{release_date_raw}' for appid {appid}")

                    positive_reviews = negative_reviews = None
                    try:
                        reviews = client.get_app_reviews(appid)
                        positive_reviews = reviews["total_positive"]
                        negative_reviews = reviews["total_negative"]
                    except (ReviewsNotFound, SteamAPIError) as e:
                        print(f"Failed to fetch reviews for appid {appid}: {e}")

                    cur.execute(
                        """
                        INSERT INTO games (appid, title, release_date, price, genres, developers, publishers, metacritic, positive_reviews, negative_reviews, total_achievements)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        ON CONFLICT (appid) DO UPDATE SET
                            title = excluded.title,
                            release_date = excluded.release_date,
                            price = excluded.price,
                            genres = excluded.genres, 
                            developers = excluded.developers,
                            publishers = excluded.publishers,
                            metacritic = excluded.metacritic,
                            positive_reviews = excluded.positive_reviews,
                            negative_reviews = excluded.negative_reviews,
                            total_achievements = excluded.total_achievements,
                            updated_at = CURRENT_TIMESTAMP
                        """,
                        (appid, details["name"], release_date_parsed, price, genres, developers, publishers, metacritic, positive_reviews, negative_reviews, total_achievements)
                    )
                    conn.commit()

                except (StoreGameNotFound, SteamAPIError) as e:
                    print(f"Failed to fetch store details for appid {appid}: {e}")
                    cur.execute(
                        "INSERT INTO games (appid) VALUES (%s) ON CONFLICT (appid) DO NOTHING",
                        (appid,)
                    )
                    conn.commit()

                time.sleep(1)  # only rate-limit when we actually hit the Store API

            # playtime data comes from get_owned_games, not appdetails,
            # so this insert happens regardless of metadata fetch success
            playtime_minutes = game.get("playtime_forever", 0)
            last_played_raw = game.get("rtime_last_played")
            last_played = datetime.fromtimestamp(last_played_raw).date() if last_played_raw else None

            achievements_unlocked = None
            try:
                ach = client.get_player_achievements(steam_id, appid)
                achievements_unlocked = sum(1 for a in ach if a["achieved"] == 1)
                time.sleep(1)
            except (SteamAPIError, AchievementsNotFound) as e:
                print(f"Exception caught while fetching achievements for appid {appid}: {e}")

            cur.execute(
                """
                INSERT INTO user_game (steam_id, appid, playtime_minutes, last_played, achievements_unlocked)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (steam_id, appid) DO UPDATE SET
                    playtime_minutes = EXCLUDED.playtime_minutes,
                    last_played = EXCLUDED.last_played,
                    achievements_unlocked = EXCLUDED.achievements_unlocked,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (steam_id, appid, playtime_minutes, last_played, achievements_unlocked)
            )
            conn.commit()