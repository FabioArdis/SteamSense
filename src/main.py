"""
this is a scratch script, where i run the pipeline on demand. most of the stages below are commented out since they're
either one-time or expensive. uncomment the relevant block to re-run a specific stage.
"""
from dotenv import load_dotenv
import os

from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
import matplotlib.pyplot as plt

from models.clustering import build_clustering_matrix, find_best_k, FEATURE_COLUMNS, assign_to_cluster, explain_cluster_assignment, build_live_vector
from models.recommender import find_nearest_neighbors, recommend_games, explain_recommendation
from src.collector.bulk_import import load_games_dataset
from src.collector.steam_client import SteamClient
from src.collector.sync import get_connection, sync_owned_games, get_engine
from src.collector.title_matching import find_fuzzy_matches, build_title_map
from src.features.engagement import update_engagement_score
from src.features.player_features import build_player_features, build_bulk_player_features, \
    build_all_bulk_player_features, get_or_build_bulk_features, get_owned_appids

load_dotenv()

client = SteamClient(api_key=os.environ["STEAM_API_KEY"])
conn = get_connection(host=os.environ["POSTGRES_HOST"], port=int(os.environ["POSTGRES_PORT"]), dbname=os.environ["POSTGRES_DB"], user=os.environ["POSTGRES_USER"], password=os.environ["POSTGRES_PASSWORD"])
engine = get_engine(host=os.environ["POSTGRES_HOST"], port=int(os.environ["POSTGRES_PORT"]), dbname=os.environ["POSTGRES_DB"], user=os.environ["POSTGRES_USER"], password=os.environ["POSTGRES_PASSWORD"])
#sync_owned_games(client=client, conn=conn, steam_id=os.environ["STEAMSENSE_TARGET_STEAMID"])
#update_engagement_score(conn)

#print(build_player_features(conn, steam_id=os.environ["STEAMSENSE_TARGET_STEAMID"]))
#load_games_dataset(conn)

#fuzzy_results = find_fuzzy_matches(conn)
#survived = fuzzy_results[(fuzzy_results["score"] >= 90) & fuzzy_results["is_plausible"]]

#known_bad = {"Empires", "Cities XL"} # eyeballed this but there could be more i haven't noticed
#final_matches = survived[~survived["original"].isin(known_bad)]

#build_title_map(conn, final_matches)

# only circa 30% of the bulk population seems to be eligible, that should be enough
all_features = get_or_build_bulk_features(engine)
complete_features = all_features.dropna()

matrix, min_age, max_age = build_clustering_matrix(complete_features)

kmeans = KMeans(n_clusters=2, random_state=42, n_init=10)
labels = kmeans.fit_predict(matrix)
matrix = matrix.copy()
matrix["cluster"] = labels

live_features = build_player_features(engine, steam_id=os.environ["STEAMSENSE_TARGET_STEAMID"])
vector = build_live_vector(live_features, min_age, max_age)

my_cluster = assign_to_cluster(kmeans, vector)
print(f"Profile {os.environ["STEAMSENSE_TARGET_STEAMID"]} lands in cluster {my_cluster}")

print(explain_cluster_assignment(matrix, vector, my_cluster).to_string())

matrix_with_ids = matrix.copy()
matrix_with_ids["bulk_user_id"] = complete_features["bulk_user_id"].values

neighbors = find_nearest_neighbors(vector, matrix_with_ids, k=50)
owned_appids = get_owned_appids(engine, os.environ["STEAMSENSE_TARGET_STEAMID"])

recommendations = recommend_games(engine, neighbors, owned_appids, top_n=10)
print(recommendations.to_string())

top_appid = int(recommendations.iloc[0]["appid"])
top_title = recommendations.iloc[0]["title"]
print(f"\nWhy '{top_title}' (appid {top_appid}) was recommended:")
print(explain_recommendation(engine, neighbors, top_appid).to_string())

conn.close()