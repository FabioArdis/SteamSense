"""
recommender based on cosine-similarity KNN over the dataset population's feature vectors, aggregating neighbor-owned
games weighted by (similarity * playtime) into a ranked candidate list.

like previously mentioned in main.py, only games with a resolved appid via bulk_title_map can ever be recommended, so
a portion (~30%) of the unmatched titles are invisible to this step, even though they contributed to the similarity
score. thus, the pool of recommendable games is capped by the same title-matching coverage ceiling in title_matching.py,
not just by neighbor selection.
"""
import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity

from models.clustering import FEATURE_COLUMNS

def find_nearest_neighbors(vector: pd.DataFrame, population_matrix: pd.DataFrame, k: int = 50) -> pd.DataFrame:
    # compute cosine similarity between our target user and everyone else.
    # cosine_similarity is a 2d array and we just want the flat list of scores.
    similarities = cosine_similarity(vector[FEATURE_COLUMNS], population_matrix[FEATURE_COLUMNS])[0]

    result = population_matrix[["bulk_user_id"]].copy()
    result["similarity"] = similarities

    # highest similarity wins. sort it descending and chop off at k.
    return result.sort_values("similarity", ascending=False).head(k)

def recommend_games(engine, neighbors: pd.DataFrame, owned_appids: set[int], top_n: int = 10) -> pd.DataFrame:
    # aggregates games owned by the given neighbors, excluding games the target user already owns.
    # includes contributor_count per game so the user can distinguish a broadly-backed recommendation from one driven by
    # a single dominant neighbor.

    # interesting observation: contributor_count ceiling scales with k. at L=15, max contributor_count across all
    # candidates was 6. at k=50, it rose to 22, and the top recommendation shifted from a single-neighbor-dominated
    # result (driving ~80% of the score) to a broadly-supported one (7 contributors with a real playtime spread). thus,
    # k=50 was adopted as the default based on this improvement.

    # possible improvement: dampen individual contribution via a log transform on playtime_hours (the same way we
    # already do in features.engegement), so one neighbor's outsized playtime doesn't linearly dominate a game's score.
    neighbor_ids = tuple(neighbors["bulk_user_id"].tolist())

    query = """
        SELECT bug.bulk_user_id, bg.appid, bg.title, bug.playtime_hours
        FROM bulk_user_game bug
        JOIN bulk_title_map btm ON bug.game_title = btm.game_title
        JOIN bulk_games bg ON btm.appid = bg.appid
        WHERE bug.bulk_user_id IN %s
    """

    candidates = pd.read_sql(query, engine, params=(neighbor_ids,))

    # filter out the games the user already has in their library.
    candidates = candidates[~candidates["appid"].isin(owned_appids)]

    # merge adds in the similarity scores we calculated earlier.
    candidates = candidates.merge(neighbors, on="bulk_user_id")

    # create the weighted score field by similarity and playtime.
    candidates["weighted_score"] = candidates["similarity"] * candidates["playtime_hours"]

    # debug output to see the distribution of how many neighbors own what.
    neighbor_game_counts = candidates.groupby(["appid", "title"])["bulk_user_id"].nunique().sort_values(ascending=False)
    print(neighbor_game_counts.describe())
    print(neighbor_game_counts.head(20))

    # group it all together by game, sum up the weighted scores and count how many unique neighbors actually pitched in.
    scored = (
        candidates.groupby(["appid", "title"])
        .agg(
            weighted_score=("weighted_score", "sum"),
            contributor_count=("bulk_user_id", "nunique"),
        )
        .reset_index()
        .sort_values("weighted_score", ascending=False)
    )

    return scored.head(top_n)

def explain_recommendation(engine, neighbors: pd.DataFrame, appid: int) -> pd.DataFrame:
    # there's an important observation: since contribution scales with raw playtime, a singe neighbor with both high
    # similarity and very high playtime can dominate a game's total score almost entirely, even with few other neighbors
    # own it. this roughly translates to "one very-similar neighbor is very obsessed with this", rather than
    # "recommended because similar players liked this".

    neighbor_ids = tuple(neighbors["bulk_user_id"].tolist())

    query = """
        SELECT bug.bulk_user_id, bug.playtime_hours
        FROM bulk_user_game bug
        JOIN bulk_title_map btm ON bug.game_title = btm.game_title
        WHERE btm.appid = %s AND bug.bulk_user_id IN %s
    """
    contributors = pd.read_sql(query, engine, params=(appid, neighbor_ids))

    # put the similarity scores back in so we can do the math.
    contributors = contributors.merge(neighbors, on="bulk_user_id")

    # calculate exactly how much score each neighbor brought to the table.
    contributors["contribution"] = contributors["similarity"] * contributors["playtime_hours"]

    return contributors.sort_values("contribution", ascending=False)