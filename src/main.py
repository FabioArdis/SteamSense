from dotenv import load_dotenv
import os

from src.collector.bulk_import import load_games_dataset
from src.collector.steam_client import SteamClient
from src.collector.sync import get_connection, sync_owned_games, get_engine
from src.collector.title_matching import find_fuzzy_matches, build_title_map
from src.features.engagement import update_engagement_score
from src.features.player_features import build_player_features, build_bulk_player_features, \
    build_all_bulk_player_features

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
sample_features = build_all_bulk_player_features(engine)
print(sample_features.describe())
print(sample_features.isna().sum())

conn.close()