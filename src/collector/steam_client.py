import requests

from src.collector.exceptions import SteamAPIError, StoreGameNotFound


class SteamClient:
    BASE_URL = "https://api.steampowered.com"
    STORE_URL = "https://store.steampowered.com/api"

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

    def get_app_details(self, appid) -> dict:
        response = requests.get(f"{self.STORE_URL}/appdetails", params={"appids": appid})

        if response.status_code != 200:
            raise SteamAPIError(f"Steam Store API returned {response.status_code}")

        data = response.json()
        if data[str(appid)]["success"] is not True:
            raise StoreGameNotFound(f"Game not found for appid: {appid}")

        return data