from dotenv import load_dotenv
import os
from src.collector.steam_client import SteamClient

load_dotenv()

client = SteamClient(api_key=os.environ["STEAM_API_KEY"])
games = client.get_owned_games(steam_id=os.environ["STEAMSENSE_TARGET_STEAMID"])

print(len(games))
print(games[0])