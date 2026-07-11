import re
import pandas as pd
from rapidfuzz import process, fuzz


def extract_trailing_number(title: str) -> int | None:
    if not title:
        return None

    cleaned = re.sub(r'[^A-Za-z0-9 ]', ' ', title).upper()
    tokens = cleaned.split()

    roman_map = {
        'I': 1, 'II': 2, 'III': 3, 'IV': 4, 'V': 5,
        'VI': 6, 'VII': 7, 'VIII': 8, 'IX': 9, 'X': 10,
        'XI': 11, 'XII': 12, 'XIII': 13, 'XIV': 14, 'XV': 15
    }

    for token in reversed(tokens):
        if token.isdigit():
            return int(token)
        if token in roman_map:
            return roman_map[token]

    return None


def is_plausible_match(original_title: str, candidate_title: str, candidate_release_date, score: float) -> bool:
    if score < 90:
        return False

    if extract_trailing_number(original_title) != extract_trailing_number(candidate_title):
        return False

    if candidate_release_date is not None and candidate_release_date.year > 2018:
        return False

    return True


def find_fuzzy_matches(conn) -> pd.DataFrame:
    unmatched_query = """
        SELECT DISTINCT bug.game_title
        FROM bulk_user_game bug
        LEFT JOIN bulk_games bg
            ON TRIM(regexp_replace(lower(bug.game_title), '[^a-z0-9 ]', '', 'g'))
             = TRIM(regexp_replace(lower(bg.title), '[^a-z0-9 ]', '', 'g'))
        WHERE bg.title IS NULL
    """
    unmatched = pd.read_sql(unmatched_query, conn)["game_title"].tolist()

    candidates_df = pd.read_sql("SELECT appid, title, release_date FROM bulk_games", conn)
    candidates_df["release_date"] = pd.to_datetime(candidates_df["release_date"], errors="coerce")
    candidate_titles = candidates_df["title"].tolist()

    results = []
    for title in unmatched:
        res = process.extractOne(title, candidate_titles, scorer=fuzz.ratio)
        if res is None:
            results.append((title, None, None, 0.0, False))
            continue

        match_title, score, index = res
        raw_date = candidates_df.iloc[index]["release_date"]
        candidate_date = raw_date if pd.notna(raw_date) else None
        appid = int(candidates_df.iloc[index]["appid"])

        plausible = is_plausible_match(title, match_title, candidate_date, score)
        results.append((title, match_title, appid, score, plausible))

    return pd.DataFrame(results, columns=["original", "best_match", "appid", "score", "is_plausible"])


def build_title_map(conn, verified_fuzzy_matches: pd.DataFrame | None = None):
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO bulk_title_map (game_title, appid, match_method, match_score)
            SELECT DISTINCT bug.game_title, bg.appid, 'exact', 100.0
            FROM bulk_user_game bug
            JOIN bulk_games bg ON bug.game_title = bg.title
            ON CONFLICT (game_title) DO NOTHING
        """)

        cur.execute("""
            INSERT INTO bulk_title_map (game_title, appid, match_method, match_score)
            SELECT DISTINCT bug.game_title, bg.appid, 'normalized', 95.0
            FROM bulk_user_game bug
            JOIN bulk_games bg
                ON TRIM(regexp_replace(lower(bug.game_title), '[^a-z0-9 ]', '', 'g'))
                 = TRIM(regexp_replace(lower(bg.title), '[^a-z0-9 ]', '', 'g'))
            WHERE bug.game_title NOT IN (SELECT game_title FROM bulk_title_map)
            ON CONFLICT (game_title) DO NOTHING
        """)
        conn.commit()

        if verified_fuzzy_matches is not None:
            for _, row in verified_fuzzy_matches.iterrows():
                cur.execute(
                    """
                    INSERT INTO bulk_title_map (game_title, appid, match_method, match_score)
                    VALUES (%s, %s, 'fuzzy', %s)
                    ON CONFLICT (game_title) DO NOTHING
                    """,
                    (row["original"], int(row["appid"]), row["score"])
                )
            conn.commit()