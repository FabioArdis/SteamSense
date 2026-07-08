import requests

from src.collector.exceptions import SteamAPIError


class SteamClient:
    BASE_URL = "https://api.steampowered.com"

    def __init__(self, api_key: str):
        self.api_key = api_key

    def get_owned_games(self, steam_id: str) -> list[dict]:
        endpoint = f"{self.BASE_URL}/IPlayerService/GetOwnedGames/v1/"
        params = {
            "key": self.api_key,
            "steamid": steam_id,
            "include_appinfo": True,
            "format": "json"
        }

        response = requests.get(endpoint, params)

        if response.status_code != 200:
            raise SteamAPIError(f"SteamAPI returned {response.status_code}")

        return response.json()["response"]["games"]