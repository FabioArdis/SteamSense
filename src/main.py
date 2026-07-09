from dotenv import load_dotenv
import os
from src.collector.steam_client import SteamClient
from src.collector.sync import get_connection, sync_owned_games
from src.features.engagement import update_engagement_score

load_dotenv()

client = SteamClient(api_key=os.environ["STEAM_API_KEY"])
conn = get_connection(host=os.environ["POSTGRES_HOST"], port=int(os.environ["POSTGRES_PORT"]), dbname=os.environ["POSTGRES_DB"], user=os.environ["POSTGRES_USER"], password=os.environ["POSTGRES_PASSWORD"])
sync_owned_games(client=client, conn=conn, steam_id=os.environ["STEAMSENSE_TARGET_STEAMID"])
update_engagement_score(conn)

conn.close()